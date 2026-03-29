"""
Chapter 3-0: Tool Use 6단계 한눈에 보기

Function Calling의 전체 흐름을 6단계로 정리한 최소 예제입니다.

  ① 함수/API 구현
  ② Tool metadata 정의 (schema)
  ③ LLM API 요청 시 tools(schema) 포함
  ④ Tool routing / dispatch 구현
  ⑤ Tool result handling (LLM response injection)
  ⑥ 테스트 및 검증
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-20250514"


# ── Step ① 함수/API 구현 ─────────────────────────────────
# 실제로 실행될 함수들을 구현합니다.

def get_weather(city: str) -> str:
    """도시의 날씨를 반환하는 함수 (데모용 하드코딩)"""
    data = {"Seoul": "맑음, 18°C", "Busan": "흐림, 22°C"}
    return data.get(city, f"{city}: 정보 없음")


def add_numbers(a: float, b: float) -> str:
    """두 수를 더하는 함수"""
    return str(a + b)


# ── Step ② Tool metadata 정의 (schema) ──────────────────
# LLM이 읽을 수 있는 JSON Schema 형태로 도구 명세를 작성합니다.
# description이 명확해야 LLM이 올바른 도구를 선택합니다.

tools = [
    {
        "name": "get_weather",
        "description": "도시의 현재 날씨를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "도시 이름 (영문)"}
            },
            "required": ["city"],
        },
    },
    {
        "name": "add_numbers",
        "description": "두 숫자를 더합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "첫 번째 숫자"},
                "b": {"type": "number", "description": "두 번째 숫자"},
            },
            "required": ["a", "b"],
        },
    },
]


# ── Step ④ Tool routing / dispatch 구현 ─────────────────
# LLM이 반환한 도구 이름을 보고 실제 함수를 매핑·실행합니다.
# (Step ③ 이전에 미리 정의해 둡니다)

def dispatch_tool(name: str, args: dict) -> str:
    """도구 이름 → 실제 함수 라우팅"""
    if name == "get_weather":
        return get_weather(args["city"])
    elif name == "add_numbers":
        return add_numbers(args["a"], args["b"])
    else:
        return f"알 수 없는 도구: {name}"


# ── Step ③ + ⑤ LLM API 호출 & 결과 주입 ────────────────
# 하나의 함수로 전체 흐름을 실행합니다.
#   ③ tools(schema)를 포함하여 LLM API 호출
#   ⑤ 도구 실행 결과를 tool_result로 LLM에 다시 전달

def run(user_message: str):
    print(f"\n{'='*50}")
    print(f"[사용자] {user_message}")
    print("=" * 50)

    messages = [{"role": "user", "content": user_message}]

    # ── Step ③: tools를 포함하여 API 호출
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=tools,          # ← schema 전달
        messages=messages,
    )

    # 도구 호출이 필요 없으면 바로 답변
    if response.stop_reason == "end_turn":
        print(f"[LLM 답변] {response.content[0].text}")
        return

    # ── Step ④: 도구 호출 요청이면 dispatch
    tool_block = next(b for b in response.content if b.type == "tool_use")
    print(f"[LLM 요청] 도구={tool_block.name}, 인자={tool_block.input}")

    result = dispatch_tool(tool_block.name, tool_block.input)
    print(f"[도구 실행] 결과={result}")

    # ── Step ⑤: tool_result를 LLM에 주입
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_block.id,   # 요청-결과 매칭
                "content": result,
            }
        ],
    })

    final = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )
    print(f"[LLM 답변] {final.content[0].text}")


# ── Step ⑥ 테스트 및 검증 ───────────────────────────────
# 다양한 질문으로 LLM이 올바른 도구를 선택하는지 확인합니다.

if __name__ == "__main__":
    run("서울 날씨 어때?")          # → get_weather 호출
    run("15와 27을 더해줘")         # → add_numbers 호출
    run("안녕하세요!")              # → 도구 없이 직접 답변
