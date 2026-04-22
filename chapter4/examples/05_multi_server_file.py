"""
Chapter 4-5 보조: 파일시스템 MCP 서버

05_multi_server.py의 두 번째 연결 대상.
Tool만 제공하며, 03_components_server.py(Tool+Resource+Prompt)와 결합되어
다중 서버 구성을 시연합니다.
"""

import json
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("file-tools")


@mcp.tool()
def list_files(directory: str = ".") -> str:
    """디렉토리의 파일 목록을 반환합니다.

    Args:
        directory: 조회할 경로 (기본값: 현재 디렉토리)
    """
    try:
        entries = sorted(os.listdir(directory))
        lines = []
        for e in entries:
            path = os.path.join(directory, e)
            kind = "DIR" if os.path.isdir(path) else "FILE"
            lines.append(f"[{kind}] {e}")
        return "\n".join(lines) if lines else "(비어 있음)"
    except FileNotFoundError:
        return f"디렉토리를 찾을 수 없음: {directory}"
    except PermissionError:
        return f"접근 권한 없음: {directory}"


@mcp.tool()
def file_info(path: str) -> str:
    """파일의 크기/수정일 정보를 반환합니다.

    Args:
        path: 조회할 파일 경로
    """
    try:
        stat = os.stat(path)
        size = stat.st_size
        unit = "B"
        if size >= 1024 * 1024:
            size, unit = size / (1024 * 1024), "MB"
        elif size >= 1024:
            size, unit = size / 1024, "KB"
        return json.dumps({
            "path": path,
            "size": f"{size:.1f} {unit}" if isinstance(size, float) else f"{size} {unit}",
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "is_directory": os.path.isdir(path),
        }, ensure_ascii=False)
    except FileNotFoundError:
        return f"파일을 찾을 수 없음: {path}"


if __name__ == "__main__":
    mcp.run()
