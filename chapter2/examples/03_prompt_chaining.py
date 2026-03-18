"""
Chapter 2-3: Prompt Chaining — 프롬프트 연쇄

복잡한 작업을 한 번에 시키면 품질이 떨어집니다.
작업을 여러 단계로 나누고, 각 단계의 출력을 다음 단계의 입력으로 연결합니다.

비유:
  한 번에 "에세이 써줘" vs "개요 잡아줘" → "본문 써줘" → "퇴고해줘"
  후자가 훨씬 좋은 결과를 냅니다.

Agent에서의 활용:
  Agent의 핵심 동작 방식 자체가 Prompt Chaining입니다.
  관찰 → 판단 → 행동 → 관찰... 각 단계가 별도의 LLM 호출입니다.
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-20250514"


def call_llm(system, user_message):
    """간단한 LLM 호출 헬퍼"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ============================================================
# 1부: 단일 호출 vs Prompt Chaining 비교
# ============================================================
print("=" * 60)
print("1부: 단일 호출 vs Prompt Chaining 비교")
print("=" * 60)

article = """인공지능 기술이 의료 분야에 혁신을 가져오고 있다.
특히 영상 진단에서 AI는 전문의 수준의 정확도를 보여주고 있으며,
조기 진단율을 30% 이상 높이는 성과를 거두었다.
그러나 의료 AI의 판단에 대한 법적 책임 소재가 불분명하고,
환자 데이터 프라이버시 문제도 여전히 과제로 남아있다.
또한 AI 진단 시스템 도입에 필요한 비용이 높아
소규모 병원에서는 접근이 어려운 실정이다."""

# --- 단일 호출: 모든 것을 한 번에 ---
print("\n--- 단일 호출 ---")
result = call_llm(
    system="",
    user_message=f"""다음 기사를 분석하여:
1) 핵심 요약 (1줄)
2) 찬성 논점과 반대 논점 정리
3) 종합 평가

기사:
{article}""",
)
print(result)

# --- Prompt Chaining: 3단계로 분리 ---
print("\n--- Prompt Chaining (3단계) ---")

# Step 1: 핵심 내용 추출
print("[Step 1] 핵심 내용 추출")
step1_result = call_llm(
    system="기사의 핵심 내용을 요약하세요. 주요 사실과 수치만 간결하게 정리하세요.",
    user_message=article,
)
print(f"  → {step1_result}\n")

# Step 2: 찬반 논점 분석 (Step 1 결과를 입력으로 사용)
print("[Step 2] 찬반 논점 분석")
step2_result = call_llm(
    system="""아래 요약을 바탕으로 찬성 논점과 반대 논점을 각각 정리하세요.
형식:
찬성: ...
반대: ...""",
    user_message=f"기사 요약:\n{step1_result}",
)
print(f"  → {step2_result}\n")

# Step 3: 종합 평가 (Step 1 + Step 2 결과를 입력으로 사용)
print("[Step 3] 종합 평가")
step3_result = call_llm(
    system="요약과 찬반 논점을 바탕으로 균형 잡힌 종합 평가를 2~3문장으로 작성하세요.",
    user_message=f"요약:\n{step1_result}\n\n논점 분석:\n{step2_result}",
)
print(f"  → {step3_result}")


# ============================================================
# 2부: 검증 체인 — 생성 후 검증
# ============================================================
# LLM이 생성한 결과를 다른 LLM 호출로 검증하는 패턴입니다.
# Agent에서 자기 검증(self-verification)으로 활용합니다.
print()
print("=" * 60)
print("2부: 검증 체인 (생성 → 검증)")
print("=" * 60)

# Step 1: 코드 생성
print("\n[Step 1] 코드 생성")
generated_code = call_llm(
    system="Python 함수를 작성하세요. 코드만 출력하세요.",
    user_message="리스트에서 중복을 제거하면서 원래 순서를 유지하는 함수",
)
print(f"  생성된 코드:\n{generated_code}\n")

# Step 2: 코드 검증
print("[Step 2] 코드 검증")
review = call_llm(
    system="""다음 코드를 검토하세요. 아래 항목을 확인하세요:
- 정확성: 의도대로 동작하는가?
- 엣지 케이스: 빈 리스트, 단일 원소 등 처리
- 개선점: 있다면 제안

검토 결과만 간결하게 작성하세요.""",
    user_message=generated_code,
)
print(f"  검토 결과:\n{review}")


# ============================================================
# 3부: 변환 체인 — 단계적 변환
# ============================================================
# 데이터를 여러 단계로 변환하는 파이프라인 패턴입니다.
print()
print("=" * 60)
print("3부: 변환 체인 (원문 → 번역 → 요약)")
print("=" * 60)

original = """Artificial intelligence is transforming how we approach
software development. Large language models can now write code,
review pull requests, and even debug complex systems. However,
the key challenge remains: ensuring AI-generated code is reliable,
secure, and maintainable in production environments."""

# Step 1: 번역
print("\n[Step 1] 번역")
translated = call_llm(
    system="영어를 한국어로 자연스럽게 번역하세요. 번역문만 출력하세요.",
    user_message=original,
)
print(f"  → {translated}\n")

# Step 2: 핵심 키워드 추출
print("[Step 2] 키워드 추출")
keywords = call_llm(
    system="텍스트에서 핵심 키워드 5개를 콤마로 구분하여 나열하세요. 키워드만 출력하세요.",
    user_message=translated,
)
print(f"  → {keywords}\n")

# Step 3: 한 줄 요약
print("[Step 3] 한 줄 요약")
summary = call_llm(
    system="텍스트를 한 문장으로 요약하세요.",
    user_message=translated,
)
print(f"  → {summary}")


# ============================================================
# 정리: Prompt Chaining 핵심
# ============================================================
print()
print("=" * 60)
print("정리: Prompt Chaining 핵심")
print("=" * 60)
print("""
1. 언제 체이닝하는가?
   - 작업이 2개 이상의 독립적인 하위 작업으로 나뉠 때
   - 한 번에 시키면 품질이 떨어지거나 형식이 불안정할 때
   - 중간 결과를 검증하거나 로깅해야 할 때

2. 체이닝 패턴
   - 순차 체인: A → B → C (분석 파이프라인)
   - 검증 체인: 생성 → 검증 → (수정) (자기 검증)
   - 분기 체인: A → B1 또는 B2 (조건부 분기)

3. 주의사항
   - 단계가 많을수록 API 호출 비용과 지연이 증가
   - 각 단계의 출력 형식을 명확히 지정해야 연결이 깔끔
   - 불필요한 분할은 오히려 비효율 → 적절한 단위로 나눌 것

4. Agent와의 관계
   - Agent 루프 자체가 Prompt Chaining의 확장
   - 관찰 → 추론(CoT) → 행동 → 관찰... 의 반복
   - Chapter 4의 ReAct = CoT + Prompt Chaining + Tool Use
""")
