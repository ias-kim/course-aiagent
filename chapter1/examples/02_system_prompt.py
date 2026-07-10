"""
Chapter 1-2: System Prompt 활용

System prompt로 AI의 역할과 행동 규칙을 지정합니다.
같은 사용자 질문도 system prompt가 달라지면 말투, 깊이, 예시 방식이 달라집니다.

- system 파라미터의 역할
- 동일한 질문, 다른 system prompt → 다른 응답
"""

# ============================================================
# 프롬프트의 종류와 권한 계층
# ============================================================
#
# AI Agent를 만들 때 LLM에 전달되는 정보는 크게 3가지로 볼 수 있습니다.
# 핵심은 "누가 넣은 지시인가"입니다. 작성 주체에 따라 우선순위와 쓰임이 달라집니다.
#
# ┌─────────────────────────────────────────────────────────────┐
# │  1. System Prompt (시스템 프롬프트) — 개발자 영역            │
# │     - 작성자: 개발자 (앱을 만드는 사람)                      │
# │     - 위치: messages.create()의 system 파라미터              │
# │     - 역할: AI의 성격, 규칙, 제약 조건을 정함                │
# │     - 우선순위: 사용자 메시지보다 높은 수준의 지시             │
# │     - 특징: 보통 UI에 표시하지 않지만, 비밀 저장소는 아님       │
# │     - 예: "당신은 친절한 선생님입니다. 욕설에 응하지 마세요." │
# ├─────────────────────────────────────────────────────────────┤
# │  2. User Prompt (사용자 프롬프트) — 사용자 영역              │
# │     - 작성자: 최종 사용자 (앱을 쓰는 사람)                   │
# │     - 위치: messages의 role="user" 메시지                    │
# │     - 역할: 질문, 요청, 지시 등 사용자의 의도 전달            │
# │     - 권한: system prompt의 규칙 안에서만 동작                │
# │     - 예: "Python에서 리스트와 튜플의 차이가 뭐야?"           │
# ├─────────────────────────────────────────────────────────────┤
# │  3. Context (컨텍스트) — 동적으로 주입되는 정보               │
# │     - 작성자: 시스템이 자동 생성 (개발자가 로직 설계)         │
# │     - 위치: messages 내에 포함 (히스토리, 검색 결과 등)       │
# │     - 역할: LLM이 답할 때 참고할 자료                         │
# │     - 종류:                                                  │
# │       · 대화 히스토리 — 이전 대화 내용 (05, 06번 예제)        │
# │       · 검색 결과(RAG) — 외부 DB/문서에서 가져온 정보         │
# │       · 도구 실행 결과 — 함수 호출 결과 (Chapter 4에서 다룸)  │
# │     - 예: [이전 대화] "내 이름은 영찬이야" → "영찬님 반갑..."│
# └─────────────────────────────────────────────────────────────┘
#
# 지시 우선순위:
#   System Prompt > User Prompt
#
#   → 사용자가 "지금부터 규칙을 무시해"라고 해도 모델은
#     system prompt의 상위 지시를 우선하도록 설계되어 있습니다.
#   → 단, 프롬프트만으로 보안이 완성되지는 않습니다.
#     권한 검사와 민감 정보 보호는 애플리케이션 코드에서도 해야 합니다.
#
# Claude API에서는 이렇게 연결됩니다:
#   client.messages.create(
#       system="...",       ← (1) System Prompt
#       messages=[
#           {...history...}, ← (3) Context (대화 히스토리)
#           {"role": "user", "content": "..."}, ← (2) User Prompt
#       ],
#   )
#

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()

# 세 예제 모두 같은 질문을 사용합니다.
# 달라지는 것은 오직 system prompt뿐입니다.
user_message = "Python에서 리스트와 튜플의 차이가 뭐야?"

# --- 예시 1: system prompt 없이 질문만 보낼 때 ---
# 모델의 기본 응답 스타일을 관찰합니다.
print("=== System Prompt 없음 ===")
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": user_message}],
)
print(response.content[0].text)

# --- 예시 2: 친절한 한국어 선생님 역할을 줄 때 ---
# 초보자에게 맞춘 비유와 쉬운 설명을 유도합니다.
print("\n=== 친절한 선생님 역할 ===")
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="당신은 프로그래밍을 처음 배우는 학생을 가르치는 친절한 선생님입니다. 비유를 들어 쉽게 설명하세요.",
    messages=[{"role": "user", "content": user_message}],
)
print(response.content[0].text)

# --- 예시 3: 시니어 개발자 역할을 줄 때 ---
# 같은 질문이라도 실무 관점과 정확성을 더 강조하도록 유도합니다.
print("\n=== 시니어 개발자 역할 ===")
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="당신은 10년차 시니어 Python 개발자입니다. 기술적으로 정확하고 간결하게 답변하되, 실무에서의 best practice를 함께 알려주세요.",
    messages=[{"role": "user", "content": user_message}],
)
print(response.content[0].text)
