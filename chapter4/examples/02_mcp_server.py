"""
Chapter 4-2: MCP 서버 만들기

MCP 서버는 도구(Tools)를 외부에 제공하는 독립 프로세스입니다.
이 파일 자체가 하나의 MCP 서버입니다.

핵심 포인트:
    - @mcp.tool() 데코레이터로 함수를 도구로 노출
    - 함수의 타입 힌트와 독스트링이 자동으로 JSON Schema로 변환됨
      → Ch3에서 수동 작성했던 input_schema를 자동 생성!
    - mcp.run()으로 서버 실행

실행 방법:
    python chapter4/examples/02_mcp_server.py

    이 서버는 stdio 전송을 사용합니다.
    직접 실행하면 입력 대기 상태가 됩니다.
    03_mcp_client.py에서 이 서버에 연결합니다.
"""

import json
from datetime import datetime, timezone, timedelta
from mcp.server.fastmcp import FastMCP

# MCP 서버 생성
# name: 서버 식별자 (클라이언트가 연결 시 확인)
mcp = FastMCP("weather-tools")


# ============================================================
# 도구 정의: @mcp.tool() 데코레이터
# ============================================================
# Ch3에서는 JSON Schema를 수동으로 작성했지만,
# MCP에서는 함수의 타입 힌트와 독스트링에서 자동 생성됩니다.
#
# Ch3 방식:
#   tools = [{
#       "name": "get_weather",
#       "description": "날씨를 조회합니다",
#       "input_schema": {
#           "type": "object",
#           "properties": {"city": {"type": "string", ...}},
#           "required": ["city"]
#       }
#   }]
#
# MCP 방식:
#   @mcp.tool()
#   def get_weather(city: str) -> str:
#       """날씨를 조회합니다"""  ← 이것만으로 위 JSON Schema가 자동 생성!


@mcp.tool()
def get_weather(city: str) -> str:
    """특정 도시의 현재 날씨 정보를 가져옵니다.

    Args:
        city: 날씨를 조회할 도시 이름 (예: '서울', '부산', '제주')
    """
    weather_data = {
        "서울": {"temp": 12, "condition": "맑음", "humidity": 45},
        "부산": {"temp": 15, "condition": "흐림", "humidity": 60},
        "제주": {"temp": 18, "condition": "비", "humidity": 80},
        "도쿄": {"temp": 14, "condition": "맑음", "humidity": 40},
        "뉴욕": {"temp": 8, "condition": "눈", "humidity": 70},
    }
    data = weather_data.get(city)
    if data:
        return json.dumps(data, ensure_ascii=False)
    return f"'{city}'의 날씨 정보를 찾을 수 없습니다. 지원 도시: {', '.join(weather_data.keys())}"


@mcp.tool()
def calculator(expression: str) -> str:
    """수학 계산을 수행합니다. 사칙연산, 거듭제곱 등을 처리합니다.

    Args:
        expression: 계산할 수학 표현식 (예: '2 + 3', '10 ** 2')
    """
    try:
        # 주의: eval은 보안 위험이 있으므로 학습용으로만 사용
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"계산 오류: {e}"


@mcp.tool()
def get_exchange_rate(from_currency: str, to_currency: str, amount: float = 1.0) -> str:
    """두 통화 간의 환율을 조회하고 금액을 변환합니다.

    Args:
        from_currency: 원본 통화 코드 (예: 'USD', 'EUR', 'JPY')
        to_currency: 대상 통화 코드 (예: 'KRW', 'USD')
        amount: 변환할 금액 (기본값: 1.0)
    """
    rates = {
        ("USD", "KRW"): 1350.50,
        ("EUR", "KRW"): 1450.30,
        ("JPY", "KRW"): 9.15,
        ("KRW", "USD"): 0.00074,
        ("KRW", "JPY"): 0.109,
    }
    pair = (from_currency.upper(), to_currency.upper())
    rate = rates.get(pair)
    if rate:
        converted = amount * rate
        return json.dumps({
            "from": pair[0], "to": pair[1],
            "rate": rate, "amount": amount,
            "result": round(converted, 2),
        }, ensure_ascii=False)
    return f"'{pair[0]} → {pair[1]}' 환율 정보를 찾을 수 없습니다."


@mcp.tool()
def get_time(city: str) -> str:
    """특정 도시의 현재 날짜와 시간을 알려줍니다.

    Args:
        city: 시간을 조회할 도시 이름
    """
    tz_offsets = {
        "서울": 9, "부산": 9, "제주": 9,
        "도쿄": 9, "뉴욕": -5, "런던": 0,
    }
    offset = tz_offsets.get(city)
    if offset is not None:
        tz = timezone(timedelta(hours=offset))
        now = datetime.now(tz)
        return json.dumps({
            "city": city,
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": f"UTC{'+' if offset >= 0 else ''}{offset}",
        }, ensure_ascii=False)
    return f"'{city}'의 시간대 정보를 찾을 수 없습니다."


# ============================================================
# 서버 실행
# ============================================================
# mcp.run()은 stdio 전송으로 서버를 시작합니다.
# 클라이언트(03_mcp_client.py)가 이 프로세스를 실행하고 통신합니다.
if __name__ == "__main__":
    mcp.run()
