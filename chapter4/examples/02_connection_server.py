"""
Chapter 4-2: MCP 연결 절차 확인용 - 최소 서버

이 서버는 연결 절차를 관찰하기 위한 '증명용' 최소 구성입니다.
    - Resource 1개 (greeting://welcome)
    - Tool 1개 (echo)
    - Prompt 1개 (introduction)

실행하지 말고 02_connection_client.py에서 자동으로 기동합니다.

서버가 클라이언트에 노출하는 것:
    1) 서버 이름/버전 (initialize 응답)
    2) capabilities (resources/tools/prompts 지원 여부)
    3) 각 구성 요소의 목록과 스키마
"""

from mcp.server.fastmcp import FastMCP

# name은 initialize 시 클라이언트에게 전달됨
mcp = FastMCP("demo-server")


# ============================================================
# Resource: 환영 메시지
# ============================================================
@mcp.resource("greeting://welcome")
def welcome_message() -> str:
    """서버가 제공하는 환영 메시지를 반환합니다."""
    return "안녕하세요! MCP 연결이 성공했습니다."


# ============================================================
# Tool: 에코 (입력을 그대로 반환)
# ============================================================
@mcp.tool()
def echo(message: str) -> str:
    """입력 메시지를 그대로 반환합니다.

    Args:
        message: 반환할 메시지
    """
    return f"echo: {message}"


# ============================================================
# Prompt: 자기소개 템플릿
# ============================================================
@mcp.prompt()
def introduction(name: str) -> str:
    """사용자를 환영하는 자기소개 프롬프트를 생성합니다.

    Args:
        name: 사용자 이름
    """
    return f"당신은 친절한 안내자입니다. '{name}'님에게 이 서버가 어떤 기능을 제공하는지 간단히 설명하세요."


if __name__ == "__main__":
    mcp.run()
