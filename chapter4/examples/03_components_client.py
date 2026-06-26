"""
Chapter 4-3: MCP 3대 구성요소 클라이언트 (Resource / Tool / Prompt)

03_components_server.py에 연결해 세 구성요소를 직접 호출하고,
"누가 호출하는가"와 "무엇이 반환되는가"를 비교합니다.

일부러 LLM을 사용하지 않습니다.
MCP 구성요소 자체의 차이를 먼저 보기 위해서입니다.

실행:
    python chapter4/examples/03_components_client.py
"""

import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SERVER_PATH = str(Path(__file__).parent / "03_components_server.py")


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)


def box(label: str, content: str) -> None:
    print(f"\n  [{label}]")
    for line in content.split("\n"):
        print(f"  {line}")


async def main():
    print("=" * 70)
    print(" Chapter 4-3: 3대 구성요소 직접 호출")
    print("=" * 70)

    server_params = StdioServerParameters(command=sys.executable, args=[SERVER_PATH])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ============================================================
            # Part A: Resource - Host 앱이 직접 읽어 오는 데이터
            # ============================================================
            section("Part A: Resource (데이터 읽기)")
            print("""
  호출 주체: Host 앱 (개발자 코드가 직접 호출)
  메서드   : session.read_resource(uri)
  특징     : URI로 식별, 부수효과 없음, 데이터 반환
""")

            # 1) 고정 URI 리소스를 읽습니다.
            print("  ── 1) notes://list 호출")
            result = await session.read_resource("notes://list")
            box("반환된 데이터", result.contents[0].text)

            # 2) URI 안에 파라미터가 들어가는 리소스를 읽습니다.
            print("\n  ── 2) notes://N002 호출 (URI 파라미터)")
            result = await session.read_resource("notes://N002")
            box("반환된 데이터", result.contents[0].text)

            print("\n  >> Host가 '필요하다고 판단해서' 직접 읽어옴")
            print("  >> 이 데이터는 나중에 LLM의 system/user 메시지에 주입 가능")

            # ============================================================
            # Part B: Tool - 모델이 요청하고 Host가 실행하는 기능
            # ============================================================
            section("Part B: Tool (행동 수행)")
            print("""
  호출 주체: LLM이 자율 판단 → Host가 승인 후 실행
  메서드   : session.call_tool(name, arguments)
  특징     : 함수명으로 식별, 상태 변경 가능, 결과 반환
""")
            # 실제 Agent에서는 LLM이 tool_use로 요청하지만, 여기서는 차이를 보기 위해 직접 호출합니다.

            # 1) 읽기 성격의 검색 Tool입니다.
            print("  ── 1) search_notes(keyword='MCP') 호출")
            result = await session.call_tool("search_notes", {"keyword": "MCP"})
            box("반환된 결과", result.content[0].text)

            # 2) 메모를 추가하는 Tool입니다. 서버 상태가 바뀝니다.
            print("\n  ── 2) add_note(title='테스트', body='...') 호출")
            result = await session.call_tool(
                "add_note",
                {"title": "테스트 메모", "body": "Tool 호출로 추가됨"},
            )
            
            box("반환된 결과", result.content[0].text)

            # 3) Resource를 다시 읽어 Tool 호출로 상태가 바뀌었는지 확인합니다.
            print("\n  ── 3) 변경 확인: notes://list 다시 읽기 (Resource)")
            result = await session.read_resource("notes://list")
            box("변경된 전체 목록", result.contents[0].text)

            print("\n  >> Tool은 부수효과 발생 (메모가 실제로 추가됨)")
            print("  >> Resource로 다시 읽어보면 상태가 바뀐 것을 확인 가능")

            # ============================================================
            # Part C: Prompt - 사용자가 선택하는 대화 템플릿
            # ============================================================
            section("Part C: Prompt (대화 템플릿)")
            print("""
  호출 주체: 사용자가 UI에서 명시적 선택
  메서드   : session.get_prompt(name, arguments)
  특징     : 완성된 프롬프트 문자열을 반환 (LLM에 그대로 전달할 메시지)
""")

            print("  ── summarize_notes(topic='학습') 호출")
            result = await session.get_prompt("summarize_notes", {"topic": "학습"})

            # Prompt는 Claude API의 messages와 비슷한 메시지 리스트를 반환합니다.
            for msg in result.messages:
                print(f"\n  [role: {msg.role}]")
                print("  " + "─" * 50)
                text = msg.content.text if hasattr(msg.content, "text") else str(msg.content)
                for line in text.split("\n"):
                    print(f"  {line}")

            print("\n  >> Prompt는 '완성된 질문/지시문'을 서버에서 받아옴")
            print("  >> 그대로 LLM에 messages=[...]로 전달하면 됨")
            print("  >> 사용자는 복잡한 프롬프트를 매번 작성하지 않아도 됨")

            # ============================================================
            # 세 구성요소를 한눈에 비교합니다.
            # ============================================================
            section("비교 요약: 누가, 언제, 무엇을")
            print("""
  ┌──────────┬────────────────┬──────────────────┬──────────────────┐
  │  구성요소 │  호출 주체      │  API 메서드      │  반환 형태        │
  ├──────────┼────────────────┼──────────────────┼──────────────────┤
  │ Resource │ Host 앱         │ read_resource   │ 데이터(텍스트)   │
  │ Tool     │ LLM (승인: Host)│ call_tool       │ 실행 결과        │
  │ Prompt   │ 사용자          │ get_prompt      │ 메시지 리스트    │
  └──────────┴────────────────┴──────────────────┴──────────────────┘

  핵심 차이:
    Resource : "미리 읽어서 컨텍스트에 넣어준다"
    Tool     : "LLM이 판단해서 필요할 때 호출한다"
    Prompt   : "사용자가 골라서 바로 실행한다"

  다음 단계 (04_agent_with_mcp.py):
    → 이 셋을 실제 LLM(Claude)과 결합하여 Agent 동작 체험
""")


if __name__ == "__main__":
    asyncio.run(main())
