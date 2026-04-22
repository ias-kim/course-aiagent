"""
Chapter 4-4: MCP 3대 구성요소 + LLM 결합 Agent

03_components_server.py의 Resource/Tool/Prompt를
실제 Claude(LLM)와 결합하여 각 제어 방식이 어떻게 동작하는지 체험합니다.

구현하는 3가지 시나리오:

    [1] Application-controlled (Resource)
        사용자 입력에 @notes://N002 같은 참조가 있으면
        Host가 자동으로 리소스를 읽어 컨텍스트에 주입한 뒤 LLM 호출

    [2] Model-controlled (Tool)
        일반 대화에서 LLM이 자율 판단해 search_notes / add_note 호출
        → Host는 승인 게이트 역할

    [3] User-controlled (Prompt)
        사용자가 '/summarize 학습' 같은 슬래시 명령 입력 시
        Host가 서버에서 프롬프트를 가져와 LLM에 전달

실행:
    python chapter4/examples/04_agent_with_mcp.py
"""

import asyncio
import json
import re
import sys
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
SERVER_PATH = str(Path(__file__).parent / "03_components_server.py")


# ============================================================
# 유틸: @참조 감지 & 슬래시 명령 파싱
# ============================================================
RESOURCE_REF_PATTERN = re.compile(r"@(\S+://\S+)")
SLASH_PATTERN = re.compile(r"^/(\w+)(?:\s+(.*))?$")


async def resolve_resources(session: ClientSession, user_input: str) -> str:
    """사용자 입력에서 @uri 패턴을 찾아 리소스를 읽고 컨텍스트에 주입."""
    matches = RESOURCE_REF_PATTERN.findall(user_input)
    if not matches:
        return user_input

    context_blocks = []
    cleaned = user_input
    for uri in matches:
        print(f"  [Host] @참조 감지 → read_resource({uri!r})")
        try:
            result = await session.read_resource(uri)
            text = result.contents[0].text
            context_blocks.append(f"[참조 자료 {uri}]\n{text}")
        except Exception as e:
            context_blocks.append(f"[참조 실패 {uri}: {e}]")
        cleaned = cleaned.replace(f"@{uri}", f"({uri})")

    return "\n\n".join(context_blocks) + "\n\n---\n사용자 요청: " + cleaned


async def parse_slash_command(session: ClientSession, user_input: str):
    """/<prompt_name> <arg> 형식을 파싱하여 서버의 Prompt를 가져옴."""
    match = SLASH_PATTERN.match(user_input.strip())
    if not match:
        return None
    name, arg = match.group(1), match.group(2) or ""
    print(f"  [Host] 슬래시 명령 감지 → get_prompt({name!r}, topic={arg!r})")
    try:
        # 단순화: 첫 파라미터 이름을 topic으로 가정 (실제로는 arguments 스키마 조회 가능)
        result = await session.get_prompt(name, {"topic": arg} if arg else {})
        # Prompt가 반환한 첫 메시지를 사용자 메시지로 사용
        first = result.messages[0]
        return first.content.text if hasattr(first.content, "text") else str(first.content)
    except Exception as e:
        print(f"  [Host] Prompt 가져오기 실패: {e}")
        return None


async def run_agent_turn(session: ClientSession, claude_tools, conversation, user_text: str):
    """한 턴의 Agent 루프 실행 (tool_use 반복 처리)."""
    conversation.append({"role": "user", "content": user_text})

    for _ in range(6):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system="당신은 메모장 관리 비서입니다. 도구를 적절히 활용해 한국어로 답변하세요.",
            tools=claude_tools,
            messages=conversation,
        )

        if response.stop_reason == "end_turn":
            final = next((b.text for b in response.content if b.type == "text"), "")
            conversation.append({"role": "assistant", "content": final})
            print(f"\n  Claude: {final}")
            return

        if response.stop_reason == "tool_use":
            conversation.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    args_str = json.dumps(block.input, ensure_ascii=False)
                    print(f"\n  [LLM 판단] 도구 호출 요청: {block.name}({args_str})")
                    # Host가 여기서 승인 로직을 수행할 수 있음 (여기서는 자동 허용)
                    print(f"  [Host] 승인 → 실행")
                    result = await session.call_tool(block.name, arguments=block.input)
                    text = result.content[0].text if result.content else ""
                    print(f"  [결과] {text}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": text,
                        "is_error": result.isError or False,
                    })
            conversation.append({"role": "user", "content": tool_results})


# ============================================================
# 메인
# ============================================================
async def main():
    print("=" * 70)
    print(" Chapter 4-4: MCP 3대 구성요소 + LLM Agent")
    print("=" * 70)
    print("""
  입력 방식:
    일반 질문              → LLM이 Tool 자율 호출 (Model-controlled)
    @notes://N001 ...     → Host가 Resource 주입 (Application-controlled)
    /summarize 학습       → 서버 Prompt 사용 (User-controlled)
    quit                  → 종료
""")

    server_params = StdioServerParameters(command=sys.executable, args=[SERVER_PATH])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Tool 목록을 Claude API 형식으로 변환
            tools_result = await session.list_tools()
            claude_tools = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema,
                }
                for t in tools_result.tools
            ]
            print(f"  서버 도구: {', '.join(t['name'] for t in claude_tools)}")

            # 사용 가능한 Prompt 목록
            prompts_result = await session.list_prompts()
            prompt_names = [p.name for p in prompts_result.prompts]
            print(f"  서버 Prompt: {', '.join(prompt_names)}")

            # Resource 목록
            res_result = await session.list_resources()
            templates = await session.list_resource_templates()
            all_uris = [r.uri for r in res_result.resources] + [
                t.uriTemplate for t in templates.resourceTemplates
            ]
            print(f"  서버 Resource: {', '.join(str(u) for u in all_uris)}")
            print("-" * 70)

            conversation = []

            while True:
                print()
                user_input = input("사용자: ").strip()
                if not user_input:
                    continue
                if user_input.lower() == "quit":
                    print("종료합니다.")
                    break

                # 1) 슬래시 명령 우선 처리 (User-controlled Prompt)
                slash_text = await parse_slash_command(session, user_input)
                if slash_text is not None:
                    await run_agent_turn(session, claude_tools, conversation, slash_text)
                    continue

                # 2) @참조가 있으면 Resource 주입 (Application-controlled)
                if RESOURCE_REF_PATTERN.search(user_input):
                    user_text = await resolve_resources(session, user_input)
                    await run_agent_turn(session, claude_tools, conversation, user_text)
                    continue

                # 3) 그 외 일반 대화 (Model-controlled Tools 자율 호출)
                await run_agent_turn(session, claude_tools, conversation, user_input)


if __name__ == "__main__":
    asyncio.run(main())
