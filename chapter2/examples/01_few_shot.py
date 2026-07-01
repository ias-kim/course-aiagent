"""
Chapter 2-1: Few-shot Prompting (In-context Learning)

In-context Learning이란?
  모델을 다시 학습시키지 않고, 프롬프트 안에 예시를 넣는 것만으로
  모델의 행동을 유도하는 기법입니다.
  모델 자체는 바뀌지 않고, 이번 입력에 포함된 문맥만 보고 패턴을 따라 합니다.

예시 개수에 따른 분류:
  - Zero-shot: 예시 없이 지시만 (예: "감성을 분류하세요")
  - One-shot: 예시 1개를 함께 제공
  - Few-shot: 예시 2~5개를 함께 제공

주의:
  "학습"이라는 표현이 붙지만, 모델이 실제로 학습하는 것은 아닙니다.
  매번 호출할 때마다 예시를 함께 보내야 동일한 효과를 얻을 수 있습니다.

Agent에서의 활용:
  입력 → 출력 패턴을 예시로 정의하면, 별도 파싱 로직 없이도
  LLM이 일관된 형식으로 응답하게 만들 수 있습니다.
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 1부: Zero-shot vs Few-shot 비교
# ============================================================
# 같은 감성 분류 작업을 예시 없이 할 때와 예시를 줄 때로 비교합니다.

print("=" * 60)
print("1부: Zero-shot vs Few-shot 비교")
print("=" * 60)

target_text = "배송이 하루만에 왔는데 포장이 찢어져 있었어요"

# --- Zero-shot: 예시 없이 지시만 전달 ---
print("\n--- Zero-shot ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=100,
    messages=[{
        "role": "user",
        "content": f"다음 리뷰의 감성을 '긍정', '부정', '혼합' 중 하나로 분류하세요.\n\n리뷰: {target_text}",
    }],
)
print(f"응답: {response.content[0].text}")
# → 정답은 맞출 수 있지만, 설명이 붙거나 표현이 달라질 수 있습니다.
# → 코드에서 자동 처리하려면 이런 흔들림이 문제가 됩니다.

# --- Few-shot: 예시를 먼저 보여주고 실제 문제를 맡김 ---
# user/assistant 메시지 쌍으로 "이런 입력에는 이렇게 답해"라는 패턴을 보여줍니다.
# 마지막 질문은 그 패턴을 이어받아 같은 형식으로 답하기를 기대합니다.
print("\n--- Few-shot ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=100,
    messages=[
        # 예시 1: 긍정 리뷰는 "긍정"만 답하게 합니다.
        {"role": "user", "content": "리뷰: 정말 좋은 제품이에요! 추천합니다."},
        {"role": "assistant", "content": "긍정"},
        # 예시 2: 부정 리뷰도 한 단어로 답하게 합니다.
        {"role": "user", "content": "리뷰: 품질이 너무 안 좋고 환불도 어렵네요."},
        {"role": "assistant", "content": "부정"},
        # 예시 3: 장단점이 섞인 리뷰의 기준을 보여줍니다.
        {"role": "user", "content": "리뷰: 기능은 좋은데 가격이 너무 비싸요."},
        {"role": "assistant", "content": "혼합"},
        # 실제로 분류할 입력입니다.
        {"role": "user", "content": f"리뷰: {target_text}"},
    ],
)
print(f"응답: {response.content[0].text}")
# → 예시 덕분에 "혼합"처럼 짧고 일정한 형식의 답을 기대할 수 있습니다.


# ============================================================
# 2부: Few-shot으로 출력 형식 통제
# ============================================================
# "키워드를 추출해줘"라고만 하면 쉼표 목록, 문장, 해시태그 등 형식이 흔들릴 수 있습니다.
# 예시로 "#태그 #형식"을 보여주면 원하는 출력 스타일을 더 안정적으로 얻습니다.
print()
print("=" * 60)
print("2부: Few-shot으로 출력 형식 통제")
print("=" * 60)

print("\n--- 키워드 추출 (태그 형식) ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=100,
    messages=[
        # 예시 1: 뉴스 문장에서 핵심 단어를 해시태그로 변환합니다.
        {"role": "user", "content": "텍스트: 오늘 서울에 폭우가 내려 지하철 운행이 지연되고 있습니다."},
        {"role": "assistant", "content": "#서울 #폭우 #지하철 #운행지연"},
        # 예시 2: 같은 형식을 한 번 더 보여줘 패턴을 강화합니다.
        {"role": "user", "content": "텍스트: 삼성전자가 신형 갤럭시를 출시하며 AI 기능을 대폭 강화했다."},
        {"role": "assistant", "content": "#삼성전자 #갤럭시 #출시 #AI"},
        # 실제로 키워드를 뽑을 문장입니다.
        {"role": "user", "content": "텍스트: 정부가 내년도 교육 예산을 늘려 초등학교 코딩 교육을 의무화한다."},
    ],
)
print(f"응답: {response.content[0].text}")
# → 예시와 같은 해시태그 형식으로 응답하기를 기대합니다.


# ============================================================
# 3부: Few-shot + System Prompt 조합
# ============================================================
# System Prompt는 역할과 규칙을 잡고,
# Few-shot 예시는 실제 입력과 출력의 모양을 보여줍니다.
# 둘을 함께 쓰면 역할과 형식이 모두 안정됩니다.
print()
print("=" * 60)
print("3부: System Prompt + Few-shot 조합")
print("=" * 60)

print("\n--- SQL 쿼리 생성기 ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=200,
    system="""당신은 자연어를 SQL 쿼리로 변환하는 변환기입니다.
