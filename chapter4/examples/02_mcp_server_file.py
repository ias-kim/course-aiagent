"""
Chapter 4-4용: 파일 관리 MCP 서버

04_multi_server.py에서 두 번째 서버로 사용됩니다.
날씨/환율 서버(02_mcp_server.py)와 함께 연결하여
다중 서버 구성을 보여줍니다.

제공하는 도구:
    - list_files: 디렉토리 파일 목록 조회
    - read_file: 파일 내용 읽기
    - file_info: 파일 크기/수정일 등 정보 조회
"""

import json
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("file-tools")


@mcp.tool()
def list_files(directory: str = ".") -> str:
    """디렉토리의 파일 목록을 조회합니다.

    Args:
        directory: 조회할 디렉토리 경로 (기본값: 현재 디렉토리)
    """
    try:
        entries = os.listdir(directory)
        result = []
        for entry in sorted(entries):
            full_path = os.path.join(directory, entry)
            entry_type = "DIR" if os.path.isdir(full_path) else "FILE"
            result.append(f"[{entry_type}] {entry}")
        if not result:
            return f"'{directory}'는 비어 있습니다."
        return "\n".join(result)
    except FileNotFoundError:
        return f"디렉토리 '{directory}'를 찾을 수 없습니다."
    except PermissionError:
        return f"디렉토리 '{directory}'에 접근 권한이 없습니다."


@mcp.tool()
def read_file(file_path: str) -> str:
    """텍스트 파일의 내용을 읽습니다. 최대 100줄까지 읽습니다.

    Args:
        file_path: 읽을 파일 경로
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[:100]
        content = "".join(lines)
        total = len(lines)
        if total == 100:
            content += f"\n... (100줄까지만 표시)"
        return content
    except FileNotFoundError:
        return f"파일 '{file_path}'를 찾을 수 없습니다."
    except UnicodeDecodeError:
        return f"파일 '{file_path}'는 텍스트 파일이 아닙니다."


@mcp.tool()
def file_info(file_path: str) -> str:
    """파일의 크기, 수정일 등 메타 정보를 조회합니다.

    Args:
        file_path: 조회할 파일 경로
    """
    try:
        stat = os.stat(file_path)
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size = stat.st_size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"

        return json.dumps({
            "path": file_path,
            "size": size_str,
            "modified": modified,
            "is_directory": os.path.isdir(file_path),
        }, ensure_ascii=False)
    except FileNotFoundError:
        return f"파일 '{file_path}'를 찾을 수 없습니다."


if __name__ == "__main__":
    mcp.run()
