"""
Chapter 4-5: 다중 MCP 서버 연결

실제 Agent는 여러 MCP 서버에 동시 연결하여
분야별로 전문화된 도구를 조합해 사용합니다.

이 예제의 구성:
    서버 A: 메모장 (03_components_server.py) - Tool/Resource/Prompt
    서버 B: 파일시스템 (05_multi_server_file.py) - Tool만

의도적으로 성격이 다른 두 서버를 연결해,
'도구 네임스페이스 관리'와 '세션 분리'의 현실적 필요성을 보여줍니다.

핵심 패턴:
    1) 서버별 세션을 딕셔너리로 관리
    2) 도구 이름 → 세션 매핑으로 라우팅
    3) 도구 이름 충돌 시 서버명 prefix 처리

실행:
    python chapter4/examples/05_multi_server.py
"""

import asyncio
import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-20250514"

BASE = Path(__file__).parent
SERVERS = {
    "notes": str(BASE / "03_components_server.py"),
    "files": str(BASE / "05_multi_server_file.py"),
}


async def connect_server(stack: AsyncExitStack, server_path: str, label: str):
    """서버 연결을 AsyncExitStack으로 안전하게 관리."""
    params = StdioServerParameters(command=sys.executable, args=[server_path])
    read, write = await stack.enter_async_context(stdio_client(params))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()

    tools = await session.list_tools()
    print(f"  [{label}] {len(tools.tools)}개 도구: {', '.join(t.name for t in tools.tools)}")
    return session, tools.tools


async def main():
    print("=" * 70)
    print(" Chapter 4-5: 다중 MCP 서버 연결")
    print("=" * 70)

    # AsyncExitStack으로 여러 세션을 한 번에 관리
    async with AsyncExitStack() as stack:
        print("\n[1단계] 서버 연결")
        sessions = {}
        all_tools = []
        tool_to_session = {}

        for label, path in SERVERS.items():
            session, tools = await connect_server(stack, path, label)
            sessions[label] = session

            # 도구를 Claude 형식으로 변환 + 라우팅 테이블 작성
            for tool in tools:
                # 이름 충돌 방지를 위한 접두사 정책
                prefixed_name = f"{label}__{tool.name}"
                all_tools.append({
                    "name": prefixed_name,
                    "description": f"[{label}] {tool.description or ''}",
                    "input_schema": tool.inputSchema,
                })
                tool_to_session[prefixed_name] = (session, tool.name)

        print(f"\n  전체 도구: {len(all_tools)}개 (접두사 적용)")
        for t in all_tools:
            print(f"    - {t['name']}")

        # ============================================================
        # 2단계: Agent 루프
        # ============================================================
        print("\n[2단계] Agent 실행")
        user_message = "내 메모를 검색해 'MCP' 관련된 것을 찾고, 현재 디렉토리 파일 목록도 알려줘."
        print(f"\n  사용자: {user_message}")

        messages = [{"role": "user", "content": user_message}]

        for _ in range(10):
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                tools=all_tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                final = next((b.text for b in response.content if b.type == "text"), "")
                print(f"\n  Claude: {final}")
                break

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        routing = tool_to_session.get(block.name)
                        args_str = json.dumps(block.input, ensure_ascii=False)
                        print(f"\n  [도구 호출] {block.name}({args_str})")

                        if not routing:
                            text = f"알 수 없는 도구: {block.name}"
                            is_error = True
                        else:
                            session, real_name = routing
                            print(f"  [라우팅] → 서버의 실제 이름: {real_name}")
                            result = await session.call_tool(real_name, arguments=block.input)
                            text = result.content[0].text if result.content else ""
                            is_error = result.isError or False

                        print(f"  [결과] {text[:80]}{'...' if len(text) > 80 else ''}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": text,
                            "is_error": is_error,
                        })
                messages.append({"role": "user", "content": tool_results})

        # ============================================================
        # 정리
        # ============================================================
        print()
        print("=" * 70)
        print(" 정리: 다중 서버 연결 패턴")
        print("=" * 70)
        print("""
  [핵심 포인트]
    1) AsyncExitStack으로 여러 세션 수명 주기 일괄 관리
    2) 도구 이름 접두사(server__tool)로 충돌 방지
    3) tool_to_session 매핑으로 올바른 서버에 라우팅

  [실전 고려사항]
    - 서버별로 권한/승인 정책을 다르게 적용 가능
    - 서버 하나가 실패해도 나머지로 계속 동작하도록 격리
    - 서버 목록을 설정 파일로 외부화하면 재사용성 향상
""")


if __name__ == "__main__":
    asyncio.run(main())
