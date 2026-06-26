"""
Chapter 1-4: 스트리밍 응답

응답을 한 번에 기다리지 않고, 생성되는 대로 실시간으로 받아봅니다.
- 긴 응답에서 사용자 경험(UX) 개선
- 이벤트 타입별 처리 방법
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()

# --- 방법 1: stream() 컨텍스트 매니저 (가장 간단한 방식) ---
print("=== 스트리밍 응답 ===")

with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=512,
    messages=[
        {"role": "user", "content": "AI Agent가 뭔지 3문장으로 설명해주세요."}
    ],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

print()  # 스트리밍 출력이 끝난 뒤 줄을 바꿔 화면을 정리합니다.

# 스트리밍이 끝난 뒤에는 최종 메시지 객체에서 토큰 사용량을 확인할 수 있습니다.
final_message = stream.get_final_message()
print("*"*100)
print(f"\n=== 토큰 사용량 ===")
print(f"입력: {final_message.usage.input_tokens}, 출력: {final_message.usage.output_tokens}")

# --- 방법 2: 이벤트 단위로 더 세밀하게 처리 ---
# UI에서 시작/종료 상태를 따로 표시하고 싶을 때 유용합니다.
print("\n=== 이벤트 단위 처리 ===")

with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "하늘이 파란 이유를 한 문장으로 알려주세요."}
    ],
) as stream:
    for event in stream:
        match event.type:
            case "message_start":
                print("[시작]", end=" ")
            case "content_block_start":
                print("[블록 시작]", end=" ")
            case "content_block_stop":
                print("[블록 끝]", end=" ")
            case "message_stop":
                print("[완료]")
            case "text":
                print(event.text, end="", flush=True)
