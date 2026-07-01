"""
Chapter 3-4: 순차 도구 호출 (Tool Chaining)

LLM이 첫 번째 도구 결과를 보고 다음 도구를 이어서 호출하는 패턴입니다.

예시:
    "서울 날씨에 맞는 옷을 추천해줘"
    1) get_weather("서울") → "12°C, 맑음"
    2) LLM이 12도를 보고 → recommend_clothing("12", "맑음")
    3) 최종 답변: "가벼운 자켓을 추천합니다"

이것이 가능한 이유:
    Agent 루프(Ch3-3)가 stop_reason=="tool_use"인 동안 반복하기 때문에,
    LLM은 이전 도구 결과를 바탕으로 다음 도구를 자유롭게 호출할 수 있습니다.

    → 개발자가 순서를 하드코딩하지 않아도, LLM이 스스로 판단합니다.
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 순차 호출이 자연스럽게 일어나는 도구 세트입니다.
# 검색 결과의 product_id가 상세 조회 도구의 입력으로 이어집니다.
# ============================================================
tools = [
    {
        "name": "search_product",
        "description": "키워드로 상품을 검색합니다. 카테고리는 선택사항입니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "상품 카테고리 (예: '전자기기', '의류', '식품')",
                },
                "keyword": {
                    "type": "string",
                    "description": "검색 키워드",
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "get_product_detail",
        "description": "상품 ID로 상세 정보(가격, 재고, 평점)를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "상품 고유 ID",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "calculator",
        "description": "수학 계산을 수행합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "수학 표현식"},
            },
            "required": ["expression"],
        },
    },
]


# ============================================================
# 도구 실행 함수입니다. 실제 쇼핑몰 API 대신 더미 데이터를 사용합니다.
# ============================================================
def execute_tool(name: str, tool_input: dict) -> str:
    if name == "search_product":
        # 키워드 검색 결과를 흉내 냅니다.
        keyword = tool_input["keyword"]
        products = {
            "노트북": [
                {"id": "PROD-001", "name": "MacBook Air M3", "price_hint": "1,690,000원"},
                {"id": "PROD-002", "name": "Galaxy Book4 Pro", "price_hint": "1,490,000원"},
            ],
            "이어폰": [
                {"id": "PROD-010", "name": "AirPods Pro 2", "price_hint": "359,000원"},
                {"id": "PROD-011", "name": "Galaxy Buds3 Pro", "price_hint": "329,000원"},
            ],
        }
        results = products.get(keyword, [{"id": "PROD-999", "name": f"{keyword} 관련 상품", "price_hint": "가격 미정"}])
        return json.dumps(results, ensure_ascii=False)

    elif name == "get_product_detail":
        # 상품 ID로 상세 정보를 조회하는 상황을 흉내 냅니다.
        details = {
            "PROD-001": {"name": "MacBook Air M3", "price": 1690000, "stock": 15, "rating": 4.8, "discount": 5},
            "PROD-002": {"name": "Galaxy Book4 Pro", "price": 1490000, "stock": 8, "rating": 4.6, "discount": 10},
            "PROD-010": {"name": "AirPods Pro 2", "price": 359000, "stock": 50, "rating": 4.7, "discount": 0},
            "PROD-011": {"name": "Galaxy Buds3 Pro", "price": 329000, "stock": 0, "rating": 4.5, "discount": 15},
        }
        detail = details.get(tool_input["product_id"], {"name": "알 수 없는 상품"})
        return json.dumps(detail, ensure_ascii=False)

    elif name == "calculator":
        try:
            # 주의: eval은 보안 위험이 있으므로 실제 서비스에서는 사용하지 않습니다.
            return str(eval(tool_input["expression"]))
        except Exception as e:
            return f"오류: {e}"

    return f"알 수 없는 도구: {name}"


# ============================================================
# Ch3-3의 Agent 루프 패턴을 그대로 사용합니다.
# ============================================================
def agent_loop(user_message: str, max_iterations: int = 10) -> str:
    """도구 호출이 끝날 때까지 반복하는 Tool Use Agent 루프입니다."""
    messages = [{"role": "user", "content": user_message}]
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n  --- 반복 {iteration} ---")

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if b.type == "text"), "")

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [도구] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                    result = execute_tool(block.name, block.input)
                    print(f"  [결과] {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})

    return "최대 반복 초과"


# ============================================================
# 테스트: 순차 도구 호출 관찰
# ============================================================
# 모델이 이전 도구 결과를 보고 다음 도구를 고르는 과정을 관찰합니다.

# --- 테스트 1: 검색 → 상세 조회 ---
print("=" * 60)
print("테스트 1: 검색 → 상세 조회 (2단계)")
print("=" * 60)
print("질문: 노트북 추천해줘. 가장 평점 높은 걸로 상세 정보 알려줘.")
result = agent_loop("노트북 추천해줘. 가장 평점 높은 걸로 상세 정보 알려줘.")
print(f"\n최종 답변:\n{result}")

# 예상 흐름은 다음과 같습니다.
#   반복 1: search_product("노트북") → [PROD-001, PROD-002]
#   반복 2: get_product_detail("PROD-001") → {rating: 4.8, ...}
#   반복 3: 최종 답변

# --- 테스트 2: 검색 → 상세 조회 → 계산 (3단계) ---
print("\n" + "=" * 60)
print("테스트 2: 검색 → 상세 → 할인 계산 (3단계)")
print("=" * 60)
print("질문: 이어폰 검색해서 할인율이 가장 높은 제품의 할인된 가격을 계산해줘.")
result = agent_loop("이어폰 검색해서 할인율이 가장 높은 제품의 할인된 가격을 계산해줘.")
print(f"\n최종 답변:\n{result}")

# 예상 흐름은 다음과 같습니다.
#   반복 1: search_product("이어폰") → [PROD-010, PROD-011]
#   반복 2: get_product_detail("PROD-010"), get_product_detail("PROD-011")
#   반복 3: calculator("329000 * (1 - 15/100)")
#   반복 4: 최종 답변


# ============================================================
# 정리
# ============================================================
print()
print("=" * 60)
print("정리: 순차 도구 호출")
print("=" * 60)
print("""
[핵심 포인트]

1. LLM이 도구 호출 순서를 스스로 결정한다
   - 개발자가 "먼저 검색하고 그 다음 상세 조회해"라고 하드코딩하지 않음
   - LLM이 이전 도구 결과를 보고 다음 행동을 판단

2. Agent 루프가 이를 가능하게 한다
   - stop_reason=="tool_use"면 계속 반복
   - 각 반복에서 LLM은 전체 대화 히스토리(이전 도구 결과 포함)를 참고

3. 도구 설계가 중요하다
   - search_product → ID 목록 반환 → get_product_detail이 ID를 받음
   - 도구 간 입출력이 자연스럽게 연결되도록 설계해야 함

4. 이 패턴이 실제 Agent의 핵심이다
   - 웹 검색 → 페이지 읽기 → 요약
   - DB 조회 → 분석 → 보고서 작성
   - 파일 탐색 → 코드 읽기 → 수정
""")
