"""
Chapter 3-1: Tool Use 기본

Tool Use(Function Calling)란?
    LLM이 혼자 답하기 어렵거나 외부 계산이 필요한 질문에 대해,
    "이 도구를 이 인자로 호출해줘"라고 요청하는 메커니즘입니다.

    LLM은 도구를 직접 실행하지 않습니다.
    도구 호출을 "요청"할 뿐이고, 실제 실행은 Agent(우리 코드)가 합니다.

흐름:
    1. 개발자가 사용 가능한 도구 목록을 API에 전달 (tools 파라미터)
    2. LLM이 사용자 질문을 보고, 도구가 필요하면 tool_use 블록을 반환
    3. Agent(우리 코드)가 해당 도구를 실제로 실행
    4. 실행 결과를 tool_result로 LLM에 다시 전달
    5. LLM이 결과를 바탕으로 최종 답변 생성

    [User] → [LLM: "계산기 도구를 써야겠다"] → [Agent: 도구 실행] → [LLM: "답은 42입니다"]
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 1부: 도구 정의
# ============================================================
# 도구는 JSON Schema 형식으로 설명합니다.
# 모델은 이 설명을 읽고 어떤 도구를 어떤 인자로 요청할지 판단합니다.

print("=" * 60)
print("1부: 도구 정의와 기본 호출")
print("=" * 60)

# 간단한 계산기 도구 정의입니다.
tools = [
    {
        "name": "calculator",              # 모델이 tool_use에서 사용할 도구 이름입니다.
        "description": "두 숫자의 사칙연산을 수행합니다. 수학 계산이 필요할 때 사용하세요.",  # 모델이 도구 사용 시점을 판단하는 설명입니다.
        "input_schema": {                   # 도구가 받을 입력 형태입니다.
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "계산할 수학 표현식 (예: '2 + 3', '10 * 5')",
                },
            },
            "required": ["expression"],     # 이 값이 없으면 도구를 실행할 수 없습니다.
        },
    }
]

# 도구 정의의 핵심 요소:
#   - name: 도구 식별자. 모델이 이 이름으로 호출을 요청합니다.
#   - description: 모델이 "이 도구를 써야겠다"라고 판단하는 근거입니다.
#   - input_schema: 도구가 받을 인자 형태입니다. 모델은 이 스키마에 맞춰 인자를 만듭니다.


# ============================================================
# 2부: 도구가 포함된 API 호출
# ============================================================
# tools 파라미터로 도구를 전달하면, 모델이 필요할 때 tool_use 블록을 반환합니다.
print()
print("=" * 60)
print("2부: LLM의 도구 호출 요청")
print("=" * 60)

response = client.messages.create(
    model=MODEL,
    max_tokens=1024,
    tools=tools,        # 모델에게 사용 가능한 도구 목록을 알려줍니다.
    messages=[
        {"role": "user", "content": "127 곱하기 389는 얼마야?"}
    ],
)

# 응답 구조를 확인해 tool_use가 어떻게 생겼는지 봅니다.
print("\n[응답 전체 구조]")
print(f"stop_reason: {response.stop_reason}")  # "tool_use" ← 도구 호출을 위해 중단됨!
print(f"content 블록 수: {len(response.content)}")

for i, block in enumerate(response.content):
    print(f"\n  [블록 {i}] type: {block.type}")
    if block.type == "text":
        print(f"    text: {block.text}")
    elif block.type == "tool_use":
        print(f"    id: {block.id}")           # 도구 호출 고유 ID (결과 반환 시 필요)
        print(f"    name: {block.name}")        # 호출할 도구 이름
        print(f"    input: {block.input}")      # 도구에 전달할 인자

# stop_reason이 "tool_use"라는 뜻:
#   모델이 "여기서 잠깐 멈출 테니, 이 도구를 실행해서 결과를 알려줘"라고 요청한 것입니다.


# ============================================================
# 3부: 도구 실행 → 결과 반환 → 최종 답변
# ============================================================
# 이제 요청, 실행, 결과 반환, 최종 답변까지 한 번에 연결합니다.
print()
print("=" * 60)
print("3부: 전체 흐름 (요청 → 도구 실행 → 최종 답변)")
print("=" * 60)


def run_calculator(expression: str) -> str:
    """계산기 도구의 실제 구현입니다."""
    try:
        # 주의: eval은 보안 위험이 있으므로 실제 서비스에서는 사용하지 않습니다.
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"계산 오류: {e}"


# Step 1: 사용자 질문과 도구 정의를 함께 보냅니다.
print("\n[Step 1] 사용자 질문 전송")
messages = [
    {"role": "user", "content": "127 곱하기 389는 얼마야?"}
]

response = client.messages.create(
    model=MODEL,
    max_tokens=1024,
    tools=tools,
    messages=messages,
)
print(f"  stop_reason: {response.stop_reason}")

# Step 2: 모델이 도구 호출을 요청했는지 확인하고, 우리 코드가 실행합니다.
if response.stop_reason == "tool_use":
    # 응답 content 안에서 tool_use 블록을 찾습니다.
    tool_block = next(b for b in response.content if b.type == "tool_use")

    print(f"\n[Step 2] LLM이 도구 호출 요청")
    print(f"  도구: {tool_block.name}")
    print(f"  인자: {tool_block.input}")

    # 모델이 요청한 인자로 실제 Python 함수를 실행합니다.
    tool_result = run_calculator(tool_block.input["expression"])
    print(f"  실행 결과: {tool_result}")

    # Step 3: 도구 결과를 모델에게 반환합니다.
    # 이전 tool_use 응답과 그에 대한 tool_result를 messages에 순서대로 추가합니다.
    print(f"\n[Step 3] 도구 결과를 LLM에 전달")
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_block.id,   # 어떤 도구 호출의 결과인지 맞춰 줍니다.
                "content": tool_result,
            }
        ],
    })

    # Step 4: 모델이 도구 결과를 참고해 사용자에게 최종 답변합니다.
    final_response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )
    print(f"\n[Step 4] 최종 답변")
    print(f"  stop_reason: {final_response.stop_reason}")  # "end_turn"
    print(f"  답변: {final_response.content[0].text}")


# ============================================================
# 정리: Tool Use 메시지 흐름
# ============================================================
print()
print("=" * 60)
print("정리: Tool Use 메시지 흐름")
print("=" * 60)
print("""
[전체 흐름]

  User: "127 × 389는?"
    │
    ▼
  LLM 호출 (tools 포함)
    │
    ▼
  LLM 응답: stop_reason="tool_use"
    content: [
      TextBlock("계산해보겠습니다"),
      ToolUseBlock(name="calculator", input={"expression": "127 * 389"})
    ]
    │
    ▼
  Agent가 도구 실행: eval("127 * 389") → "49403"
    │
    ▼
  LLM 재호출 (tool_result 포함)
    messages: [...이전 대화, tool_result: "49403"]
    │
    ▼
  LLM 최종 응답: stop_reason="end_turn"
    "127 곱하기 389는 49,403입니다."

[핵심 포인트]
1. LLM은 도구를 직접 실행하지 않는다 — "호출 요청"만 한다
2. 도구 실행은 Agent(우리 코드)의 책임이다
3. tool_use_id로 요청과 결과를 매칭한다
4. stop_reason으로 도구 호출 여부를 판단한다
   - "tool_use": 도구 실행이 필요함 → 도구 실행 후 재호출
   - "end_turn": 최종 답변 완료
""")
