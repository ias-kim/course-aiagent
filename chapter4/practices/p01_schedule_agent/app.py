"""
실습 P01: 일정 관리 Agent

MCP 서버(schedule_server.py)의 도구를 활용하는 웹 기반 Agent입니다.

학습 목표:
    - MCP 서버의 도구를 Agent에 연결하는 방법을 이해한다
    - Agent 코드에 DB 로직이 없음을 확인한다 (도구가 서버로 분리)
    - 자연어 → 도구 호출 → DB 조작의 전체 흐름을 체험한다

구조:
    사용자: "내일 3시에 팀 미팅 추가해줘"
        ↓
    Flask (app.py) ─── MCP 클라이언트 ─── MCP 서버 (schedule_server.py)
        ↓                                      ↓
    Claude API                             SQLite DB
        ↓
    tool_use: add_schedule("팀 미팅", "2026-03-27 15:00")
        ↓
    MCP 서버가 DB에 INSERT
        ↓
    "팀 미팅이 추가되었습니다!"

실행: python chapter4/practices/p01_schedule_agent/app.py → http://localhost:5011
"""

import asyncio
import json
import sys
import time
import threading
from pathlib import Path
from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

app = Flask(__name__)
client = Anthropic()
MODEL = "claude-sonnet-4-20250514"
SERVER_PATH = str(Path(__file__).parent / "schedule_server.py")

# 세션별 대화 히스토리
conversations: dict[str, list] = {}

# MCP 세션과 도구를 관리하는 글로벌 상태
mcp_state = {
    "session": None,
    "tools": [],
    "loop": None,
}

TOOL_INFO = {
    "add_schedule": {"icon": "📅", "label": "일정 추가"},
    "list_schedules": {"icon": "📋", "label": "일정 조회"},
    "update_schedule": {"icon": "✏️", "label": "일정 수정"},
    "delete_schedule": {"icon": "🗑️", "label": "일정 삭제"},
}

SYSTEM_PROMPT = """당신은 일정 관리 어시스턴트입니다. 한국어로 답변합니다.

사용자가 일정을 추가, 조회, 수정, 삭제하려 할 때 적절한 도구를 사용하세요.
- 날짜를 말할 때 '내일', '다음 주 월요일' 같은 표현은 구체적인 날짜로 변환하세요.
- 일정 목록을 보여줄 때는 보기 좋게 정리해서 알려주세요.
- 도구가 필요 없는 일반 대화에는 자연스럽게 답하세요."""


async def init_mcp():
    """MCP 서버에 연결하고 도구 목록을 조회합니다."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_PATH],
    )

    read_stream, write_stream = await stdio_client(server_params).__aenter__()
    session = await ClientSession(read_stream, write_stream).__aenter__()
    await session.initialize()

    tools_result = await session.list_tools()
    claude_tools = [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        }
        for tool in tools_result.tools
    ]

    mcp_state["session"] = session
    mcp_state["tools"] = claude_tools
    print(f"MCP 서버 연결 완료. 도구 {len(claude_tools)}개: {', '.join(t['name'] for t in claude_tools)}")


mcp_ready = threading.Event()


def start_mcp_in_background():
    """별도 스레드에서 asyncio 이벤트 루프를 실행하여 MCP를 초기화합니다."""
    loop = asyncio.new_event_loop()
    mcp_state["loop"] = loop
    loop.run_until_complete(init_mcp())
    mcp_ready.set()  # 초기화 완료 시그널
    # 루프를 유지 (MCP 세션이 살아있어야 함)
    loop.run_forever()


# Flask 시작 전에 MCP 연결
mcp_thread = threading.Thread(target=start_mcp_in_background, daemon=True)
mcp_thread.start()
mcp_ready.wait(timeout=10)  # 최대 10초 대기


@app.route("/")
def index():
    return render_template("index.html", tool_info=TOOL_INFO)


@app.route("/chat", methods=["POST"])
def chat():
    """Agent 루프 + MCP 도구 호출을 SSE로 스트리밍합니다."""
    data = request.json
    user_message = data["message"]
    session_id = data.get("session_id", "default")

    if session_id not in conversations:
        conversations[session_id] = []

    history = conversations[session_id]
    history.append({"role": "user", "content": user_message})

    session = mcp_state["session"]
    loop = mcp_state["loop"]

    def generate():
        total_input = 0
        total_output = 0

        for iteration in range(10):
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=mcp_state["tools"],
                messages=history,
            )

            total_input += response.usage.input_tokens
            total_output += response.usage.output_tokens

            if response.stop_reason == "end_turn":
                assistant_text = ""
                for block in response.content:
                    if block.type == "text":
                        assistant_text = block.text
                        yield f"data: {json.dumps({'text': block.text})}\n\n"
                history.append({"role": "assistant", "content": assistant_text})
                break

            if response.stop_reason == "tool_use":
                history.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "text" and block.text:
                        yield f"data: {json.dumps({'text': block.text})}\n\n"

                    if block.type == "tool_use":
                        info = TOOL_INFO.get(block.name, {"icon": "🔧", "label": block.name})
                        yield f"data: {json.dumps({'tool_call': {'name': block.name, 'icon': info['icon'], 'label': info['label'], 'input': block.input}})}\n\n"

                        # MCP 서버에 도구 실행 위임 (asyncio)
                        future = asyncio.run_coroutine_threadsafe(
                            session.call_tool(block.name, arguments=block.input),
                            loop,
                        )
                        result = future.result(timeout=10)
                        result_text = result.content[0].text if result.content else "결과 없음"
                        is_error = result.isError or False

                        yield f"data: {json.dumps({'tool_result': {'name': block.name, 'result': result_text, 'is_error': is_error}})}\n\n"

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                            "is_error": is_error,
                        })

                history.append({"role": "user", "content": tool_results})

        yield f"data: {json.dumps({'done': True, 'input_tokens': total_input, 'output_tokens': total_output})}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream")


@app.route("/reset", methods=["POST"])
def reset():
    session_id = request.json.get("session_id", "default")
    conversations.pop(session_id, None)
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True, port=5011, use_reloader=False)


# ============================================================
# REST API 명세
# ============================================================
#
# 1. GET /
#    메인 페이지 (채팅 UI + 도구 목록)
#
# ─────────────────────────────────────────────────────────────
#
# 2. POST /chat
#    사용자 메시지를 받아 MCP Agent 루프를 실행합니다.
#
#    Request:
#      Content-Type: application/json
#      Body:
#      {
#        "message":    (string, 필수) 사용자 메시지
#        "session_id": (string, 선택) 세션 식별자 (기본값: "default")
#      }
#
#    Response:
#      Content-Type: text/event-stream
#      SSE 이벤트:
#
#      [도구 호출]
#        data: {"tool_call": {"name": "add_schedule", "icon": "📅", "label": "일정 추가", "input": {...}}}
#
#      [도구 결과]
#        data: {"tool_result": {"name": "add_schedule", "result": "{...}", "is_error": false}}
#
#      [텍스트]
#        data: {"text": "팀 미팅이 추가되었습니다!"}
#
#      [완료]
#        data: {"done": true, "input_tokens": 200, "output_tokens": 100}
#
# ─────────────────────────────────────────────────────────────
#
# 3. POST /reset
#    대화 히스토리를 초기화합니다.
#
#    Request Body: {"session_id": "..."}
#    Response: {"status": "ok"}
