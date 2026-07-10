"""
Chapter 1-4: 스트리밍 응답

응답을 한 번에 기다리지 않고, 생성되는 대로 실시간으로 받아봅니다.
- 긴 응답에서 사용자 경험(UX) 개선
- 이벤트 타입별 처리 방법

일반 호출은 답변이 완성될 때까지 기다렸다가 한 번에 받습니다.
스트리밍은 답변 조각을 받는 즉시 화면에 보여주므로, 사용자가 덜 기다린다고 느낍니다.
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()

# --- 방법 1: stream() 컨텍스트 매니저 (가장 간단한 방식) ---
# stream.text_stream은 텍스트 조각만 순서대로 꺼내 줍니다.
# 채팅 UI처럼 "글자가 생성되는 즉시 보여주기"에 가장 쓰기 쉽습니다.
print("=== 스트리밍 응답 (도착한 텍스트 조각을 즉시 출력) ===")

with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[
        {"role": "user", "content": "AI Agent가 뭔지 3문장으로 설명해주세요."}
    ],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

print()  # 스트리밍 출력이 끝난 뒤 줄을 바꿔 화면을 정리합니다.

# 스트리밍 중에는 조각을 바로 출력하고,
# 스트리밍이 끝난 뒤에는 최종 메시지 객체에서 토큰 사용량을 확인할 수 있습니다.
final_message = stream.get_final_message()
print("-" * 60)
print("=== 스트림 종료 후 확인한 최종 사용량 ===")
print(f"입력: {final_message.usage.input_tokens}, 출력: {final_message.usage.output_tokens}")

# --- 방법 2: 이벤트 단위로 더 세밀하게 처리 ---
# 텍스트뿐 아니라 "메시지 시작", "블록 시작/종료" 같은 이벤트까지 보고 싶을 때
# stream 자체를 순회합니다. UI에서 로딩 상태나 완료 상태를 분리해 표시할 때 유용합니다.
print("\n=== 이벤트 단위 처리 ===")

with client.messages.stream(
    model="claude-sonnet-4-6",
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
                print(" [블록 끝]", end=" ")
            case "message_stop":
                print("[완료]")
            case "text":
                print(event.text, end="", flush=True)
