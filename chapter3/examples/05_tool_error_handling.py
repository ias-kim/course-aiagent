"""
Chapter 3-5: 도구 에러 처리

도구 실행은 외부 API, 입력값, 권한 문제 때문에 언제든 실패할 수 있습니다.
- API 서버 다운
- 잘못된 입력값
- 타임아웃
- 권한 부족

Agent는 도구 실패 시 다음 두 가지를 해야 합니다.
    1) 에러 정보를 LLM에게 알려주고
    2) LLM이 대안을 찾거나 사용자에게 안내하도록 해야 합니다.

핵심: tool_result에 is_error=True를 설정하면,
      LLM이 에러 상황을 인식하고 적절히 대응합니다.
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 에러 처리를 실험할 도구 정의입니다.
# ============================================================
tools = [
    {
        "name": "get_stock_price",
        "description": "주식 종목의 현재 가격을 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "주식 종목 코드 (예: 'AAPL', '005930')",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_company_info",
        "description": "기업의 기본 정보(업종, 시가총액 등)를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "종목 코드"},
            },
            "required": ["symbol"],
        },
    },
]


# ============================================================
# 1부: 일부러 성공과 실패가 모두 나오도록 도구를 구현합니다.
# ============================================================
print("=" * 60)
print("1부: 도구 에러 시뮬레이션")
print("=" * 60)


def execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """
    도구 실행 결과와 에러 여부를 함께 반환합니다.

    Returns:
        (결과 문자열, 에러 여부)
    """
    if name == "get_stock_price":
        symbol = tool_input["symbol"]
        # 일부 종목만 지원하고, 나머지는 에러로 처리합니다.
        prices = {
            "AAPL": {"price": 178.50, "change": "+1.2%"},
            "005930": {"price": 72000, "change": "-0.5%"},
        }
        if symbol in prices:
            return json.dumps(prices[symbol], ensure_ascii=False), False
        else:
            # 에러 케이스도 문자열로 구체적인 원인을 알려줍니다.
            return f"오류: 종목 코드 '{symbol}'을 찾을 수 없습니다. 유효한 종목 코드를 확인해주세요.", True

    elif name == "get_company_info":
        symbol = tool_input["symbol"]
        infos = {
            "AAPL": {"name": "Apple Inc.", "sector": "Technology", "market_cap": "2.8T USD"},
            "005930": {"name": "삼성전자", "sector": "반도체/전자", "market_cap": "430조원"},
        }
        if symbol in infos:
            return json.dumps(infos[symbol], ensure_ascii=False), False
        else:
            return f"오류: '{symbol}'에 대한 기업 정보가 없습니다.", True

    return f"알 수 없는 도구: {name}", True


# ============================================================
# 2부: is_error를 포함해 에러를 모델에게 알려주는 Agent 루프입니다.
# ============================================================
print()
print("=" * 60)
print("2부: 에러 처리가 포함된 Agent 루프")
print("=" * 60)


def agent_loop(user_message: str, max_iterations: int = 10) -> str:
    """도구 성공/실패를 모두 처리하는 Agent 루프입니다."""
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

                    # 도구 실행 결과와 에러 여부를 함께 받습니다.
                    result, is_error = execute_tool(block.name, block.input)

                    if is_error:
                        print(f"  [에러] {result}")
                    else:
                        print(f"  [결과] {result}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                        "is_error": is_error,  # 핵심: 모델에게 이 결과가 실패인지 알려줍니다.
                    })

            messages.append({"role": "user", "content": tool_results})

    return "최대 반복 초과"


# ============================================================
# 테스트
# ============================================================

# --- 테스트 1: 정상적으로 결과를 받는 경우 ---
print("\n" + "=" * 60)
print("테스트 1: 정상 호출")
print("=" * 60)
print("질문: 애플(AAPL) 주가 알려줘")
result = agent_loop("애플(AAPL) 주가 알려줘")
print(f"\n최종 답변:\n{result}")

# --- 테스트 2: 도구가 실패하고 모델이 사용자에게 안내하는 경우 ---
print("\n" + "=" * 60)
print("테스트 2: 존재하지 않는 종목")
print("=" * 60)
print("질문: XYZABC 주가 알려줘")
result = agent_loop("XYZABC 주가 알려줘")
print(f"\n최종 답변:\n{result}")
# → 모델이 "종목을 찾을 수 없다"는 에러를 보고 사용자에게 설명합니다.

# --- 테스트 3: 일부 도구 호출은 성공하고 일부는 실패하는 경우 ---
print("\n" + "=" * 60)
print("테스트 3: 삼성전자와 알 수 없는 종목 비교")
print("=" * 60)
print("질문: 삼성전자(005930)와 LG전자(066570) 주가를 비교해줘")
result = agent_loop("삼성전자(005930)와 LG전자(066570) 주가를 비교해줘")
print(f"\n최종 답변:\n{result}")
# → 모델은 성공한 정보와 실패한 정보를 구분해 부분 결과로 답변합니다.


# ============================================================
# 정리
# ============================================================
print()
print("=" * 60)
print("정리: 도구 에러 처리")
print("=" * 60)
print("""
[is_error 플래그]

  # 성공
  {"type": "tool_result", "tool_use_id": "...", "content": "결과"}

  # 실패 — is_error: True 추가
  {"type": "tool_result", "tool_use_id": "...", "content": "오류 메시지", "is_error": True}

  → LLM은 is_error=True를 보고:
    - 사용자에게 에러를 안내하거나
    - 다른 도구/방법을 시도하거나
    - 부분 결과로 답변을 구성합니다

[에러 처리 베스트 프랙티스]

1. 에러 메시지는 구체적으로
   ✗ "오류 발생"
   ✓ "종목 코드 'XYZ'를 찾을 수 없습니다. 유효한 코드를 확인해주세요."
   → LLM이 원인을 파악하고 더 나은 대응 가능

2. 도구 실행을 try-except로 감싸기
   → 예상치 못한 예외도 안전하게 처리

3. is_error를 정직하게 설정
   → LLM이 에러를 성공으로 오인하면 잘못된 답변 생성

4. 타임아웃 설정
   → 도구가 무한 대기하지 않도록 제한
""")
