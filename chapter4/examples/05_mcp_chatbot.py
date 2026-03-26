"""
Chapter 4-5: MCP 기반 대화형 Agent

Ch1-5의 Agent 루프 + Ch3의 Tool Use + Ch4의 MCP를
모두 결합한 완전한 대화형 Agent입니다.

구조:
    사용자 입력
        ↓
    Agent 루프 (while)
        ↓
    Claude API (tools = MCP에서 자동 조회)
        ↓
    tool_use → MCP 서버에 실행 위임
        ↓
    tool_result → Claude에 전달
        ↓
    end_turn → 사용자에게 응답
        ↓
    반복

실행 방법:
    python chapter4/examples/05_mcp_chatbot.py

    02_mcp_server.py가 자동으로 실행됩니다.
    'quit' 입력으로 종료할 수 있습니다.
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
SERVER_PATH = str(Path(__file__).parent / "02_mcp_server.py")


async def main():
    print("=" * 60)
    print("MCP 기반 대화형 Agent")
    print("=" * 60)
    print("02_mcp_server.py의 도구를 사용합니다.")
    print("종료하려면 'quit'을 입력하세요.\n")

    # MCP 서버 연결
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_PATH],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 도구 목록 조회 및 변환
            tools_result = await session.list_tools()
            claude_tools = [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema,
                }
                for tool in tools_result.tools
            ]

            print(f"사용 가능한 도구: {', '.join(t['name'] for t in claude_tools)}")
            print("-" * 60)

            # 대화 히스토리 (Ch1-5에서 배운 패턴)
            conversation_history = []

            while True:
                user_input = input("\n사용자: ")
                if user_input.strip().lower() == "quit":
                    print("대화를 종료합니다.")
                    break

                if not user_input.strip():
                    continue

                conversation_history.append({"role": "user", "content": user_input})

                # Agent 루프
                for iteration in range(10):
                    response = client.messages.create(
                        model=MODEL,
                        max_tokens=1024,
                        system="당신은 다양한 도구를 활용하는 유능한 어시스턴트입니다. 한국어로 답변합니다.",
                        tools=claude_tools,
                        messages=conversation_history,
                    )

                    # 최종 답변
                    if response.stop_reason == "end_turn":
                        assistant_text = next(
                            (b.text for b in response.content if b.type == "text"), ""
                        )
                        conversation_history.append({"role": "assistant", "content": assistant_text})
                        print(f"Claude: {assistant_text}")
                        print(f"  [토큰: 입력 {response.usage.input_tokens} / 출력 {response.usage.output_tokens}]")
                        break

                    # 도구 호출
                    if response.stop_reason == "tool_use":
                        conversation_history.append({"role": "assistant", "content": response.content})

                        tool_results = []
                        for block in response.content:
                            if block.type == "tool_use":
                                print(f"  [도구] {block.name}({json.dumps(block.input, ensure_ascii=False)})")

                                result = await session.call_tool(
                                    block.name,
                                    arguments=block.input,
                                )
                                result_text = result.content[0].text if result.content else "결과 없음"
                                is_error = result.isError or False

                                if is_error:
                                    print(f"  [에러] {result_text}")
                                else:
                                    print(f"  [결과] {result_text}")

                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result_text,
                                    "is_error": is_error,
                                })

                        conversation_history.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    asyncio.run(main())
