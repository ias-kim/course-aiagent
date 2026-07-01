"""
실습 P01: 페르소나 챗봇

페르소나(Persona)란?
    AI에게 입히는 "역할 설정"입니다.
    동일한 LLM이라도 페르소나에 따라 말투, 지식 범위, 응답 스타일이 완전히 달라집니다.

AI Agent에서 페르소나를 만들 때는 보통 System Prompt에 아래 4가지를 넣습니다.

    1) 역할 정의 (Role)       — "당신은 ~입니다"
    2) 말투/톤 설정 (Tone)    — "~하게 말합니다" (반말, 존댓말, 이모지 등)
    3) 지식 범위 (Scope)      — "~에 대해서만 답합니다"
    4) 행동 규칙 (Rules)      — "~하지 않습니다", "~할 때는 ~합니다"

    예시:
        system = "당신은 조선시대 선비입니다. 고풍스러운 말투를 사용하며,
                  현대 기술에 대한 질문에는 조선시대의 관점에서 해석하여 답합니다.
                  욕설이나 부적절한 질문에는 '그런 말은 예의에 어긋나옵니다'라고 답합니다."
                  ↑ Role          ↑ Tone              ↑ Scope                    ↑ Rules

실습 목표:
    - System Prompt로 페르소나를 설정하는 방법을 익힌다
    - 동일한 질문에 페르소나별로 응답이 어떻게 달라지는지 체험한다
    - Flask + SSE로 스트리밍 채팅 UI를 구현한다
"""

import json
from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

app = Flask(__name__)
client = Anthropic()
MODEL = "claude-sonnet-4-6"

# ============================================================
# 페르소나 정의
# ============================================================
# 각 페르소나는 하나의 System Prompt로 구현됩니다.
# Role, Tone, Scope, Rules가 문장 안에 어떻게 녹아 있는지 비교해 보세요.
PERSONAS = {
    "teacher": {
        "name": "친절한 선생님",
        "description": "프로그래밍 입문자를 위한 선생님",
        "system": (
            # Role: AI가 맡을 역할
            "당신은 프로그래밍을 처음 배우는 학생을 가르치는 친절한 선생님입니다. "
            # Tone: 답변 말투와 분위기
            "항상 존댓말을 사용하고, 격려하는 톤으로 말합니다. "
            # Scope: 주로 답할 주제 범위
            "프로그래밍 관련 질문에 대해 비유와 예시를 들어 쉽게 설명합니다. "
            # Rules: 답변할 때 지켜야 할 규칙
            "코드 예시를 보여줄 때는 반드시 한 줄씩 설명을 덧붙입니다. "
            "프로그래밍과 무관한 질문에는 '좋은 질문이지만, 프로그래밍 관련 내용을 함께 이야기해봐요!'라고 안내합니다."
        ),
    },
    "chef": {
        "name": "요리사 셰프",
        "description": "열정적인 한식 요리사",
        "system": (
            "당신은 20년 경력의 열정적인 한식 요리사입니다. "
            "반말을 사용하고 호탕한 말투로 말합니다. '자!', '좋아!' 같은 감탄사를 자주 씁니다. "
            "요리 관련 질문에는 실용적인 레시피와 팁을 알려줍니다. 계량은 정확하게 알려줍니다. "
            "요리와 관련 없는 질문에는 어떻게든 요리에 비유해서 답합니다."
        ),
    },
    "detective": {
        "name": "탐정",
        "description": "추리를 좋아하는 탐정",
        "system": (
            "당신은 셜록 홈즈 스타일의 탐정입니다. "
            "모든 대화를 추리하듯 분석적으로 접근하며, '흥미롭군...', '단서를 정리해보면...' 같은 표현을 사용합니다. "
            "어떤 질문이든 논리적 추론 과정을 보여주며 답합니다. "
            "결론을 바로 말하지 않고, 추리 과정을 먼저 보여준 뒤 결론을 제시합니다."
        ),
    },
}

# 세션별 대화 히스토리입니다. 실습용이라 서버 메모리에만 저장합니다.
conversations: dict[str, list] = {}


@app.route("/")
def index():
    """페르소나 선택 화면과 채팅 UI를 보여줍니다."""
    return render_template("index.html", personas=PERSONAS)


