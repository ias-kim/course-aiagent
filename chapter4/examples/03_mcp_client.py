"""
Chapter 4-3: MCP 클라이언트 — 서버에 연결하여 도구 사용

MCP 클라이언트가 하는 일:
    1) MCP 서버 프로세스를 실행 (또는 원격 서버에 연결)
    2) 서버가 제공하는 도구 목록을 자동으로 조회
    3) 도구를 Claude API의 tools 형식으로 변환
    4) LLM의 tool_use 요청에 따라 서버에 도구 실행을 위임

핵심 차이 (Ch3 vs Ch4):
    Ch3: execute_tool() 함수를 직접 작성 → Agent 내부에서 실행
    Ch4: session.call_tool()로 MCP 서버에 실행 위임 → 서버가 실행

실행 방법:
    python chapter4/examples/03_mcp_client.py

    이 스크립트가 02_mcp_server.py를 자동으로 실행하고 연결합니다.
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

# MCP 서버 경로 (02_mcp_server.py)
SERVER_PATH = str(Path(__file__).parent / "02_mcp_server.py")


async def main():
    print("=" * 60)
    print("Chapter 4-3: MCP 클라이언트")
    print("=" * 60)

    # ============================================================
    # 1단계: MCP 서버에 연결
    # ============================================================
    # StdioServerParameters: 로컬 프로세스로 서버를 실행
    # → 02_mcp_server.py를 자식 프로세스로 실행하고 stdin/stdout으로 통신
    server_params = StdioServerParameters(
        command=sys.executable,    # Python 실행 파일
        args=[SERVER_PATH],        # 서버 스크립트 경로
    )

    print("\n[1단계] MCP 서버에 연결 중...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 서버 초기화 (핸드셰이크)
            await session.initialize()
            print("  서버 연결 완료!")

            # ============================================================
            # 2단계: 서버의 도구 목록 자동 조회
            # ============================================================
            # Ch3에서는 tools 리스트를 수동으로 작성했지만,
            # MCP에서는 서버에서 자동으로 가져옵니다.
            print("\n[2단계] 서버 도구 목록 조회")

            tools_result = await session.list_tools()
            print(f"  발견된 도구: {len(tools_result.tools)}개")
            for tool in tools_result.tools:
                print(f"    - {tool.name}: {tool.description[:40]}...")

            # MCP 도구 → Claude API tools 형식으로 변환
            claude_tools = [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema,
                }
                for tool in tools_result.tools
            ]

            # ============================================================
            # 3단계: 도구를 활용한 대화
            # ============================================================
            print("\n[3단계] 도구를 활용한 대화")

            user_message = "서울 날씨 알려주고, 100달러를 원화로 환산해줘"
            print(f"\n  사용자: {user_message}")

            messages = [{"role": "user", "content": user_message}]

            # Agent 루프 (Ch3-3과 동일한 패턴)
            max_iterations = 10
            for iteration in range(max_iterations):
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    tools=claude_tools,    # ← MCP에서 가져온 도구
                    messages=messages,
                )

                # 최종 답변
                if response.stop_reason == "end_turn":
                    final = next((b.text for b in response.content if b.type == "text"), "")
                    print(f"\n  Claude: {final}")
                    break

                # 도구 호출 처리
                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})

                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            print(f"\n  [도구 호출] {block.name}({json.dumps(block.input, ensure_ascii=False)})")

                            # 핵심 차이: MCP 서버에 실행 위임
                            # Ch3: result = execute_tool(name, input)  ← 직접 실행
                            # Ch4: result = await session.call_tool()  ← 서버에 위임
                            result = await session.call_tool(
                                block.name,
                                arguments=block.input,
                            )
                            result_text = result.content[0].text if result.content else "결과 없음"
                            is_error = result.isError or False

                            print(f"  [결과] {result_text}")

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text,
                                "is_error": is_error,
                            })

                    messages.append({"role": "user", "content": tool_results})

    # ============================================================
    # 정리
    # ============================================================
    print()
    print("=" * 60)
    print("정리: MCP 클라이언트 핵심 코드")
    print("=" * 60)
    print("""
[연결]
  async with stdio_client(server_params) as (read, write):
      async with ClientSession(read, write) as session:
          await session.initialize()

[도구 조회]
  tools = await session.list_tools()    # 서버가 제공하는 도구 자동 조회

[도구 실행]
  result = await session.call_tool(     # 서버에 실행 위임
      "get_weather",
      arguments={"city": "서울"}
  )

[Ch3 → Ch4 변경점]
  1. tools 리스트를 수동 작성 → session.list_tools()로 자동 조회
  2. execute_tool() 직접 실행 → session.call_tool()로 서버에 위임
  3. Agent 루프 패턴은 동일 (stop_reason 기반)
""")


if __name__ == "__main__":
    asyncio.run(main())
