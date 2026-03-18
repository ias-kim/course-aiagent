"""
Chapter 2-5: Prompt Template — 재사용 가능한 프롬프트 설계

실제 Agent 개발에서는 프롬프트를 하드코딩하지 않습니다.
변수를 포함한 템플릿을 만들고, 상황에 따라 값을 채워 넣습니다.

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
MODEL = "claude-sonnet-4-20250514"


# ============================================================
# 1부: 기본 템플릿 — f-string 활용
# ============================================================
print("=" * 60)
print("1부: 기본 템플릿 (f-string)")
print("=" * 60)

# --- 간단한 변수 치환 ---
def analyze_text(text, language="한국어", analysis_type="감성 분석"):
    """텍스트 분석 템플릿"""
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


# 같은 함수, 다른 분석
print("\n--- 같은 텍스트, 다른 분석 ---")
sample = "이 영화는 스토리는 좋았는데 연기가 아쉬웠다."

result1 = analyze_text(sample, analysis_type="감성 분석")
print(f"  감성 분석: {result1}")

result2 = analyze_text(sample, analysis_type="키워드 추출")
print(f"  키워드 추출: {result2}")


# ============================================================
# 2부: 컨텍스트 주입 템플릿
# ============================================================
# Agent의 핵심 패턴: 외부 정보를 프롬프트에 동적으로 삽입
print()
print("=" * 60)
print("2부: 컨텍스트 주입 템플릿")
print("=" * 60)

# --- 검색 결과 주입 (RAG의 기본 원리) ---
print("\n--- 검색 결과를 프롬프트에 주입 ---")

# 실제로는 DB나 검색 엔진에서 가져오지만, 여기서는 시뮬레이션
search_results = [
    {"title": "Python 3.13 릴리스 노트", "content": "Python 3.13에서는 GIL 제거 실험적 지원이 추가되었습니다."},
    {"title": "Python 성능 개선", "content": "JIT 컴파일러 도입으로 일부 워크로드에서 최대 30% 성능 향상이 보고되었습니다."},
]


def answer_with_context(question, context_docs):
    """검색 결과를 컨텍스트로 주입하는 QA 템플릿"""
    # 검색 결과를 텍스트로 변환
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
# 3부: 도구 선택 템플릿 (Agent 핵심 패턴)
# ============================================================
# Agent가 사용 가능한 도구 목록을 동적으로 프롬프트에 삽입하여
# 상황에 맞는 도구를 선택하게 합니다.
print()
print("=" * 60)
print("3부: 도구 선택 템플릿 (Agent 핵심 패턴)")
print("=" * 60)

# 사용 가능한 도구 정의
available_tools = [
    {"name": "search", "description": "웹에서 정보를 검색합니다", "params": "query: 검색어"},
    {"name": "calculator", "description": "수학 계산을 수행합니다", "params": "expression: 수식"},
    {"name": "weather", "description": "날씨 정보를 조회합니다", "params": "city: 도시명"},
]


def select_tool(user_request, tools):
    """사용자 요청에 적합한 도구를 선택하는 템플릿"""
    # 도구 목록을 텍스트로 변환
    tools_text = "\n".join(
        f"- {t['name']}: {t['description']} (파라미터: {t['params']})"
        for t in tools
    )

    system_template = f"""사용 가능한 도구:
{tools_text}

사용자 요청을 분석하고, 적합한 도구를 선택하세요.
응답 형식 (JSON만 출력):
{{"tool": "도구명", "params": {{"파라미터명": "값"}}, "reason": "선택 이유"}}

적합한 도구가 없으면:
{{"tool": "none", "params": {{}}, "reason": "이유"}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=system_template,
        messages=[{"role": "user", "content": user_request}],
    )
    return response.content[0].text


# 여러 요청으로 테스트
test_requests = [
    "서울 날씨 어때?",
    "15% 할인하면 85000원짜리 얼마야?",
    "최신 AI 뉴스 알려줘",
    "노래 추천해줘",  # 적합한 도구 없음
]

for req in test_requests:
    result = select_tool(req, available_tools)
    print(f"\n  요청: {req}")
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
   - 컨텍스트 주입: 검색 결과, DB 조회 결과를 프롬프트에 삽입
   - 도구 선택: 사용 가능한 도구 목록을 동적으로 구성
   - 다국어/다목적: 언어, 분석 유형 등을 변수로 전환

3. Agent 개발에서의 위치
   - Agent의 모든 LLM 호출은 사실상 템플릿 기반
   - Chapter 3 Tool Use: 도구 정의를 프롬프트에 자동 삽입
   - Chapter 4 ReAct: 관찰 결과를 프롬프트에 주입하여 다음 행동 결정
""")
