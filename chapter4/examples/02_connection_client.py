"""
Chapter 4-2: MCP 연결 절차 확인용 - 추적 클라이언트

Host(Client)와 MCP Server 간 연결 절차를 단계별로 추적합니다.

전체 흐름:
    1) Transport 수립          - stdio_client() 로 자식 프로세스 실행
    2) 세션 생성               - ClientSession 준비
    3) initialize 핸드셰이크    - 프로토콜 버전 협상, capabilities 교환
    4) initialized 알림 전송    - "나 준비됐어" (Notification, 응답 없음)
    5) Discovery               - list_resources / list_tools / list_prompts

실행:
    python chapter4/examples/02_connection_client.py
"""

import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import (
    CreateMessageResult,
    ElicitResult,
    ListRootsResult,
    Root,
    TextContent,
)

# Windows 콘솔에서 한글/유니코드 출력
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SERVER_PATH = str(Path(__file__).parent / "02_connection_server.py")


# ============================================================
# 클라이언트 capabilities 콜백 (서버 -> 클라이언트 요청 처리)
# ============================================================
# 콜백을 등록하면 해당 capability가 자동으로 활성화됩니다.
# 데모용이라 실제 동작은 최소화 (로깅 + 더미 응답).


async def sampling_callback(context, params):
    """서버가 LLM 호출을 요청할 때 실행됨 (sampling/createMessage).

    실제 구현에서는 여기서 Claude/GPT 등의 LLM API를 호출하고
    결과를 서버에 돌려줍니다.
    """
    print("\n  [Client.sampling] 서버가 LLM 호출 요청")
    print(f"     모델 선호: {params.modelPreferences}")
    return CreateMessageResult(
        role="assistant",
        content=TextContent(type="text", text="(데모 클라이언트의 sampling 응답)"),
        model="demo-model",
        stopReason="endTurn",
    )


async def elicitation_callback(context, params):
    """서버가 사용자 입력을 요청할 때 실행됨 (elicitation/create).

    실제 구현에서는 여기서 UI 다이얼로그/CLI 프롬프트를 띄워
    사용자 입력을 받아 서버에 돌려줍니다.
    """
    print("\n  [Client.elicitation] 서버가 사용자 입력 요청")
    print(f"     메시지: {getattr(params, 'message', '(없음)')}")
    return ElicitResult(action="decline")  # 데모: 자동 거절


async def list_roots_callback(context):
    """서버가 클라이언트의 파일 루트 목록을 요청할 때 실행됨 (roots/list)."""
    print("\n  [Client.roots] 서버가 파일 루트 목록 요청")
    return ListRootsResult(roots=[
        Root(uri="file:///demo/project", name="Demo Project"),
    ])


def section(title: str) -> None:
    """섹션 헤더 출력"""
    print()
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)


def dump(label: str, obj) -> None:
    """객체를 JSON으로 덤프"""
    print(f"\n  [{label}]")
    try:
        # Pydantic 모델이면 model_dump 사용
        if hasattr(obj, "model_dump"):
            data = obj.model_dump()
        else:
            data = obj
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    except Exception:
        print(f"  {obj!r}")


