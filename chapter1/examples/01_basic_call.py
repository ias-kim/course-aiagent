"""
Chapter 1-1: Claude API 기본 호출

Claude API를 가장 작은 단위로 호출해 봅니다.
이 파일의 목표는 "요청을 보내고, 응답 객체에서 텍스트와 사용량을 읽는 흐름"을
한 번에 눈으로 확인하는 것입니다.

- Anthropic 클라이언트 생성
- messages.create()로 메시지 전송
- 응답 객체에서 필요한 값 읽기
"""

from dotenv import load_dotenv
from anthropic import Anthropic
import os

load_dotenv()
print(os.environ["ANTHROPIC_API_KEY"])

# 1. 클라이언트 생성
# load_dotenv()가 .env 파일을 읽고, Anthropic()은 ANTHROPIC_API_KEY 환경변수로
# 자동 인증합니다. API 키를 코드에 직접 쓰지 않는 것이 기본 원칙입니다.
client = Anthropic()


# 2. 메시지 전송
# messages.create()에는 최소한 다음 3가지를 넣습니다.
#   1) 어떤 모델에게 요청할지
#   2) 답변을 최대 얼마나 길게 받을지
#   3) 사용자 메시지가 무엇인지
#
# 주요 파라미터:
#   - model (필수): 사용할 모델의 ID
#       1) "claude-sonnet-4-6": 속도와 성능의 균형 (가장 많이 사용)
#       2) "claude-haiku-4-5-20251001": 빠르고 저렴, 간단한 작업에 적합
#       3) "claude-opus-4-8": 최고 성능, 복잡한 추론에 적합
#   - max_tokens (필수): "출력"을 최대 몇 토큰까지 생성할지 정하는 상한
#   - messages (필수): 대화 메시지 리스트
#       1) role: "user"(사용자) 또는 "assistant"(AI) - 누가 말했는지 표시
#       2) content: 메시지 내용 (문자열 또는 콘텐츠 블록 리스트)
#   - system (선택): AI의 역할과 규칙을 정하는 시스템 프롬프트 (02번 예제)
#   - temperature (선택): 답변의 다양성을 조절하는 값, 0.0~1.0 (03번 예제)
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "안녕하세요! 자기소개를 한 문장으로 해주세요."}
    ],
)

# 3. 응답 구조 확인
# response는 단순 문자열이 아니라 id, 모델명, 종료 이유, 토큰 사용량 등을 가진
# 객체입니다. 실제 앱에서는 텍스트뿐 아니라 stop_reason과 usage도 자주 확인합니다.
print("=== 전체 응답 객체 ===")
print(f"ID: {response.id}")
print(f"모델: {response.model}")
print(f"종료 이유: {response.stop_reason}")
print(f"토큰 사용량: 입력 {response.usage.input_tokens}, 출력 {response.usage.output_tokens}")

print("\n=== 응답 텍스트 ===")
print(response.content[0].text)


# 토큰(Token)이란?
#   LLM이 글을 읽고 생성할 때 사용하는 작은 조각입니다.
#   - 영어: 단어 1개 ≈ 1~2 토큰 (예: "hello" → 1토큰, "artificial" → 1토큰)
#   - 한국어: 단어 1개 ≈ 2~4 토큰 (예: "안녕하세요" → 3토큰)
#   - 대략 영어 기준 1토큰 ≈ 4글자, 한국어 기준 1토큰 ≈ 1~2글자
#   - input_tokens: 우리가 보낸 메시지를 토큰으로 센 값 → 입력 비용과 관련
#   - output_tokens: 모델이 만든 답변을 토큰으로 센 값 → 출력 비용과 관련
#   - max_tokens: 출력 토큰 상한. 너무 작으면 답변이 중간에 끊길 수 있음

# response 객체의 주요 속성:
#   - id: 요청의 고유 식별자 (예: "msg_01XFDUDYJgAACzvnptvVoYEL")
#   - model: 실제 사용된 모델명
#   - role: 응답자 역할 (항상 "assistant")
#   - type: 객체 타입 (항상 "message")
#   - stop_reason: 응답 종료 이유
#       - "end_turn": 모델이 자연스럽게 응답을 완료함
#       - "max_tokens": max_tokens 제한에 도달하여 잘림
#       - "tool_use": 도구 호출을 위해 중단됨 (Chapter 4에서 다룸)
#   - content: 응답 콘텐츠 블록 리스트
#       하나의 응답 안에 텍스트, 도구 호출 등 여러 블록이 들어올 수 있음
#       각 블록의 공통 속성:
#       - type: 블록의 종류를 구분
#           - "text": 일반 텍스트 응답
#           - "tool_use": 도구 호출 요청 (Chapter 4에서 다룸)
#       TextBlock (type="text")일 때:
#       - text: 실제 응답 텍스트 문자열
#       ToolUseBlock (type="tool_use")일 때:
#       - id: 도구 호출 고유 ID (도구 결과 반환 시 필요)
#       - name: 호출할 도구 이름
#       - input: 도구에 전달할 인자 (dict)
#
#       일반 텍스트 답변만 받을 때는 보통 content[0].text로 읽으면 됩니다.
#   - usage: 토큰 사용량
#       - usage.input_tokens: 입력에 사용된 토큰 수
#       - usage.output_tokens: 출력에 사용된 토큰 수
