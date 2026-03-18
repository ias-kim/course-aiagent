"""
Chapter 2-1: Few-shot Prompting

LLM에게 몇 가지 예시를 보여주면, 패턴을 학습하여 원하는 형식과 스타일로 응답합니다.
- Zero-shot: 예시 없이 지시만
- One-shot: 예시 1개
- Few-shot: 예시 2~5개

Agent에서의 활용:
  입력 → 출력 패턴을 예시로 정의하면, 별도 파싱 로직 없이도
  LLM이 일관된 형식으로 응답하게 만들 수 있습니다.
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-20250514"


# ============================================================
# 1부: Zero-shot vs Few-shot 비교
# ============================================================
# 같은 작업(감성 분류)을 예시 유무에 따라 비교합니다.

print("=" * 60)
print("1부: Zero-shot vs Few-shot 비교")
print("=" * 60)

target_text = "배송이 하루만에 왔는데 포장이 찢어져 있었어요"

# --- Zero-shot: 지시만 ---
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
# → 긴 설명과 함께 답변할 수 있음 (형식 불일치)

# --- Few-shot: 예시를 함께 제공 ---
print("\n--- Few-shot ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=100,
    messages=[
        # 예시 1: 긍정
        {"role": "user", "content": "리뷰: 정말 좋은 제품이에요! 추천합니다."},
        {"role": "assistant", "content": "긍정"},
        # 예시 2: 부정
        {"role": "user", "content": "리뷰: 품질이 너무 안 좋고 환불도 어렵네요."},
        {"role": "assistant", "content": "부정"},
        # 예시 3: 혼합
        {"role": "user", "content": "리뷰: 기능은 좋은데 가격이 너무 비싸요."},
        {"role": "assistant", "content": "혼합"},
        # 실제 분류 대상
        {"role": "user", "content": f"리뷰: {target_text}"},
    ],
)
print(f"응답: {response.content[0].text}")
# → "혼합" 한 단어로 일관되게 응답


# ============================================================
# 2부: Few-shot으로 출력 형식 통제
# ============================================================
# 예시를 통해 복잡한 출력 형식도 유도할 수 있습니다.
print()
print("=" * 60)
print("2부: Few-shot으로 출력 형식 통제")
print("=" * 60)

print("\n--- 키워드 추출 (태그 형식) ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=100,
    messages=[
        # 예시 1
        {"role": "user", "content": "텍스트: 오늘 서울에 폭우가 내려 지하철 운행이 지연되고 있습니다."},
        {"role": "assistant", "content": "#서울 #폭우 #지하철 #운행지연"},
        # 예시 2
        {"role": "user", "content": "텍스트: 삼성전자가 신형 갤럭시를 출시하며 AI 기능을 대폭 강화했다."},
        {"role": "assistant", "content": "#삼성전자 #갤럭시 #출시 #AI"},
        # 실제 추출 대상
        {"role": "user", "content": "텍스트: 정부가 내년도 교육 예산을 늘려 초등학교 코딩 교육을 의무화한다."},
    ],
)
print(f"응답: {response.content[0].text}")
# → "#정부 #교육 #예산 #코딩 #의무화" 형식으로 응답


# ============================================================
# 3부: Few-shot + System Prompt 조합
# ============================================================
# System Prompt로 역할을 설정하고, Few-shot으로 형식을 정의하면
# 가장 안정적인 출력을 얻을 수 있습니다.
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
        # 예시 1
        {"role": "user", "content": "서울에 사는 사용자 목록"},
        {"role": "assistant", "content": "SELECT * FROM users WHERE city = '서울';"},
        # 예시 2
        {"role": "user", "content": "30살 이상 사용자 수"},
        {"role": "assistant", "content": "SELECT COUNT(*) FROM users WHERE age >= 30;"},
        # 실제 변환 대상
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
1. 예시 개수
   - Zero-shot: 간단한 작업, LLM이 이미 잘 아는 경우
   - 1~2개: 출력 형식을 맞추고 싶을 때
   - 3~5개: 패턴이 복잡하거나 일관성이 중요할 때
   - 너무 많으면 토큰 낭비 → 적절한 균형 필요

2. 좋은 예시의 조건
   - 실제 사용 케이스와 유사할 것
   - 다양한 케이스를 커버할 것 (긍정/부정/혼합 모두 포함)
   - 출력 형식이 일관될 것

3. Agent에서의 활용
   - 도구 선택 패턴을 예시로 보여줄 수 있음
   - 구조화된 출력(Ch1-8)과 결합하면 매우 강력
   - System Prompt(역할) + Few-shot(형식) = 가장 안정적인 조합
""")
