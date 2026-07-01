"""
Chapter 1-5: LLM은 기억하지 못한다 → Agent의 필요성

LLM API 호출은 기본적으로 서로 독립적입니다 (stateless).
이전 대화를 기억하지 못하기 때문에, 대화 맥락을 유지하려면
우리가 직접 메시지 히스토리를 관리해야 합니다.

이것이 바로 "Agent"의 가장 기본적인 출발점입니다.
Agent = LLM + 메모리(대화 히스토리) + 루프
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"

# ============================================================
# 1부: LLM은 기억하지 못한다 (Stateless)
# ============================================================
print("=" * 60)
print("1부: LLM은 기억하지 못한다")
print("=" * 60)

# 첫 번째 호출: 모델에게 이름을 알려줍니다.
response1 = client.messages.create(
    model=MODEL,
    max_tokens=256,
    messages=[
        {"role": "user", "content": "내 이름은 영찬이야. 기억해줘!"}
    ],
)
print(f"[1번 호출] 사용자: 내 이름은 영찬이야. 기억해줘!")
print(f"[1번 호출] Claude: {response1.content[0].text}")

# 두 번째 호출: 다시 이름을 물어봅니다. 이전 요청과 연결하지 않으면 기억하지 못합니다.
# API 입장에서는 방금 전 호출과 완전히 별개의 새 요청이기 때문입니다.
response2 = client.messages.create(
    model=MODEL,
    max_tokens=256,
    messages=[
        {"role": "user", "content": "내 이름이 뭐였지?"}
    ],
)
print(f"\n[2번 호출] 사용자: 내 이름이 뭐였지?")
print(f"[2번 호출] Claude: {response2.content[0].text}")
# → 이전 대화를 보내지 않았으므로 모른다고 답하거나 다른 이름을 말할 수 있습니다.

# ============================================================
# 2부: 메시지 히스토리로 기억 만들기
# ============================================================
# 해결책은 이전 대화를 messages에 함께 넣어 보내는 것입니다.
# 정확히 말하면 LLM이 기억하는 것이 아니라, 매 호출마다 전체 대화를 다시 읽는 방식입니다.
print()
print("=" * 60)
print("2부: 메시지 히스토리로 기억 만들기")
print("=" * 60)

response3 = client.messages.create(
    model=MODEL,
    max_tokens=256,
    messages=[
        # 1번 호출에서 오갔던 대화를 그대로 포함합니다.
        {"role": "user", "content": "내 이름은 영찬이야. 기억해줘!"},
        {"role": "assistant", "content": response1.content[0].text},
        # 그 뒤에 이번 질문을 이어 붙입니다.
        {"role": "user", "content": "내 이름이 뭐였지?"},
    ],
)
print(f"[히스토리 포함] 사용자: 내 이름이 뭐였지?")
print(f"[히스토리 포함] Claude: {response3.content[0].text}")
# → 이번에는 히스토리 안에 이름이 있으므로 올바르게 답할 가능성이 높습니다.

# ============================================================
# 3부: 간단한 Agent 루프
# ============================================================
# 위 패턴을 자동화하면 Agent의 기본 구조가 됩니다.
#
#   Agent = while 루프 + 메시지 히스토리 + LLM 호출
#
#   [사용자 입력] → [히스토리에 추가] → [LLM 호출] → [응답을 히스토리에 추가] → 반복
print()
print("=" * 60)
print("3부: 간단한 Agent 루프 (종료하려면 'quit' 입력)")
print("=" * 60)

conversation_history = []  # 지금까지의 user/assistant 메시지를 순서대로 저장합니다.

while True:
    user_input = input("\n사용자: ")
    if user_input.strip().lower() == "quit":
        print("대화를 종료합니다.")
        break

    # 새 사용자 메시지를 히스토리에 추가합니다.
    conversation_history.append({"role": "user", "content": user_input})

    # 누적된 전체 히스토리를 함께 보내야 모델이 대화 맥락을 이해합니다.
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=conversation_history,  # 누적된 전체 대화를 매번 다시 보냅니다.
    )

    assistant_message = response.content[0].text

    # AI 응답도 저장해야 다음 턴에서 자연스럽게 이어집니다.
    conversation_history.append({"role": "assistant", "content": assistant_message})

    print(f"Claude: {assistant_message}")

    # 히스토리가 길어질수록 입력 토큰도 함께 늘어난다는 점을 확인합니다.
    print(f"  [히스토리: {len(conversation_history)}개 메시지, "
          f"토큰 사용: 입력 {response.usage.input_tokens} / 출력 {response.usage.output_tokens}]")
