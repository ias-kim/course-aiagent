"""
Chapter 3-3: Tool Use 에이전트 루프

Ch1-5에서 배운 대화 히스토리 루프에 Tool Use를 결합합니다.
이 패턴이 실제 AI Agent의 가장 기본적인 골격입니다.

Agent 루프 = while 루프 + 대화 히스토리 + LLM 호출 + 도구 실행

    while True:
        response = LLM(messages, tools)
        if response.stop_reason == "tool_use":
            결과 = 도구 실행
            messages에 결과 추가
            continue              ← 도구 결과를 가지고 다시 LLM 호출
        else:
            break                 ← 최종 답변 완료

핵심:
    LLM이 도구를 호출하는 한 루프를 계속 돌고,
    최종 답변(end_turn)이 나오면 루프를 종료합니다.
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 도구 정의와 실행 함수를 한 파일 안에 둔 학습용 예제입니다.
# ============================================================
tools = [
    {
        "name": "get_weather",
        "description": "특정 도시의 현재 날씨 정보를 가져옵니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "도시 이름"},
            },
            "required": ["city"],
        },
    },
    {
        "name": "calculator",
        "description": "수학 계산을 수행합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "수학 표현식"},
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_exchange_rate",
        "description": "두 통화 간의 환율을 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_currency": {"type": "string", "description": "원본 통화 코드 (예: USD)"},
                "to_currency": {"type": "string", "description": "대상 통화 코드 (예: KRW)"},
            },
            "required": ["from_currency", "to_currency"],
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> str:
    """도구를 실행합니다. 외부 API 대신 하드코딩 데이터로 시뮬레이션합니다."""
    if name == "get_weather":
        weather = {
            "서울": "맑음, 12°C, 습도 45%",
            "부산": "흐림, 15°C, 습도 60%",
            "도쿄": "맑음, 14°C, 습도 40%",
        }
        return weather.get(tool_input["city"], f"{tool_input['city']}: 날씨 정보 없음")

    elif name == "calculator":
        try:
            # 주의: eval은 보안 위험이 있으므로 실제 서비스에서는 사용하지 않습니다.
            return str(eval(tool_input["expression"]))
        except Exception as e:
            return f"계산 오류: {e}"

    elif name == "get_exchange_rate":
        rates = {
            ("USD", "KRW"): 1350.50,
            ("EUR", "KRW"): 1450.30,
            ("JPY", "KRW"): 9.15,
        }
        pair = (tool_input["from_currency"], tool_input["to_currency"])
        rate = rates.get(pair, 0)
        if rate:
            return f"1 {pair[0]} = {rate} {pair[1]}"
        return f"환율 정보 없음: {pair[0]} → {pair[1]}"

    return f"알 수 없는 도구: {name}"


# ============================================================
# Agent 루프 구현입니다.
# ============================================================
print("=" * 60)
print("Tool Use Agent 루프")
print("=" * 60)


def agent_loop(user_message: str, max_iterations: int = 10) -> str:
    """
    Tool Use가 포함된 Agent 루프입니다.

    모델이 도구를 요청하면 실행 결과를 messages에 추가하고 다시 호출합니다.
    최종 답변(end_turn)이 나오면 루프를 멈추고 답변을 반환합니다.

    Args:
        user_message: 사용자 질문
        max_iterations: 도구 호출이 끝나지 않는 상황을 막기 위한 최대 반복 횟수
    """
    messages = [{"role": "user", "content": user_message}]
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n  --- 반복 {iteration} ---")

        # 현재까지의 대화와 도구 목록을 함께 보내 모델의 다음 행동을 받습니다.
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        print(f"  stop_reason: {response.stop_reason}")

        # 최종 답변이면 더 이상 도구를 실행하지 않고 종료합니다.
        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if b.type == "text"),
                "응답 없음"
            )
            return final_text

        # 도구 호출 요청이 오면 실제 도구를 실행합니다.
        if response.stop_reason == "tool_use":
            # tool_use가 들어 있는 모델 응답도 히스토리에 남겨야 합니다.
            messages.append({"role": "assistant", "content": response.content})

            # 한 응답에 여러 tool_use 블록이 들어올 수 있으므로 모두 처리합니다.
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [도구 호출] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                    result = execute_tool(block.name, block.input)
                    print(f"  [도구 결과] {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # 실행 결과를 tool_result로 히스토리에 추가합니다.
            messages.append({"role": "user", "content": tool_results})
            # 다음 반복에서 모델은 이 결과를 보고 최종 답변할지, 도구를 더 쓸지 판단합니다.

    return "최대 반복 횟수 초과"


# ============================================================
# 다양한 질문으로 Agent 루프가 어떻게 반복되는지 확인합니다.
# ============================================================

# --- 테스트 1: 도구 하나만 필요한 질문 ---
print("\n" + "=" * 60)
print("테스트 1: 단일 도구 호출")
print("=" * 60)
result = agent_loop("서울 날씨 알려줘")
print(f"\n최종 답변: {result}")

# --- 테스트 2: 여러 도구가 필요한 복합 질문 ---
print("\n" + "=" * 60)
print("테스트 2: 복합 질문")
print("=" * 60)
result = agent_loop("100달러가 한국 돈으로 얼마야? 그리고 서울 날씨도 알려줘")
print(f"\n최종 답변: {result}")

# --- 테스트 3: 도구 없이 바로 답할 수 있는 질문 ---
print("\n" + "=" * 60)
print("테스트 3: 도구 불필요한 질문")
print("=" * 60)
result = agent_loop("AI Agent란 무엇인가요?")
print(f"\n최종 답변: {result}")


# ============================================================
# 정리: Agent 루프 핵심
# ============================================================
print()
print("=" * 60)
print("정리")
print("=" * 60)
print("""
[Agent 루프 흐름도]

  User: "100달러가 원화로 얼마고, 서울 날씨도 알려줘"
    │
    ▼
  ┌─────────────────────────────────────┐
  │ while stop_reason == "tool_use":    │
  │                                     │
  │   반복 1: LLM → tool_use           │
  │     get_exchange_rate(USD → KRW)    │
  │     get_weather(서울)               │ ← 여러 도구 동시 호출 가능
  │     결과를 messages에 추가           │
  │                                     │
  │   반복 2: LLM → end_turn           │
  │     "100달러는 약 135,050원이고,    │
  │      서울은 맑음, 12도입니다."       │
  └─────────────────────────────────────┘
    │
    ▼
  최종 답변 반환

[핵심 포인트]
1. stop_reason으로 루프 계속/종료를 판단한다
2. 한 번에 여러 도구가 호출될 수 있다 → 모든 tool_use 블록 처리
3. max_iterations로 무한 루프를 반드시 방지한다
4. 이 패턴이 Ch4 ReAct Agent의 기반이 된다
""")
