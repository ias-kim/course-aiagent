"""
Chapter 4-3: MCP 3대 구성요소 서버 (Resource / Tool / Prompt)

하나의 서버에서 세 구성요소를 각각 정의하여
"무엇이 어떻게 다른가"를 본질적으로 비교할 수 있습니다.

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

# 샘플 메모 저장소 (실제 DB 대신 메모리)
NOTES = {
    "N001": {"title": "MCP 학습", "body": "Resource는 데이터, Tool은 행동", "created": "2026-04-20"},
    "N002": {"title": "TaskGroup 메모", "body": "Python 3.11+ 구조적 동시성", "created": "2026-04-21"},
    "N003": {"title": "장보기", "body": "계란, 우유, 빵", "created": "2026-04-22"},
}


# ============================================================
# Resource: 데이터 읽기 (Application-controlled)
# ============================================================
# Host 앱이 필요 시점에 읽어 LLM 컨텍스트에 주입
# URI로 식별, 부수효과 없음

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
# Tool: 행동 수행 (Model-controlled)
# ============================================================
# LLM이 자율 판단으로 호출, Host가 승인 게이트 역할
# 부수효과 발생 가능

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
# Prompt: 대화 템플릿 (User-controlled)
# ============================================================
# 사용자가 명시적으로 선택, 재사용 가능한 프롬프트 제공
# 서버가 완성된 프롬프트 문자열 반환

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
