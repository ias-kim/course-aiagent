"""
실습 P01: 멀티툴 어시스턴트

Tool Use의 핵심 흐름을 웹 UI에서 눈으로 확인하는 실습입니다.

학습 목표:
    - 도구 정의(JSON Schema)와 LLM의 도구 선택 과정을 이해한다
    - Agent 루프(tool_use → tool_result → 반복)를 실제 앱에서 구현한다
    - 도구 호출 과정을 UI에 시각화하여 "LLM은 요청하고 Agent가 실행한다"를 체감한다
    - 도구 에러 시 is_error 처리 패턴을 적용한다

활용 예제:
    - Ch3-01: 도구 정의 (JSON Schema)
    - Ch3-02: 다중 도구 선택
    - Ch3-03: Agent 루프 (stop_reason 기반)
    - Ch3-05: 도구 에러 처리 (is_error)

실행: python chapter3/practices/p01_multi_tool_assistant/app.py → http://localhost:5010
"""

import json
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

app = Flask(__name__)
client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 도구 정의
# ============================================================
# 각 도구는 JSON Schema로 정의합니다.
# description은 모델이 도구 선택을 할 때 읽는 안내문이므로 구체적으로 작성합니다.
TOOLS = [
    {
        "name": "get_weather",
        "description": "특정 도시의 현재 날씨 정보를 가져옵니다. 기온, 날씨 상태, 습도를 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "날씨를 조회할 도시 이름 (예: '서울', '부산', '제주')",
                },
            },
            "required": ["city"],
        },
    },
    {
        "name": "calculator",
        "description": "수학 계산을 수행합니다. 사칙연산, 거듭제곱, 나머지 연산 등을 처리합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "계산할 수학 표현식 (예: '2 + 3', '10 ** 2', '100 / 7')",
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_exchange_rate",
        "description": "두 통화 간의 환율을 조회합니다. 원본 금액을 대상 통화로 변환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_currency": {
                    "type": "string",
                    "description": "원본 통화 코드 (예: 'USD', 'EUR', 'JPY')",
                },
                "to_currency": {
                    "type": "string",
                    "description": "대상 통화 코드 (예: 'KRW', 'USD')",
                },
                "amount": {
                    "type": "number",
                    "description": "변환할 금액 (기본값: 1)",
                },
            },
            "required": ["from_currency", "to_currency"],
        },
    },
    {
        "name": "get_time",
        "description": "특정 도시의 현재 날짜와 시간을 알려줍니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "시간을 조회할 도시 이름",
                },
            },
            "required": ["city"],
        },
    },
]


# ============================================================
# 도구 실행 함수
# ============================================================
# 실제 서비스에서는 외부 API를 호출하겠지만, 여기서는 학습용 데이터로 시뮬레이션합니다.
# 반환값은 (결과 문자열, 에러 여부)입니다.

def execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """도구를 실행하고 (결과, 에러여부)를 반환합니다."""

    if name == "get_weather":
        city = tool_input["city"]
        weather_data = {
            "서울": {"temp": 12, "condition": "맑음", "humidity": 45},
            "부산": {"temp": 15, "condition": "흐림", "humidity": 60},
            "제주": {"temp": 18, "condition": "비", "humidity": 80},
            "도쿄": {"temp": 14, "condition": "맑음", "humidity": 40},
            "뉴욕": {"temp": 8, "condition": "눈", "humidity": 70},
        }
        data = weather_data.get(city)
        if data:
            return json.dumps(data, ensure_ascii=False), False
        return f"'{city}'의 날씨 정보를 찾을 수 없습니다. 지원 도시: {', '.join(weather_data.keys())}", True

    elif name == "calculator":
        expression = tool_input["expression"]
        try:
            # 주의: eval은 보안 위험이 있으므로 실제 서비스에서는 사용하지 않습니다.
            result = eval(expression)
            return str(result), False
        except Exception as e:
            return f"계산 오류: {e}", True

    elif name == "get_exchange_rate":
        from_cur = tool_input["from_currency"].upper()
        to_cur = tool_input["to_currency"].upper()
        amount = tool_input.get("amount", 1)
        rates = {
            ("USD", "KRW"): 1350.50,
            ("EUR", "KRW"): 1450.30,
            ("JPY", "KRW"): 9.15,
            ("KRW", "USD"): 0.00074,
            ("KRW", "JPY"): 0.109,
        }
        rate = rates.get((from_cur, to_cur))
        if rate:
            converted = amount * rate
            return json.dumps({
                "from": from_cur, "to": to_cur,
                "rate": rate, "amount": amount,
                "result": round(converted, 2),
            }, ensure_ascii=False), False
        return f"'{from_cur} → {to_cur}' 환율 정보를 찾을 수 없습니다.", True

    elif name == "get_time":
        city = tool_input["city"]
        tz_offsets = {
            "서울": 9, "부산": 9, "제주": 9,
            "도쿄": 9, "뉴욕": -5, "런던": 0,
        }
        offset = tz_offsets.get(city)
        if offset is not None:
            tz = timezone(timedelta(hours=offset))
            now = datetime.now(tz)
            return json.dumps({
                "city": city,
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "timezone": f"UTC{'+' if offset >= 0 else ''}{offset}",
            }, ensure_ascii=False), False
        return f"'{city}'의 시간대 정보를 찾을 수 없습니다.", True

    return f"알 수 없는 도구: {name}", True


# UI에 표시할 도구 아이콘과 이름입니다. Claude에 전달되는 도구 정의와는 별도입니다.
TOOL_INFO = {
    "get_weather": {"icon": "🌤️", "label": "날씨 조회"},
    "calculator": {"icon": "🧮", "label": "계산기"},
    "get_exchange_rate": {"icon": "💱", "label": "환율 조회"},
    "get_time": {"icon": "🕐", "label": "시간 조회"},
}