@app.route("/chat", methods=["POST"])
def chat():
    """
    채팅 API입니다. SSE(Server-Sent Events)로 답변을 실시간 전송합니다.

    SSE란?
        서버가 브라우저로 데이터를 실시간 전송하는 단방향 스트리밍 방식입니다.
        Claude의 스트리밍 응답을 토큰 단위로 브라우저에 전달할 수 있습니다.
    """
    data = request.json
    persona_id = data["persona"]
    user_message = data["message"]
    session_id = data.get("session_id", "default")

    # 같은 브라우저 세션 안에서도 페르소나별로 대화를 따로 저장합니다.
    conv_key = f"{session_id}_{persona_id}"
    if conv_key not in conversations:
        conversations[conv_key] = []

    history = conversations[conv_key]
    history.append({"role": "user", "content": user_message})

    persona = PERSONAS[persona_id]

    def generate():
        """스트리밍 응답 생성기"""
        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            system=persona["system"],  # 페르소나를 실제로 적용하는 핵심 부분입니다.
            messages=history,
        ) as stream:
            full_response = ""
            for text in stream.text_stream:
                full_response += text
                # SSE는 각 이벤트를 "data: ...\n\n" 형태로 보냅니다.
                yield f"data: {json.dumps({'text': text})}\n\n"

            # 응답이 끝난 뒤 assistant 메시지를 히스토리에 저장합니다.
            history.append({"role": "assistant", "content": full_response})

            # 브라우저에 토큰 사용량도 함께 알려줍니다.
            usage = stream.get_final_message().usage
            yield f"data: {json.dumps({'done': True, 'input_tokens': usage.input_tokens, 'output_tokens': usage.output_tokens})}\n\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
    )


@app.route("/reset", methods=["POST"])
def reset():
    """현재 페르소나의 대화 히스토리를 초기화합니다."""
    data = request.json
    session_id = data.get("session_id", "default")
    persona_id = data.get("persona", "")
    conv_key = f"{session_id}_{persona_id}"
    conversations.pop(conv_key, None)
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True, port=5000)


# ============================================================
# REST API 명세
# ============================================================
#
# 1. GET /
#    메인 페이지, 즉 페르소나 선택과 채팅 UI를 반환합니다.
#
#    Response: text/html
#
# ─────────────────────────────────────────────────────────────
#
# 2. POST /chat
#    사용자 메시지를 받아 Claude 응답을 SSE 스트리밍으로 반환합니다.
#
#    Request:
#      Content-Type: application/json
#      Body:
#      {
#        "persona":    (string, 필수) 페르소나 ID — "teacher" | "chef" | "detective"
#        "message":    (string, 필수) 사용자 메시지
#        "session_id": (string, 선택) 세션 식별자 (기본값: "default")
#      }
#
#    Response:
#      Content-Type: text/event-stream
#      스트리밍 이벤트 (SSE):
#
#      [텍스트 청크] — 생성되는 텍스트 조각을 반복 전송
#        data: {"text": "응답 텍스트 조각"}
#
#      [완료] — 스트림 마지막에 1회 전송
#        data: {"done": true, "input_tokens": 25, "output_tokens": 130}
#
#    흐름:
#      클라이언트                           서버
#        │  POST /chat {message: "안녕"}     │
#        │ ──────────────────────────────►   │
#        │                                   │── Claude API 스트리밍 호출
#        │   data: {"text": "안"}            │
#        │ ◄──────────────────────────────   │
#        │   data: {"text": "녕하"}          │
#        │ ◄──────────────────────────────   │
#        │   data: {"text": "세요!"}         │
#        │ ◄──────────────────────────────   │
#        │   data: {"done": true, ...}       │
#        │ ◄──────────────────────────────   │
#
# ─────────────────────────────────────────────────────────────
#
# 3. POST /reset
#    특정 페르소나에 쌓인 대화 히스토리를 초기화합니다.
#
#    Request:
#      Content-Type: application/json
#      Body:
#      {
#        "persona":    (string, 필수) 초기화할 페르소나 ID
#        "session_id": (string, 선택) 세션 식별자 (기본값: "default")
#      }
#
#    Response:
#      Content-Type: application/json
#      {"status": "ok"}
