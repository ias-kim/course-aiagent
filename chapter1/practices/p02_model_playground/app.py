"""
실습 P02: 모델 플레이그라운드

Claude API의 다양한 모델과 파라미터를 직접 비교 체험하는 웹 앱입니다.

학습 목표:
    - 모델별 특성 차이를 체감한다 (속도, 품질, 비용)
    - temperature, max_tokens 등 파라미터가 응답에 미치는 영향을 실험한다
    - 토큰 사용량과 응답 시간을 확인하며 API 비용 감각을 익힌다

모델 비교:
    ┌──────────────┬──────────┬──────────┬────────────────────┐
    │ 모델         │ 속도     │ 비용     │ 적합한 작업        │
    ├──────────────┼──────────┼──────────┼────────────────────┤
    │ Haiku 4.5    │ 가장 빠름│ 가장 저렴│ 분류, 추출, 간단 QA│
    │ Sonnet 4     │ 균형     │ 중간     │ 범용, 코딩, 분석   │
    │ Opus 4       │ 느림     │ 비쌈     │ 복잡한 추론, 창작   │
    └──────────────┴──────────┴──────────┴────────────────────┘
"""

import json
import time
from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

app = Flask(__name__)
client = Anthropic()

# 사용 가능한 모델 정의
MODELS = {
    "haiku": {
        "id": "claude-haiku-4-5-20251001",
        "name": "Haiku 4.5",
        "description": "빠르고 저렴 — 간단한 작업에 적합",
    },
    "sonnet": {
        "id": "claude-sonnet-4-20250514",
        "name": "Sonnet 4",
        "description": "속도와 성능의 균형 — 범용",
    },
    "opus": {
        "id": "claude-opus-4-20250514",
        "name": "Opus 4",
        "description": "최고 성능 — 복잡한 추론에 적합",
    },
}

# 세션별 대화 히스토리
conversations: dict[str, list] = {}


@app.route("/")
def index():
    return render_template("index.html", models=MODELS)


@app.route("/chat", methods=["POST"])
def chat():
    """채팅 API — 모델/파라미터 선택 + SSE 스트리밍"""
    data = request.json
    model_key = data["model"]
    user_message = data["message"]
    temperature = float(data.get("temperature", 1.0))
    max_tokens = int(data.get("max_tokens", 1024))
    session_id = data.get("session_id", "default")

    conv_key = f"{session_id}_{model_key}"
    if conv_key not in conversations:
        conversations[conv_key] = []

    history = conversations[conv_key]
    history.append({"role": "user", "content": user_message})

    model_id = MODELS[model_key]["id"]

    def generate():
        start_time = time.time()

        with client.messages.stream(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=history,
        ) as stream:
            full_response = ""
            for text in stream.text_stream:
                full_response += text
                yield f"data: {json.dumps({'text': text})}\n\n"

            history.append({"role": "assistant", "content": full_response})

            elapsed = round(time.time() - start_time, 2)
            usage = stream.get_final_message().usage
            yield f"data: {json.dumps({'done': True, 'input_tokens': usage.input_tokens, 'output_tokens': usage.output_tokens, 'elapsed': elapsed})}\n\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
    )


@app.route("/reset", methods=["POST"])
def reset():
    data = request.json
    session_id = data.get("session_id", "default")
    model_key = data.get("model", "")
    conv_key = f"{session_id}_{model_key}"
    conversations.pop(conv_key, None)
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True, port=5001)


# ============================================================
# REST API 명세
# ============================================================
#
# 1. GET /
#    메인 페이지 (모델 선택 + 파라미터 조절 + 채팅 UI)
#
# ─────────────────────────────────────────────────────────────
#
# 2. POST /chat
#    사용자 메시지를 받아 선택된 모델로 SSE 스트리밍 응답을 반환합니다.
#
#    Request:
#      Content-Type: application/json
#      Body:
#      {
#        "model":       (string, 필수) 모델 키 — "haiku" | "sonnet" | "opus"
#        "message":     (string, 필수) 사용자 메시지
#        "temperature": (number, 선택) 0.0~1.0 (기본값: 1.0)
#        "max_tokens":  (number, 선택) 최대 출력 토큰 (기본값: 1024)
#        "session_id":  (string, 선택) 세션 식별자 (기본값: "default")
#      }
#
#    Response:
#      Content-Type: text/event-stream
#
#      [텍스트 청크]
#        data: {"text": "응답 텍스트 조각"}
#
#      [완료]
#        data: {"done": true, "input_tokens": 25, "output_tokens": 130, "elapsed": 1.53}
#
# ─────────────────────────────────────────────────────────────
#
# 3. POST /reset
#    대화 히스토리를 초기화합니다.
#
#    Request:
#      Content-Type: application/json
#      Body:
#      {
#        "model":      (string, 필수) 모델 키
#        "session_id": (string, 선택) 세션 식별자 (기본값: "default")
#      }
#
#    Response: {"status": "ok"}
