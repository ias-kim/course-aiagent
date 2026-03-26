"""
Chapter 4-4: 다중 MCP 서버 연결

실제 Agent는 여러 MCP 서버에 동시에 연결하여
다양한 도구를 활용합니다.

예시:
    서버 A: 날씨/환율 도구
    서버 B: 파일 관리 도구
    Agent가 두 서버에 동시 연결 → 모든 도구 사용 가능

이 예제에서는:
    - 두 개의 MCP 서버를 각각 실행
    - 각 서버의 도구를 합쳐서 LLM에 전달
    - 하나의 Agent가 여러 서버의 도구를 자유롭게 사용

실행 방법:
    python chapter4/examples/04_multi_server.py
"""

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-20250514"

# 서버 경로
WEATHER_SERVER = str(Path(__file__).parent / "02_mcp_server.py")


async def connect_to_server(server_path: str, server_name: str):
    """MCP 서버에 연결하고 도구 목록을 조회합니다."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_path],
    )

    read, write = await stdio_client(server_params).__aenter__()
    session = await ClientSession(read, write).__aenter__()
    await session.initialize()

    tools_result = await session.list_tools()
    print(f"  [{server_name}] 도구 {len(tools_result.tools)}개 발견")
    for tool in tools_result.tools:
        print(f"    - {tool.name}")

    # Claude API 형식으로 변환 + 서버 이름 태그
    claude_tools = []
    tool_to_session = {}
    for tool in tools_result.tools:
        claude_tools.append({
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        })
        tool_to_session[tool.name] = session

    return claude_tools, tool_to_session, session


async def main():
    print("=" * 60)
    print("Chapter 4-4: 다중 MCP 서버 연결")
    print("=" * 60)

    # ============================================================
    # 1단계: 여러 서버에 연결
    # ============================================================
    print("\n[1단계] MCP 서버들에 연결")

    # 서버 1: 날씨/환율 도구 (02_mcp_server.py)
    tools1, session_map1, session1 = await connect_to_server(WEATHER_SERVER, "날씨/환율 서버")

    # 모든 도구와 세션 매핑을 합침
    all_tools = tools1
    tool_to_session = {**session_map1}

    print(f"\n  전체 도구 수: {len(all_tools)}개")

    # ============================================================
    # 2단계: 통합 Agent 루프
    # ============================================================
    print("\n[2단계] 통합 Agent 루프")

    user_message = "서울 날씨 알려주고, 100달러를 원화로 환산해줘. 지금 서울 몇 시인지도 알려줘."
    print(f"\n  사용자: {user_message}")

    messages = [{"role": "user", "content": user_message}]

    for iteration in range(10):
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
                    # 도구 이름으로 해당 서버 세션을 찾아 실행
                    session = tool_to_session.get(block.name)
                    if session:
                        print(f"\n  [도구] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                        result = await session.call_tool(block.name, arguments=block.input)
                        result_text = result.content[0].text if result.content else "결과 없음"
                        print(f"  [결과] {result_text}")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                            "is_error": result.isError or False,
                        })
                    else:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"알 수 없는 도구: {block.name}",
                            "is_error": True,
                        })

            messages.append({"role": "user", "content": tool_results})

    # 세션 정리
    await session1.__aexit__(None, None, None)

    # ============================================================
    # 정리
    # ============================================================
    print()
    print("=" * 60)
    print("정리: 다중 서버 연결 패턴")
    print("=" * 60)
    print("""
[핵심 패턴]

  # 여러 서버에 연결
  session_a = connect("server_a.py")
  session_b = connect("server_b.py")

  # 모든 도구를 합침
  all_tools = tools_a + tools_b

  # 도구 이름 → 세션 매핑
  tool_to_session = {"get_weather": session_a, "read_file": session_b}

  # Agent 루프에서 도구 이름으로 올바른 서버에 요청
  session = tool_to_session[tool_name]
  result = await session.call_tool(tool_name, arguments=input)

[장점]
  - 도구를 기능별로 서버로 분리 → 관심사 분리
  - 서버를 독립적으로 업데이트/교체 가능
  - 다른 Agent에서도 같은 서버 재사용
""")


if __name__ == "__main__":
    asyncio.run(main())
