"""
MCP 서버: 일정 관리 도구

이 파일은 독립적인 MCP 서버입니다.
SQLite DB를 사용하여 일정을 관리하는 4가지 도구를 제공합니다.

도구 목록:
    - add_schedule: 일정 추가
    - list_schedules: 일정 목록 조회
    - update_schedule: 일정 수정
    - delete_schedule: 일정 삭제

핵심 학습 포인트:
    - Agent(app.py)에는 SQL 코드가 한 줄도 없습니다
    - DB 접근은 이 MCP 서버가 전담합니다
    - 서버만 교체하면 DB를 바꿔도 Agent 코드는 변경 없음
"""

import json
import sqlite3
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("schedule-manager")

# DB 파일: 이 서버와 같은 폴더에 생성
DB_PATH = str(Path(__file__).parent / "schedules.db")


def get_db():
    """DB 연결 및 테이블 자동 생성"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            memo TEXT DEFAULT ''
        )
    """)
    conn.commit()
    return conn


# ============================================================
# MCP 도구 정의
# ============================================================

@mcp.tool()
def add_schedule(title: str, date: str, memo: str = "") -> str:
    """새 일정을 추가합니다.

    Args:
        title: 일정 제목 (예: '팀 미팅', '과제 제출')
        date: 날짜와 시간 (예: '2026-03-27 15:00')
        memo: 메모 (선택사항)
    """
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO schedules (title, date, memo) VALUES (?, ?, ?)",
        (title, date, memo),
    )
    conn.commit()
    schedule_id = cursor.lastrowid
    conn.close()
    return json.dumps({
        "status": "success",
        "id": schedule_id,
        "message": f"일정 '{title}'이(가) 추가되었습니다. (ID: {schedule_id})",
    }, ensure_ascii=False)


@mcp.tool()
def list_schedules(date: str = "") -> str:
    """저장된 일정 목록을 조회합니다. 날짜를 지정하면 해당 날짜만 조회합니다.

    Args:
        date: 조회할 날짜 (예: '2026-03-27'). 빈 문자열이면 전체 조회
    """
    conn = get_db()
    if date:
        rows = conn.execute(
            "SELECT * FROM schedules WHERE date LIKE ? ORDER BY date",
            (f"{date}%",),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM schedules ORDER BY date"
        ).fetchall()
    conn.close()

    if not rows:
        return json.dumps({"schedules": [], "message": "등록된 일정이 없습니다."}, ensure_ascii=False)

    schedules = [
        {"id": r["id"], "title": r["title"], "date": r["date"], "memo": r["memo"]}
        for r in rows
    ]
    return json.dumps({"schedules": schedules, "count": len(schedules)}, ensure_ascii=False)


@mcp.tool()
def update_schedule(id: int, title: str = "", date: str = "", memo: str = "") -> str:
    """기존 일정을 수정합니다. 변경할 항목만 입력하세요.

    Args:
        id: 수정할 일정 ID
        title: 새 제목 (빈 문자열이면 변경 안 함)
        date: 새 날짜/시간 (빈 문자열이면 변경 안 함)
        memo: 새 메모 (빈 문자열이면 변경 안 함)
    """
    conn = get_db()
    existing = conn.execute("SELECT * FROM schedules WHERE id = ?", (id,)).fetchone()
    if not existing:
        conn.close()
        return json.dumps({"status": "error", "message": f"ID {id}인 일정을 찾을 수 없습니다."}, ensure_ascii=False)

    new_title = title if title else existing["title"]
    new_date = date if date else existing["date"]
    new_memo = memo if memo else existing["memo"]

    conn.execute(
        "UPDATE schedules SET title=?, date=?, memo=? WHERE id=?",
        (new_title, new_date, new_memo, id),
    )
    conn.commit()
    conn.close()
    return json.dumps({
        "status": "success",
        "message": f"일정 ID {id}이(가) 수정되었습니다.",
    }, ensure_ascii=False)


@mcp.tool()
def delete_schedule(id: int) -> str:
    """일정을 삭제합니다.

    Args:
        id: 삭제할 일정 ID
    """
    conn = get_db()
    existing = conn.execute("SELECT * FROM schedules WHERE id = ?", (id,)).fetchone()
    if not existing:
        conn.close()
        return json.dumps({"status": "error", "message": f"ID {id}인 일정을 찾을 수 없습니다."}, ensure_ascii=False)

    conn.execute("DELETE FROM schedules WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return json.dumps({
        "status": "success",
        "message": f"일정 '{existing['title']}'이(가) 삭제되었습니다.",
    }, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
