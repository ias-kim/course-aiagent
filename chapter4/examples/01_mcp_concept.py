"""
Chapter 4-1: MCP 개념 이해

MCP(Model Context Protocol)란?
    AI 모델이 외부 도구/데이터에 접근하는 방식을 표준화한 프로토콜입니다.
    Anthropic이 주도하는 오픈 표준으로, "AI의 USB-C"에 비유할 수 있습니다.

왜 MCP가 필요한가?
    Ch3에서 Tool Use를 직접 구현했을 때의 문제점:

    1) 도구마다 매번 JSON Schema를 수동 정의해야 함
    2) 도구 실행 코드를 Agent 내부에 직접 작성해야 함
    3) 다른 Agent에서 같은 도구를 쓰려면 코드를 복사해야 함
    4) 도구가 늘어날수록 Agent 코드가 비대해짐

    MCP의 해결책:
    ┌──────────┐      표준 프로토콜      ┌──────────┐
    │  Agent   │ ◄──── (MCP) ────► │ MCP 서버 │ ← 도구/데이터 제공
    │(클라이언트)│                      │          │
    └──────────┘                      └──────────┘

    - 도구를 MCP 서버로 분리 → Agent와 독립적으로 관리
    - 표준화된 인터페이스 → 어떤 Agent든 같은 방식으로 연결
    - 커뮤니티 MCP 서버 → 남이 만든 도구를 바로 가져다 쓸 수 있음

Ch3(Tool Use) vs Ch4(MCP) 비교:

    Ch3 방식 (직접 구현):
        Agent 코드 안에 도구 정의 + 실행 로직이 모두 포함
        → 단일 프로젝트에서 빠르게 프로토타이핑할 때 적합

    Ch4 방식 (MCP):
        도구는 별도 MCP 서버로 분리, Agent는 연결만
        → 도구 재사용, 팀 협업, 프로덕션 환경에 적합

MCP의 핵심 구성 요소:

    1) MCP 서버 (Server)
       - 도구(Tools), 리소스(Resources), 프롬프트(Prompts)를 제공
       - 독립 프로세스로 실행됨

    2) MCP 클라이언트 (Client)
       - 서버에 연결하여 도구 목록 조회, 도구 호출
       - Agent가 클라이언트 역할을 함

    3) 전송 계층 (Transport)
       - stdio: 로컬 프로세스 간 통신 (가장 간단)
       - SSE/HTTP: 원격 서버와 통신

    [Agent] ─── MCP Client ─── Transport ─── MCP Server ─── [도구/데이터]

이 파일은 개념 설명용이며 실행 코드는 없습니다.
다음 예제(02)부터 실제 MCP 서버와 클라이언트를 구현합니다.
"""


# ============================================================
# Ch3 vs Ch4 코드 비교 (개념 이해용)
# ============================================================

# --- Ch3 방식: 도구를 Agent 내부에 직접 구현 ---
ch3_example = """
# Agent 코드 안에 모든 것이 포함됨
tools = [
    {
        "name": "get_weather",
        "description": "날씨 조회",
        "input_schema": { ... }       # ← 직접 정의
    }
]

def execute_tool(name, input):        # ← 직접 구현
    if name == "get_weather":
        return call_weather_api(input["city"])

response = client.messages.create(
    tools=tools,                       # ← 직접 전달
    messages=[...]
)
"""

# --- Ch4 방식: 도구를 MCP 서버로 분리 ---
ch4_example = """
# MCP 서버 (별도 파일: weather_server.py)
@mcp.tool()
def get_weather(city: str) -> str:
    return call_weather_api(city)       # ← 서버가 도구 제공

# Agent (클라이언트)
tools = await session.list_tools()     # ← 서버에서 도구 목록 자동 조회
result = await session.call_tool(      # ← 서버에 실행 요청
    "get_weather", {"city": "서울"}
)
"""

# 출력
print("=" * 60)
print("Chapter 4-1: MCP 개념 이해")
print("=" * 60)

print("\n[Ch3 방식 — 도구를 직접 구현]")
print(ch3_example)

print("[Ch4 방식 — MCP로 분리]")
print(ch4_example)

print("=" * 60)
print("핵심 차이")
print("=" * 60)
print("""
┌────────────────┬─────────────────────┬──────────────────────┐
│                │ Ch3 (Tool Use)      │ Ch4 (MCP)            │
├────────────────┼─────────────────────┼──────────────────────┤
│ 도구 위치      │ Agent 코드 내부      │ 별도 MCP 서버         │
│ 도구 정의      │ JSON Schema 수동작성 │ 데코레이터로 자동생성  │
│ 도구 재사용    │ 코드 복사            │ 서버 연결만 하면 됨    │
│ 커뮤니티 도구  │ 직접 구현 필요       │ npm/pip 설치 후 연결   │
│ 적합한 상황    │ 프로토타이핑         │ 프로덕션, 팀 협업      │
└────────────────┴─────────────────────┴──────────────────────┘

다음 예제에서 MCP 서버를 직접 만들어봅니다 → 02_mcp_server.py
""")
