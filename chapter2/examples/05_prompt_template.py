"""
Chapter 2-5: Prompt Template — 재사용 가능한 프롬프트 설계

실제 Agent 개발에서는 프롬프트 문장을 매번 새로 쓰지 않습니다.
변수를 넣을 수 있는 템플릿을 만들고, 상황에 맞는 값을 채워 넣습니다.

비유:
  편지지 양식(템플릿)에 수신자 이름(변수)을 채우는 것과 같습니다.
  양식은 하나지만, 수신자마다 다른 편지가 됩니다.

Agent에서의 활용:
  - 도구 선택 프롬프트: 사용 가능한 도구 목록을 동적으로 삽입
  - 컨텍스트 주입: 검색 결과, 사용자 정보를 프롬프트에 포함
  - 다국어 지원: 언어 변수만 바꿔서 같은 로직 재사용
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 1부: 기본 템플릿 — f-string 활용
# ============================================================
print("=" * 60)
print("1부: 기본 템플릿 (f-string)")
print("=" * 60)

# --- 간단한 변수 치환: 언어와 분석 유형을 함수 인자로 바꿔 끼웁니다.
def analyze_text(text, language="한국어", analysis_type="감성 분석"):
    """분석 언어와 분석 종류를 바꿔 쓸 수 있는 템플릿입니다."""
    system_template = f"""당신은 {language} 텍스트 분석 전문가입니다.
주어진 텍스트에 대해 {analysis_type}을 수행하세요.
결과만 간결하게 출력하세요."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=system_template,
        messages=[{"role": "user", "content": text}],
    )
    return response.content[0].text


# 같은 함수라도 변수만 바꾸면 다른 작업에 재사용할 수 있습니다.
print("\n--- 같은 텍스트, 다른 분석 ---")
sample = "이 영화는 스토리는 좋았는데 연기가 아쉬웠다."

result1 = analyze_text(sample, analysis_type="감성 분석")
print(f"  감성 분석: {result1}")

result2 = analyze_text(sample, analysis_type="키워드 추출")
print(f"  키워드 추출: {result2}")


# ============================================================
# 2부: 컨텍스트 주입 템플릿
# ============================================================
# Agent의 핵심 패턴 중 하나는 외부 정보를 프롬프트에 동적으로 끼워 넣는 것입니다.
print()
print("=" * 60)
print("2부: 컨텍스트 주입 템플릿")
print("=" * 60)

# --- 검색 결과 주입: RAG의 기본 원리를 작은 예제로 확인합니다.
print("\n--- 검색 결과를 프롬프트에 주입 ---")

# 실제 서비스에서는 DB나 검색 엔진에서 가져오지만, 여기서는 리스트로 흉내 냅니다.
search_results = [
    {"title": "Python 3.13 릴리스 노트", "content": "Python 3.13에서는 GIL 제거 실험적 지원이 추가되었습니다."},
    {"title": "Python 성능 개선", "content": "JIT 컴파일러 도입으로 일부 워크로드에서 최대 30% 성능 향상이 보고되었습니다."},
]


def answer_with_context(question, context_docs):
    """검색 결과를 참고 문서로 넣어 답변하게 만드는 QA 템플릿입니다."""
    # 검색 결과 리스트를 모델이 읽기 쉬운 텍스트로 바꿉니다.
    context_text = "\n\n".join(
        f"[문서 {i+1}] {doc['title']}\n{doc['content']}"
        for i, doc in enumerate(context_docs)
    )

    system_template = f"""아래 참고 문서를 바탕으로 질문에 답변하세요.

참고 문서:
{context_text}

규칙:
- 참고 문서에 있는 정보만 사용하세요.
- 문서에 없는 내용은 "제공된 문서에서 확인할 수 없습니다"라고 답하세요.
- 어떤 문서를 참고했는지 명시하세요."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=system_template,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text


result = answer_with_context("Python 3.13의 주요 변경사항은?", search_results)
print(f"  응답: {result}")


# ============================================================
# 3부: 조건부 템플릿 — 상황에 따라 프롬프트 구성 변경
# ============================================================
# 사용자 유형, 주문 상태, 이전 대화 등에 따라 프롬프트를 조립합니다.
# Agent에서는 현재 상태에 맞춰 System Prompt 일부가 달라지는 일이 많습니다.
print()
print("=" * 60)
print("3부: 조건부 템플릿")
print("=" * 60)


def customer_support(user_message, user_tier="일반", has_order=False, order_info=None):
    """사용자 등급과 주문 상태에 따라 System Prompt를 다르게 만드는 예시입니다."""

    # 모든 고객에게 공통으로 적용되는 기본 역할입니다.
    system_parts = ["당신은 고객 지원 챗봇입니다."]

    # 사용자 등급에 따라 응대 우선순위와 톤을 바꿉니다.
    if user_tier == "VIP":
        system_parts.append("이 고객은 VIP입니다. 최우선으로 응대하고, 추가 혜택을 안내하세요.")
    elif user_tier == "신규":
        system_parts.append("이 고객은 신규 가입자입니다. 친절하고 상세하게 안내하세요.")

    # 주문 정보가 있으면 모델이 참고할 수 있도록 프롬프트에 넣습니다.
    if has_order and order_info:
        system_parts.append(f"""
고객의 주문 정보:
- 주문번호: {order_info['id']}
- 상품: {order_info['item']}
- 상태: {order_info['status']}
- 주문일: {order_info['date']}""")

    system_parts.append("\n간결하게 응답하세요.")

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system="\n".join(system_parts),
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# 같은 질문이라도 사용자 상태가 다르면 답변이 달라집니다.
print("\n--- 일반 고객 (주문 정보 없음) ---")
result = customer_support("주문한 상품이 언제 오나요?", user_tier="일반")
print(f"  응답: {result}")

print("\n--- VIP 고객 (주문 정보 있음) ---")
result = customer_support(
    "주문한 상품이 언제 오나요?",
    user_tier="VIP",
    has_order=True,
    order_info={"id": "ORD-2024-1234", "item": "맥북 프로 M4", "status": "배송 중", "date": "2024-12-20"},
)
print(f"  응답: {result}")


# ============================================================
# 정리: Prompt Template 핵심
# ============================================================
print()
print("=" * 60)
print("정리: Prompt Template 핵심")
print("=" * 60)
print("""
1. 템플릿 설계 원칙
   - 변하는 부분(변수)과 변하지 않는 부분(구조)을 분리
   - 변수에 들어갈 수 있는 값의 범위를 고려
   - 변수가 비어있을 때의 기본값 처리

2. 주요 활용 패턴
   - 변수 치환: 분석 유형, 언어 등을 파라미터로 전환
   - 컨텍스트 주입: 검색 결과, DB 조회 결과를 프롬프트에 삽입 (RAG의 기본 원리)
   - 조건부 구성: 사용자 상태에 따라 프롬프트를 동적으로 조립

3. Agent 개발에서의 위치
   - Agent의 모든 LLM 호출은 사실상 템플릿 기반
   - 현재 상태(대화 히스토리, 도구 결과, 사용자 정보)를 프롬프트에 주입하는 것이 핵심
""")
