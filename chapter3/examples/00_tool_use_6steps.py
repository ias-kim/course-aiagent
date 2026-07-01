"""
Chapter 3-0: Tool Use 6단계 한눈에 보기

Function Calling의 전체 흐름을 6단계로 쪼개서 보는 최소 예제입니다.

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
MODEL = "claude-sonnet-4-6"


# ── Step ① 함수/API 구현 ─────────────────────────────────
# 실제 실행은 LLM이 아니라 우리 코드의 함수가 담당합니다.

def get_weather(city: str) -> str:
    """도시의 날씨를 반환합니다. 데모용이라 값을 하드코딩했습니다."""
    data = {"Seoul": "맑음, 18°C", "Busan": "흐림, 22°C"}
    return data.get(city, f"{city}: 정보 없음")


def add_numbers(a: float, b: float) -> str:
    """두 수를 더하는 함수"""
    return str(a + b)


# ── Step ② Tool metadata 정의 (schema) ──────────────────
# LLM에게 "이런 도구가 있다"고 알려줄 명세를 JSON Schema로 작성합니다.
# description이 구체적일수록 모델이 적절한 상황에서 도구를 선택합니다.

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
# LLM이 요청한 도구 이름을 실제 Python 함수로 연결합니다.
# 이 라우팅 코드가 있어야 tool_use 요청이 실제 실행으로 이어집니다.

def dispatch_tool(name: str, args: dict) -> str:
    """도구 이름을 보고 실제 함수를 찾아 실행합니다."""
    if name == "get_weather":
        return get_weather(args["city"])
    elif name == "add_numbers":
        return add_numbers(args["a"], args["b"])
    else:
        return f"알 수 없는 도구: {name}"


# ── Step ③ + ⑤ LLM API 호출 & 결과 주입 ────────────────
# 위에서 나눈 단계를 하나의 실행 흐름으로 묶습니다.
#   ③ tools(schema)를 포함하여 LLM API 호출
#   ⑤ 도구 실행 결과를 tool_result로 LLM에 다시 전달

def run(user_message: str):
    print(f"\n{'='*50}")
    print(f"[사용자] {user_message}")
    print("=" * 50)

    messages = [{"role": "user", "content": user_message}]

    # ── Step ③: tools 명세를 함께 보내 모델이 도구를 선택할 수 있게 합니다.
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=tools,          # 모델에게 사용 가능한 도구 목록을 전달합니다.
        messages=messages,
    )

    # 도구가 필요 없다고 판단하면 모델은 바로 최종 답변을 줍니다.
    if response.stop_reason == "end_turn":
        print(f"[LLM 답변] {response.content[0].text}")
        return

    # ── Step ④: tool_use가 오면 우리 코드가 실제 함수를 실행합니다.
    tool_block = next(b for b in response.content if b.type == "tool_use")
    print(f"[LLM 요청] 도구={tool_block.name}, 인자={tool_block.input}")

    result = dispatch_tool(tool_block.name, tool_block.input)
    print(f"[도구 실행] 결과={result}")

    # ── Step ⑤: 실행 결과를 tool_result로 다시 모델에게 알려줍니다.
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_block.id,   # 어떤 요청의 결과인지 맞춰 주는 ID입니다.
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
# 다양한 질문으로 모델이 도구가 필요한지, 어떤 도구를 쓸지 확인합니다.

if __name__ == "__main__":
    run("서울 날씨 어때?")          # → get_weather 호출
    run("15와 27을 더해줘")         # → add_numbers 호출
    run("안녕하세요!")              # → 도구 없이 직접 답변
