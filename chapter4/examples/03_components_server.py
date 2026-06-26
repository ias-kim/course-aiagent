"""
Chapter 4-3: MCP 3대 구성요소 서버 (Resource / Tool / Prompt)

하나의 서버에서 세 구성요소를 각각 정의해
"무엇을 누가 언제 쓰는지"를 비교할 수 있게 만든 예제입니다.

제공 기능 (모두 '메모장' 도메인):
    Resource: notes://list          - 전체 메모 목록 읽기 (데이터)
    Resource: notes://{note_id}     - 특정 메모 읽기 (데이터 + 파라미터)

    Tool:     add_note              - 메모 추가 (상태 변경)
    Tool:     search_notes          - 메모 검색 (읽기지만 LLM이 자율 호출)

    Prompt:   summarize_notes       - 메모 요약 프롬프트 (대화 템플릿)

이 서버는 03_components_client.py에서 자동 실행됩니다.
"""

from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notes-server")

# 샘플 메모 저장소입니다. 실습을 단순하게 하려고 실제 DB 대신 메모리를 사용합니다.
NOTES = {
    "N001": {"title": "MCP 학습", "body": "Resource는 데이터, Tool은 행동", "created": "2026-04-20"},
    "N002": {"title": "TaskGroup 메모", "body": "Python 3.11+ 구조적 동시성", "created": "2026-04-21"},
    "N003": {"title": "장보기", "body": "계란, 우유, 빵", "created": "2026-04-22"},
}


# ============================================================
# Resource: Host 앱이 필요할 때 읽어 가는 데이터입니다.
# ============================================================
# URI로 식별하며, 읽기 전용이라 서버 상태를 바꾸지 않습니다.
# 읽어 온 데이터는 나중에 LLM 컨텍스트에 넣을 수 있습니다.

@mcp.resource("notes://list")
def list_notes() -> str:
    """전체 메모 목록을 반환합니다."""
    lines = [f"[{nid}] {note['title']} ({note['created']})" for nid, note in NOTES.items()]
    return "\n".join(lines) if lines else "(메모 없음)"


@mcp.resource("notes://{note_id}")
def get_note(note_id: str) -> str:
    """특정 메모의 상세 내용을 반환합니다."""
    note = NOTES.get(note_id)
    if not note:
        return f"메모 '{note_id}'를 찾을 수 없습니다."
    return f"제목: {note['title']}\n작성일: {note['created']}\n\n{note['body']}"


# ============================================================
# Tool: 모델이 필요하다고 판단하면 호출을 요청하는 실행 기능입니다.
# ============================================================
# 호출은 모델이 요청하지만, 실제 실행과 승인 여부는 Host가 담당합니다.
# 메모 추가처럼 서버 상태가 바뀌는 부수효과가 있을 수 있습니다.

@mcp.tool()
def add_note(title: str, body: str) -> str:
    """새 메모를 추가합니다.

    Args:
        title: 메모 제목
        body: 메모 본문
    """
    new_id = f"N{len(NOTES) + 1:03d}"
    NOTES[new_id] = {
        "title": title,
        "body": body,
        "created": datetime.now().strftime("%Y-%m-%d"),
    }
    return f"메모 '{new_id}' 추가 완료: {title}"


@mcp.tool()
def search_notes(keyword: str) -> str:
    """제목 또는 본문에 키워드가 포함된 메모를 검색합니다.

    Args:
        keyword: 검색 키워드
    """
    results = []
    for nid, note in NOTES.items():
        if keyword in note["title"] or keyword in note["body"]:
            results.append(f"[{nid}] {note['title']}: {note['body'][:30]}")
    return "\n".join(results) if results else f"'{keyword}' 검색 결과 없음"


# ============================================================
# Prompt: 사용자가 골라 쓰는 재사용 가능한 대화 템플릿입니다.
# ============================================================
# 서버가 완성된 프롬프트 문자열을 반환하므로, 사용자는 긴 지시문을 매번 쓰지 않아도 됩니다.

@mcp.prompt()
def summarize_notes(topic: str = "전체") -> str:
    """메모를 주제별로 요약하는 프롬프트를 생성합니다.

    Args:
        topic: 요약 대상 주제 (기본값: '전체')
    """
    return f"""당신은 유능한 개인 비서입니다.
'{topic}' 주제의 메모들을 다음 형식으로 요약하세요:

## 핵심 주제
(3개 이내 bullet)

## 실행 항목
(해야 할 일이 있다면)

## 추가 필요 정보
(부족하거나 확인 필요한 부분)

간결하고 실무적으로 작성하세요."""


if __name__ == "__main__":
    mcp.run()
