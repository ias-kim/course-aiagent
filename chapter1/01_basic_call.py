"""
Chapter 1-1: Claude API 기본 호출

가장 단순한 형태의 API 호출을 배웁니다.
- Anthropic 클라이언트 생성
- messages.create()로 메시지 전송
- 응답 구조 이해
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# 1. 클라이언트 생성 (ANTHROPIC_API_KEY 환경변수를 자동으로 사용)
client = Anthropic()

# 2. 메시지 전송
# messages.create()의 주요 파라미터:
#   - model (필수): 사용할 모델 ID
#       1) "claude-sonnet-4-20250514": 속도와 성능의 균형 (가장 많이 사용)
#       2) "claude-haiku-4-5-20251001": 빠르고 저렴, 간단한 작업에 적합
#       3) "claude-opus-4-20250514": 최고 성능, 복잡한 추론에 적합
#   - max_tokens (필수): 모델이 생성할 최대 출력 토큰 수
#   - messages (필수): 대화 메시지 리스트
#       1) role: "user"(사용자) 또는 "assistant"(AI) - 대화 순서를 구분
#       2) content: 메시지 내용 (문자열 또는 콘텐츠 블록 리스트)
#   - system (선택): AI의 역할/행동을 지정하는 시스템 프롬프트 (02번 예제에서 다룸)
#   - temperature (선택): 응답의 무작위성 조절, 0.0~1.0 (03번 예제에서 다룸)
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "안녕하세요! 자기소개를 한 문장으로 해주세요."}
    ],
)

# 3. 응답 구조 확인
print("=== 전체 응답 객체 ===")
print(f"ID: {response.id}")
print(f"모델: {response.model}")
print(f"종료 이유: {response.stop_reason}")
print(f"토큰 사용량: 입력 {response.usage.input_tokens}, 출력 {response.usage.output_tokens}")

print("\n=== 응답 텍스트 ===")
print(response.content[0].text)


# 토큰(Token)이란?
#   LLM이 텍스트를 처리하는 최소 단위입니다.
#   - 영어: 단어 1개 ≈ 1~2 토큰 (예: "hello" → 1토큰, "artificial" → 1토큰)
#   - 한국어: 단어 1개 ≈ 2~4 토큰 (예: "안녕하세요" → 3토큰)
#   - 대략 영어 기준 1토큰 ≈ 4글자, 한국어 기준 1토큰 ≈ 1~2글자
#   - input_tokens: 우리가 보낸 메시지(system + user)를 토큰화한 수 → 비용 발생
#   - output_tokens: 모델이 생성한 응답을 토큰화한 수 → 비용 발생 (input보다 단가 높음)
#   - max_tokens: 모델이 생성할 수 있는 최대 출력 토큰 수 (이 값을 초과하면 응답이 잘림)

# response 객체의 주요 속성:
#   - id: 요청의 고유 식별자 (예: "msg_01XFDUDYJgAACzvnptvVoYEL")
#   - model: 실제 사용된 모델명
#   - role: 응답자 역할 (항상 "assistant")
#   - type: 객체 타입 (항상 "message")
#   - stop_reason: 응답 종료 이유
#       - "end_turn": 모델이 자연스럽게 응답을 완료함
#       - "max_tokens": max_tokens 제한에 도달하여 잘림
#       - "tool_use": 도구 호출을 위해 중단됨 (Chapter 4에서 다룸)
#   - content: 응답 콘텐츠 블록 리스트 (List[ContentBlock])
#       하나의 응답에 여러 블록이 포함될 수 있음 (예: 텍스트 + 도구 호출)
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
#       일반 텍스트 응답에서는 content[0].text로 접근하면 됨
#   - usage: 토큰 사용량
#       - usage.input_tokens: 입력에 사용된 토큰 수
#       - usage.output_tokens: 출력에 사용된 토큰 수