async def main():
    print("\n" + "=" * 70)
    print(" Chapter 4-2: MCP 연결 절차 추적")
    print("=" * 70)
    print(f" 대상 서버: {SERVER_PATH}")

    # ============================================================
    # 1단계: Transport 수립 (stdio)
    # ============================================================
    section("1단계: Transport 수립")
    print("""
          stdio_client()는 다음을 수행합니다:
          - sys.executable로 서버 파일을 자식 프로세스로 실행
          - 서버의 stdin/stdout을 파이프로 연결
          - (read, write) 스트림을 반환 (JSON-RPC 메시지 송수신용)
    """)

    # MCP 서버를 Stdio 방식으로 구동
    # sys.executable: 선택 python Path + 명령어
    # SERVER_PATH: 실행 MCP 서버 코드 파일명    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_PATH],
    )
    print(f"  command: {server_params.command}")
    print(f"  args:    {server_params.args}")

    # 설정 서버 구동 후 stdio로 서버와 연결 수립
    # read: server -> client
    # write: client -> server
    async with stdio_client(server_params) as (read, write):
        print("\n  -> Transport 수립 완료 (서버 프로세스 기동됨)")

        # ============================================================
        # 2단계: 세션 생성 (+ 클라이언트 capabilities 등록)
        # ============================================================
        section("2단계: 세션 생성 (ClientSession + 클라이언트 capabilities)")
        print("""
  ClientSession은 JSON-RPC 요청/응답을 관리하는 계층입니다.
    - 요청 id 자동 증가
    - 응답 매칭
    - Notification 처리

  콜백을 등록하면 해당 capability가 자동 활성화됩니다:
    - sampling_callback     -> sampling capability      (LLM 호출 위임)
    - elicitation_callback  -> elicitation capability   (사용자 입력 중개)
    - list_roots_callback   -> roots capability         (파일 루트 제공)
""")

        async with ClientSession(
            read,
            write,
            sampling_callback=sampling_callback,
            elicitation_callback=elicitation_callback,
            list_roots_callback=list_roots_callback,
        ) as session:
            print("  -> 세션 객체 생성됨 (sampling/elicitation/roots 콜백 등록)")

            # ============================================================
            # 3단계: initialize 핸드셰이크
            # ============================================================
            section("3단계: initialize 핸드셰이크")
            print("""
  클라이언트 -> 서버:
    {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "initialize",
      "params": {
        "protocolVersion": "...",
        "capabilities": { ... },        <- 클라이언트가 지원하는 기능
        "clientInfo": { "name": ..., "version": ... }
      }
    }

  서버 -> 클라이언트 (응답):
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "protocolVersion": "...",
        "capabilities": { ... },        <- 서버가 지원하는 기능
        "serverInfo": { "name": ..., "version": ... }
      }
    }
""")

            init_result = await session.initialize()
            print("  -> initialize 응답 수신")
            dump("서버가 반환한 initialize 결과", init_result)

            # ============================================================
            # 4단계: Discovery - Resources
            # ============================================================
            section("4단계: Discovery (1) - resources/list")
            print("""
  클라이언트 -> 서버:
    { "jsonrpc": "2.0", "id": 2, "method": "resources/list" }
""")
            resources = await session.list_resources()
            dump("등록된 Resources", resources)

            templates = await session.list_resource_templates()
            dump("Resource Templates (URI 파라미터가 있는 것)", templates)

            # ============================================================
            # 4단계: Discovery - Tools
            # ============================================================
            section("4단계: Discovery (2) - tools/list")
            print("""
  클라이언트 -> 서버:
    { "jsonrpc": "2.0", "id": 3, "method": "tools/list" }

  응답의 inputSchema가 Claude API의 tools 파라미터로 사용됨.
""")
            tools = await session.list_tools()
            dump("등록된 Tools", tools)

            # ============================================================
            # 4단계: Discovery - Prompts
            # ============================================================
            section("4단계: Discovery (3) - prompts/list")
            print("""
  클라이언트 -> 서버:
    { "jsonrpc": "2.0", "id": 4, "method": "prompts/list" }
""")
            prompts = await session.list_prompts()
            dump("등록된 Prompts", prompts)

            # ============================================================
            # 5단계: 정리
            # ============================================================
            section("5단계: 연결 절차 요약")
            print("""
  [확인된 내용]

  1) Transport: stdio (로컬 자식 프로세스, stdin/stdout JSON-RPC)

  2) 양방향 capabilities 협상:

     [Client -> Server 호출 가능 (서버 capabilities)]
        - tools        : 도구 호출
        - resources    : 데이터 읽기
        - prompts      : 대화 템플릿

     [Server -> Client 호출 가능 (클라이언트 capabilities)]
        - sampling     : LLM 추론 위임
        - elicitation  : 사용자 입력 중개
        - roots        : 파일 루트 제공

  3) Discovery로 수집된 목록:
     - Resources   : 데이터 읽기  (Application-controlled)
     - Tools       : 행동 수행    (Model-controlled)
     - Prompts     : 대화 템플릿  (User-controlled)

  [핵심 포인트]
     양측이 capabilities를 교환하여 상대가 지원하는 기능만 호출함.
     이로써 버전 차이/구현 차이가 있어도 안전하게 통신 가능.

       - Client는 서버 capabilities를 보고 어떤 메서드를 호출할지 결정
       - Server는 클라이언트 capabilities를 보고 콜백 요청 가능 여부 판단
""")


if __name__ == "__main__":
    asyncio.run(main())
