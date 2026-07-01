"""
Chapter 1-6: 메시지 포맷 들여다보기

Agent와 LLM 사이에 오가는 메시지의 실제 모양을 확인합니다.
- 우리가 보내는 요청(Request)의 정확한 형태
- LLM이 돌려주는 응답(Response)의 정확한 형태
- 멀티턴 대화에서 메시지가 어떻게 쌓이는지
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 1부: 요청(Request) 메시지 포맷
# ============================================================
# API에 보내는 messages는 딕셔너리로 된 리스트입니다.
# 각 메시지에는 누가 말했는지(role)와 무엇을 말했는지(content)가 들어갑니다.
print("=" * 60)
print("1부: 요청(Request) 메시지 포맷")
print("=" * 60)

# 가장 단순한 형태는 user 메시지 하나만 보내는 것입니다.
messages = [
    {"role": "user", "content": "대한민국의 수도는?"}
]

print("[보내는 메시지]")
print(json.dumps(messages, ensure_ascii=False, indent=2))

response = client.messages.create(
    model=MODEL,
    max_tokens=128,
    messages=messages,
)
print(f"\n[받은 응답 텍스트]")
print(response.content[0].text)


# ============================================================
# 2부: 응답(Response) 객체 전체 구조
# ============================================================
# LLM의 응답도 문자열 하나가 아니라 여러 정보를 담은 객체입니다.
print()
print("=" * 60)
print("2부: 응답(Response) 객체 전체 구조")
print("=" * 60)

# response 객체를 딕셔너리로 바꿔 전체 구조를 눈으로 확인합니다.
response_dict = json.loads(response.to_json())
print(json.dumps(response_dict, ensure_ascii=False, indent=2))

# 핵심 구조 정리:
# {
#   "id": "msg_...",           ← 요청 고유 ID
#   "type": "message",         ← 항상 "message"
#   "role": "assistant",       ← 항상 "assistant"
#   "model": "claude-...",     ← 사용된 모델
#   "content": [               ← 응답 콘텐츠 (리스트!)
#     {
#       "type": "text",        ← 텍스트 블록
#       "text": "서울입니다."    ← 실제 응답 내용
#     }
#   ],
#   "stop_reason": "end_turn", ← 종료 이유
#   "usage": {                 ← 토큰 사용량
#     "input_tokens": 15,
#     "output_tokens": 8
#   }
# }


# ============================================================
# 3부: 멀티턴 대화의 메시지 흐름
# ============================================================
# 대화가 이어질수록 messages 리스트에는 user와 assistant 메시지가 차례대로 쌓입니다.
# 매 요청마다 이 전체 히스토리를 보내야 모델이 맥락을 따라올 수 있습니다.
print()
print("=" * 60)
print("3부: 멀티턴 대화의 메시지 흐름")
print("=" * 60)

conversation = []

# --- 턴 1 ---
user_msg_1 = "내 이름은 영찬이야."
conversation.append({"role": "user", "content": user_msg_1})

print(f"\n--- 턴 1: 요청 ---")
print(f"[보내는 messages] ({len(conversation)}개)")
print(json.dumps(conversation, ensure_ascii=False, indent=2))

response1 = client.messages.create(
    model=MODEL,
    max_tokens=256,
    messages=conversation,
)
assistant_msg_1 = response1.content[0].text
conversation.append({"role": "assistant", "content": assistant_msg_1})

print(f"\n[LLM 응답]")
print(assistant_msg_1)

# --- 턴 2 ---
user_msg_2 = "내 이름이 뭐라고 했지?"
conversation.append({"role": "user", "content": user_msg_2})

print(f"\n--- 턴 2: 요청 ---")
print(f"[보내는 messages] ({len(conversation)}개)")
print(json.dumps(conversation, ensure_ascii=False, indent=2))
# ↑ 턴 1의 대화가 함께 들어가 있으므로 모델이 이름을 참고할 수 있습니다.

response2 = client.messages.create(
    model=MODEL,
    max_tokens=256,
    messages=conversation,
)
assistant_msg_2 = response2.content[0].text
conversation.append({"role": "assistant", "content": assistant_msg_2})

print(f"\n[LLM 응답]")
print(assistant_msg_2)

# --- 턴 3 ---
user_msg_3 = "내 이름을 거꾸로 말해봐."
conversation.append({"role": "user", "content": user_msg_3})

print(f"\n--- 턴 3: 요청 ---")
print(f"[보내는 messages] ({len(conversation)}개)")
print(json.dumps(conversation, ensure_ascii=False, indent=2))
# ↑ 턴 1, 2의 대화가 모두 누적되어 있는지 확인하세요.

response3 = client.messages.create(
    model=MODEL,
    max_tokens=256,
    messages=conversation,
)
assistant_msg_3 = response3.content[0].text
conversation.append({"role": "assistant", "content": assistant_msg_3})

print(f"\n[LLM 응답]")
print(assistant_msg_3)


# ============================================================
# 정리: 메시지 포맷의 핵심 규칙
# ============================================================
print()
print("=" * 60)
print("정리: 메시지 포맷의 핵심 규칙")
print("=" * 60)
print("""
1. messages는 딕셔너리의 리스트: [{"role": "...", "content": "..."}, ...]
2. role은 "user"와 "assistant" 두 가지 (system은 별도 파라미터)
3. user와 assistant가 반드시 번갈아 와야 함
4. 응답의 content는 리스트 (여러 블록이 올 수 있음)
5. 매 요청마다 전체 대화 히스토리를 보내야 맥락이 유지됨
   → LLM은 기억하지 않으므로, "기억"은 우리가 만드는 것!

[요청 흐름 시각화]

  턴 1: [ U1 ]                    → A1
  턴 2: [ U1, A1, U2 ]            → A2
  턴 3: [ U1, A1, U2, A2, U3 ]    → A3
         ~~~~~~~~~~~~~~~~~~~~~~
         매번 전체를 다시 보냄!
""")
