"""
Chapter 3-2: 다중 도구 (Multiple Tools)

LLM에게 여러 도구를 제공하면, 질문에 맞춰 어떤 도구가 필요한지 스스로 고릅니다.

핵심 포인트:
    - 도구의 description이 선택 기준이 됩니다
    - 도구가 필요 없는 질문에는 도구 없이 직접 답변합니다
    - 하나의 응답에서 여러 도구를 동시에 호출할 수도 있습니다
"""

import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 1부: 여러 도구 정의
# ============================================================
print("=" * 60)
print("1부: 다중 도구 정의")
print("=" * 60)

tools = [
    {
        "name": "get_weather",
        "description": "특정 도시의 현재 날씨 정보를 가져옵니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "날씨를 조회할 도시 이름 (예: '서울', '부산')",
                },
            },
            "required": ["city"],
        },
    },
    {
        "name": "calculator",
        "description": "수학 계산을 수행합니다. 사칙연산, 거듭제곱 등을 처리합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "계산할 수학 표현식 (예: '2 + 3', '10 ** 2')",
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_time",
        "description": "특정 도시의 현재 시간을 알려줍니다.",
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

print(f"정의된 도구 {len(tools)}개:")
for tool in tools:
    print(f"  - {tool['name']}: {tool['description']}")


# ============================================================
# 도구 실행 함수들 (시뮬레이션)
# ============================================================
# 실제 서비스라면 외부 API를 호출하겠지만, 여기서는 학습용 더미 데이터를 반환합니다.

def get_weather(city: str) -> str:
    """날씨 API 시뮬레이션"""
    weather_data = {
        "서울": {"temp": 12, "condition": "맑음", "humidity": 45},
        "부산": {"temp": 15, "condition": "흐림", "humidity": 60},
        "제주": {"temp": 18, "condition": "비", "humidity": 80},
    }
    data = weather_data.get(city, {"temp": 20, "condition": "알 수 없음", "humidity": 50})
    return json.dumps(data, ensure_ascii=False)


def calculator(expression: str) -> str:
    """계산기"""
    try:
        # 주의: eval은 보안 위험이 있으므로 실제 서비스에서는 사용하지 않습니다.
        return str(eval(expression))
    except Exception as e:
        return f"계산 오류: {e}"


def get_time(city: str) -> str:
    """시간 조회 시뮬레이션"""
    # 예제를 단순하게 유지하기 위해 UTC+9 기준 시간만 반환합니다.
    kst = datetime.now(timezone(timedelta(hours=9)))
    return kst.strftime(f"{city} 현재 시간: %Y-%m-%d %H:%M:%S KST")


# 도구 이름을 실제 실행 함수에 연결하는 매핑입니다.
tool_functions = {
    "get_weather": lambda input: get_weather(input["city"]),
    "calculator": lambda input: calculator(input["expression"]),
    "get_time": lambda input: get_time(input["city"]),
}


def execute_tool(name: str, tool_input: dict) -> str:
    """도구 이름으로 해당 함수를 찾아 실행합니다."""
    if name in tool_functions:
        return tool_functions[name](tool_input)
    return f"알 수 없는 도구: {name}"


# ============================================================
# 2부: LLM의 도구 선택 관찰
# ============================================================
# 같은 도구 목록을 주고 질문만 바꿔 봅니다.
# 모델이 질문의 의도에 맞는 도구를 고르는지 확인합니다.
print()
print("=" * 60)
print("2부: 질문별 도구 선택")
print("=" * 60)

test_questions = [
    "서울 날씨 어때?",             # 날씨 도구가 필요한 질문
    "15의 3제곱은?",               # 계산기 도구가 필요한 질문
    "지금 도쿄 몇 시야?",          # 시간 도구가 필요한 질문
    "안녕하세요! 반갑습니다.",      # 도구 없이 바로 답할 수 있는 질문
]

for question in test_questions:
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        tools=tools,
        messages=[{"role": "user", "content": question}],
    )

    print(f"\n질문: {question}")
    print(f"  stop_reason: {response.stop_reason}")

    if response.stop_reason == "tool_use":
        tool_block = next(b for b in response.content if b.type == "tool_use")
        print(f"  선택한 도구: {tool_block.name}")
        print(f"  인자: {tool_block.input}")
    else:
        # 도구가 필요 없으면 모델이 바로 텍스트로 답합니다.
        text_block = next(b for b in response.content if b.type == "text")
        print(f"  직접 답변: {text_block.text[:50]}...")


# ============================================================
# 3부: 도구 실행까지 완료하는 헬퍼 함수
# ============================================================
# 도구 호출, 실행, 결과 반환, 최종 답변까지 하나의 helper로 묶습니다.
print()
print("=" * 60)
print("3부: 완전한 도구 호출 사이클")
print("=" * 60)


def chat_with_tools(user_message: str) -> str:
    """필요하면 도구를 실행한 뒤 사용자 질문에 답하는 함수입니다."""
    messages = [{"role": "user", "content": user_message}]

    # 1차 호출: 모델에게 질문과 도구 목록을 함께 전달합니다.
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )

    # 도구가 필요 없으면 첫 응답을 그대로 반환합니다.
    if response.stop_reason == "end_turn":
        return response.content[0].text

    # 도구 호출이 필요한 경우에는 요청된 도구를 실행합니다.
    if response.stop_reason == "tool_use":
        tool_block = next(b for b in response.content if b.type == "tool_use")

        # 모델이 만든 인자로 실제 도구 함수를 실행합니다.
        result = execute_tool(tool_block.name, tool_block.input)
        print(f"  [도구 실행] {tool_block.name}({tool_block.input}) → {result}")

        # 2차 호출: 도구 결과를 포함해 다시 모델에게 최종 답변을 요청합니다.
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_block.id, "content": result}],
        })

        final = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )
        return final.content[0].text

    return "예상치 못한 응답"


# 테스트 질문들입니다.
print("\n--- 날씨 질문 ---")
print(f"답변: {chat_with_tools('서울 날씨 어때?')}")

print("\n--- 계산 질문 ---")
print(f"답변: {chat_with_tools('2의 10승은 얼마야?')}")

print("\n--- 시간 질문 ---")
print(f"답변: {chat_with_tools('서울 지금 몇 시야?')}")

print("\n--- 일반 질문 (도구 불필요) ---")
print(f"답변: {chat_with_tools('AI Agent가 뭐야?')}")