테이블: users (id, name, age, city, created_at)
SQL 쿼리만 출력하세요. 설명은 하지 마세요.""",
    messages=[
        # 예시 1: 자연어 요청이 SQL로 바뀌는 패턴을 보여줍니다.
        {"role": "user", "content": "서울에 사는 사용자 목록"},
        {"role": "assistant", "content": "SELECT * FROM users WHERE city = '서울';"},
        # 예시 2: 집계 쿼리도 같은 방식으로 보여줍니다.
        {"role": "user", "content": "30살 이상 사용자 수"},
        {"role": "assistant", "content": "SELECT COUNT(*) FROM users WHERE age >= 30;"},
        # 실제로 SQL로 바꿀 요청입니다.
        {"role": "user", "content": "최근 가입한 부산 사용자 5명"},
    ],
)
print(f"응답: {response.content[0].text}")


# ============================================================
# 정리: Few-shot Prompting 핵심
# ============================================================
print()
print("=" * 60)
print("정리: Few-shot Prompting 핵심")
print("=" * 60)
print("""
1. 예시 개수 가이드
   - Zero-shot: 간단한 작업, LLM이 이미 잘 아는 경우
   - 1~2개: 출력 형식을 맞추고 싶을 때
   - 3~5개: 패턴이 복잡하거나 일관성이 중요할 때
   - 너무 많으면 토큰 낭비 → 적절한 균형 필요

2. 좋은 예시의 조건
   - 실제 사용 케이스와 유사할 것
   - 다양한 케이스를 커버할 것 (긍정/부정/혼합 모두 포함)
   - 출력 형식이 일관될 것

3. 주의사항
   - Few-shot은 "학습"이 아닙니다 — 매 호출마다 예시를 포함해야 합니다
   - 예시가 많을수록 input 토큰이 늘어나 비용이 증가합니다
   - 구조화된 출력이 필요하면 Ch1-8의 Structured Output도 함께 고려하세요

4. Agent에서의 활용
   - 도구 선택 패턴을 예시로 보여줄 수 있음
   - System Prompt(역할) + Few-shot(형식) = 가장 안정적인 조합
""")
