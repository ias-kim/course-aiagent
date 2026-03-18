"""
Chapter 2-2: Chain of Thought (CoT) — 단계적 추론

LLM에게 "단계별로 생각하라"고 지시하면 복잡한 문제의 정답률이 크게 올라갑니다.

왜 효과적인가?
  LLM은 다음 토큰을 예측하는 모델입니다.
  중간 과정 없이 바로 답을 내면 "추론 없는 추측"이 됩니다.
  단계별 사고를 유도하면 각 단계가 다음 단계의 맥락이 되어
  더 정확한 결론에 도달합니다.

Agent에서의 활용:
  Agent가 복잡한 판단(도구 선택, 계획 수립)을 할 때
  CoT로 추론 과정을 명시하게 하면 디버깅과 신뢰성이 높아집니다.
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-20250514"


# ============================================================
# 1부: 일반 응답 vs CoT 비교
# ============================================================
print("=" * 60)
print("1부: 일반 응답 vs CoT 비교")
print("=" * 60)

problem = """학교에 학생이 450명 있습니다.
남학생이 여학생보다 30명 많습니다.
여학생 중 40%가 안경을 쓰고 있습니다.
안경을 쓴 여학생은 몇 명입니까?"""

# --- 일반 응답 ---
print("\n--- 일반 응답 ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=256,
    messages=[{"role": "user", "content": problem}],
)
print(response.content[0].text)

# --- CoT 적용 ---
print("\n--- Chain of Thought 적용 ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=512,
    messages=[{
        "role": "user",
        "content": f"{problem}\n\n단계별로 풀어주세요.",
    }],
)
print(response.content[0].text)
# → 각 단계가 명시되어 검증 가능


# ============================================================
# 2부: CoT 유도 기법들
# ============================================================
# CoT를 유도하는 다양한 방법을 비교합니다.
print()
print("=" * 60)
print("2부: CoT 유도 기법들")
print("=" * 60)

task = "다음 코드의 출력을 예측하세요: print([x**2 for x in range(5) if x % 2 == 0])"

# 기법 1: "단계별로 생각하세요" (가장 간단)
print("\n--- 기법 1: 단계별로 생각하세요 ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=512,
    messages=[{
        "role": "user",
        "content": f"{task}\n\n단계별로 생각하세요.",
    }],
)
print(response.content[0].text)

# 기법 2: 추론 구조 지정 (더 구체적)
print("\n--- 기법 2: 추론 구조 지정 ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=512,
    system="""문제를 풀 때 다음 구조로 응답하세요:
[분석] 문제에서 주어진 정보 정리
[풀이] 단계별 풀이 과정
[답] 최종 답""",
    messages=[{"role": "user", "content": task}],
)
print(response.content[0].text)


# ============================================================
# 3부: CoT + 구조화된 출력
# ============================================================
# Agent에서는 추론 과정과 최종 결과를 모두 구조화하여 받으면
# 추론 과정은 로깅하고, 결과만 코드에서 활용할 수 있습니다.
print()
print("=" * 60)
print("3부: CoT + 구조화된 출력 (Agent 패턴)")
print("=" * 60)

print("\n--- 의사결정 Agent ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=512,
    system="""당신은 고객 문의를 분류하는 Agent입니다.
문의를 분석하고 아래 JSON 형식으로만 응답하세요.

{
  "reasoning": "단계별 추론 과정",
  "category": "환불|배송|제품문의|기술지원|기타",
  "priority": "high|medium|low",
  "suggested_action": "추천 대응 방법"
}""",
    messages=[{
        "role": "user",
        "content": "3일 전에 주문한 노트북이 아직 배송되지 않았고, 내일 발표가 있어서 급합니다.",
    }],
)

raw = response.content[0].text
print(f"LLM 원본 응답:\n{raw}\n")

result = json.loads(raw)
print(f"추론 과정: {result['reasoning']}")
print(f"분류: {result['category']}")
print(f"우선순위: {result['priority']}")
print(f"추천 대응: {result['suggested_action']}")


# ============================================================
# 정리: Chain of Thought 핵심
# ============================================================
print()
print("=" * 60)
print("정리: Chain of Thought 핵심")
print("=" * 60)
print("""
1. 언제 CoT를 사용하는가?
   - 수학, 논리, 코드 분석 등 추론이 필요한 작업
   - 여러 조건을 종합해 판단해야 할 때
   - Agent가 도구 선택이나 계획 수립을 할 때

2. CoT 유도 방법
   - 간단: "단계별로 생각하세요"
   - 구체적: 추론 구조를 지정 ([분석] → [풀이] → [답])
   - 구조화: JSON의 "reasoning" 필드로 추론과 결과 분리

3. Agent에서의 핵심 가치
   - 추론 과정이 명시되면 디버깅이 쉬워진다
   - "왜 이 도구를 선택했는가?"를 추적할 수 있다
   - Chapter 4의 ReAct 패턴의 기반이 된다
""")
