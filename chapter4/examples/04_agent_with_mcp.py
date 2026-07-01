"""
Chapter 4-4: MCP 3대 구성요소 + LLM 결합 Agent

03_components_server.py의 Resource/Tool/Prompt를
실제 Claude(LLM)와 연결해 각 제어 방식이 어떻게 동작하는지 체험합니다.

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
MODEL = "claude-sonnet-4-6"
SERVER_PATH = str(Path(__file__).parent / "03_components_server.py")


# ============================================================
# 유틸: @리소스 참조와 /프롬프트 명령을 감지합니다.
# ============================================================
RESOURCE_REF_PATTERN = re.compile(r"@(\S+://\S+)")
SLASH_PATTERN = re.compile(r"^/(\w+)(?:\s+(.*))?$")


async def resolve_resources(session: ClientSession, user_input: str) -> str:
    """사용자 입력의 @uri 참조를 찾아 Resource를 읽고, 그 내용을 질문 앞에 붙입니다."""
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
    """/<prompt_name> <arg> 형식을 파싱해 서버의 Prompt를 가져옵니다."""
    match = SLASH_PATTERN.match(user_input.strip())
    if not match:
        return None
    name, arg = match.group(1), match.group(2) or ""
    print(f"  [Host] 슬래시 명령 감지 → get_prompt({name!r}, topic={arg!r})")
    try:
        # 실습을 단순하게 하려고 첫 파라미터 이름을 topic이라고 가정합니다.
        # 실제로는 Prompt의 arguments 스키마를 조회해 맞춰 넣을 수 있습니다.
        result = await session.get_prompt(name, {"topic": arg} if arg else {})
        # Prompt가 반환한 첫 메시지를 이번 사용자 요청처럼 사용합니다.
        first = result.messages[0]
        return first.content.text if hasattr(first.content, "text") else str(first.content)
    except Exception as e:
        print(f"  [Host] Prompt 가져오기 실패: {e}")
        return None


async def run_agent_turn(session: ClientSession, claude_tools, conversation, user_text: str):
    """한 번의 사용자 입력에 대해 tool_use가 끝날 때까지 Agent 루프를 실행합니다."""
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
                    # 실제 서비스라면 여기서 승인/권한 검사를 넣습니다. 실습에서는 자동 허용합니다.
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
# 메인 실행부입니다.
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

            # MCP 서버에서 발견한 Tool 목록을 Claude API의 tools 형식으로 변환합니다.
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

            # 서버가 제공하는 Prompt 목록을 확인합니다.
            prompts_result = await session.list_prompts()
            prompt_names = [p.name for p in prompts_result.prompts]
            print(f"  서버 Prompt: {', '.join(prompt_names)}")

            # 고정 Resource와 URI 템플릿 Resource를 함께 보여줍니다.
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

                # 1) 슬래시 명령이면 사용자가 선택한 Prompt를 먼저 적용합니다.
                slash_text = await parse_slash_command(session, user_input)
                if slash_text is not None:
                    await run_agent_turn(session, claude_tools, conversation, slash_text)
                    continue

                # 2) @참조가 있으면 Host가 Resource를 읽어 컨텍스트에 넣습니다.
                if RESOURCE_REF_PATTERN.search(user_input):
                    user_text = await resolve_resources(session, user_input)
                    await run_agent_turn(session, claude_tools, conversation, user_text)
                    continue

                # 3) 일반 대화는 모델이 필요할 때 Tool 호출을 요청합니다.
                await run_agent_turn(session, claude_tools, conversation, user_input)


if __name__ == "__main__":
    asyncio.run(main())