# 브라우저 세션별 대화 히스토리입니다.
conversations: dict[str, list] = {}


# ============================================================
# Flask 라우트입니다.
# ============================================================
@app.route("/")
def index():
    return render_template("index.html", tool_info=TOOL_INFO)


@app.route("/chat", methods=["POST"])
def chat():
    """
    Agent 루프가 포함된 채팅 API입니다.
    도구 호출 과정을 SSE로 실시간 전달합니다.

    SSE 이벤트 종류:
      - tool_call: LLM이 도구 호출을 요청함
      - tool_result: 도구 실행 결과
      - text: LLM의 텍스트 응답 (최종 답변)
      - done: 응답 완료 + 토큰 사용량
    """
    data = request.json
    user_message = data["message"]
    session_id = data.get("session_id", "default")

    if session_id not in conversations:
        conversations[session_id] = []

    history = conversations[session_id]
    history.append({"role": "user", "content": user_message})

    def generate():
        max_iterations = 10
        total_input_tokens = 0
        total_output_tokens = 0

        for iteration in range(max_iterations):
            # 현재 히스토리와 도구 목록을 함께 보내 모델의 다음 행동을 받습니다.
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system="당신은 다양한 도구를 활용하는 유능한 어시스턴트입니다. 한국어로 답변합니다.",
                tools=TOOLS,
                messages=history,
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            # 최종 답변이면 텍스트를 브라우저로 보내고 루프를 종료합니다.
            if response.stop_reason == "end_turn":
                for block in response.content:
                    if block.type == "text":
                        yield f"data: {json.dumps({'text': block.text})}\n\n"
                history.append({"role": "assistant", "content": response.content[0].text})
                break

            # 도구 호출 요청이 오면 실행 과정을 UI에 보여주면서 처리합니다.
            if response.stop_reason == "tool_use":
                # tool_use가 포함된 모델 응답을 히스토리에 저장합니다.
                history.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "text" and block.text:
                        yield f"data: {json.dumps({'text': block.text})}\n\n"

                    if block.type == "tool_use":
                        tool_info = TOOL_INFO.get(block.name, {"icon": "🔧", "label": block.name})

                        # 브라우저에 "어떤 도구를 어떤 인자로 호출하는지" 먼저 알려줍니다.
                        yield f"data: {json.dumps({'tool_call': {'name': block.name, 'icon': tool_info['icon'], 'label': tool_info['label'], 'input': block.input}})}\n\n"

                        # 실제 도구 실행은 서버 코드가 담당합니다.
                        result, is_error = execute_tool(block.name, block.input)

                        # 도구 실행 결과와 성공/실패 여부를 브라우저에 보냅니다.
                        yield f"data: {json.dumps({'tool_result': {'name': block.name, 'result': result, 'is_error': is_error}})}\n\n"

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                            "is_error": is_error,
                        })

                # 도구 결과를 히스토리에 추가하면 다음 반복에서 모델이 이를 참고합니다.
                history.append({"role": "user", "content": tool_results})

        # 모든 반복이 끝나면 토큰 사용량과 함께 완료 이벤트를 보냅니다.
        yield f"data: {json.dumps({'done': True, 'input_tokens': total_input_tokens, 'output_tokens': total_output_tokens})}\n\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
    )


@app.route("/reset", methods=["POST"])
def reset():
    """대화 히스토리 초기화"""
    session_id = request.json.get("session_id", "default")
    conversations.pop(session_id, None)
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True, port=5010)


# ============================================================
# REST API 명세
# ============================================================
#
# 1. GET /
#    채팅 UI와 사용 가능한 도구 목록을 보여주는 메인 페이지
#
# ─────────────────────────────────────────────────────────────
#
# 2. POST /chat
#    사용자 메시지를 받아 Agent 루프를 실행하고 과정을 SSE로 스트리밍합니다.
#
#    Request:
#      Content-Type: application/json
#      Body:
#      {
#        "message":    (string, 필수) 사용자 메시지
#        "session_id": (string, 선택) 세션 식별자 (기본값: "default")
#      }
#
#    Response:
#      Content-Type: text/event-stream
#      스트리밍 이벤트 (SSE):
#
#      [도구 호출] — 모델이 도구 사용을 요청할 때
#        data: {"tool_call": {"name": "get_weather", "icon": "🌤️", "label": "날씨 조회", "input": {"city": "서울"}}}
#
#      [도구 결과] — 도구 실행 완료 시
#        data: {"tool_result": {"name": "get_weather", "result": "{...}", "is_error": false}}
#
#      [텍스트] — 모델의 텍스트 응답
#        data: {"text": "서울의 현재 기온은 12°C이고..."}
#
#      [완료] — 전체 응답 완료
#        data: {"done": true, "input_tokens": 150, "output_tokens": 80}
#
#    흐름:
#      클라이언트                              서버
#        │  POST /chat {message: "서울 날씨"}   │
#        │ ──────────────────────────────────►  │
#        │                                      │── LLM 호출 (tools 포함)
#        │  tool_call: get_weather("서울")      │
#        │ ◄──────────────────────────────────  │
#        │                                      │── 도구 실행
#        │  tool_result: {"temp": 12, ...}      │
#        │ ◄──────────────────────────────────  │
#        │                                      │── LLM 재호출 (결과 포함)
#        │  text: "서울은 현재 맑고 12°C..."     │
#        │ ◄──────────────────────────────────  │
#        │  done: {input_tokens, output_tokens}  │
#        │ ◄──────────────────────────────────  │
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
#        "session_id": (string, 선택) 세션 식별자 (기본값: "default")
#      }
#
#    Response:
#      Content-Type: application/json
#      {"status": "ok"}
