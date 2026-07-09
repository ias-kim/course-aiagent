"""
Chapter 2-6: Prefill과 stop_sequences — 출력 형식 강제 (레거시 기법)

04_output_control.py에서는 프롬프트로 "형식을 지켜달라"고 부탁했습니다.
이번 예제에서는 API 기능을 이용해 응답의 시작과 끝을 더 강하게 제한합니다.

- Prefill: assistant 메시지를 미리 넣어 응답이 특정 문자열 뒤에서 시작하게 만듭니다.
- stop_sequences: 지정한 문자열이 나오면 생성을 멈춰 응답의 끝을 제어합니다.
- 둘을 함께 쓰면 모델은 시작과 끝 사이에 들어갈 값만 생성하게 됩니다.

⚠️ 주의: Prefill(마지막 assistant 메시지를 미리 채우는 방식)은 Claude 4.6 이상
   모델에서 400 에러로 거부되는 레거시 기법입니다. 그래서 이 예제만 Sonnet 4.5를 씁니다.
   최신 모델에서의 대체 기법은 07_structured_outputs.py를 참고하세요.
"""

import json

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-5"  # prefill 예제를 실행하기 위해 4.5 모델 사용

SYSTEM_PROMPT = """당신은 음식 후기를 분석해 "상", "중", "하" 중 하나로 분류하는 분류기입니다.

[평가 기준]
- 상: 맛있다, 정말 좋다, 추천한다, 만족한다 등 긍정 표현이 중심인 경우
- 중: 무난하다, 보통이다, 괜찮다, 약간 아쉽다 등 중립이거나 긍정과 부정이 섞인 경우
- 하: 맛없다, 입맛에 맞지 않는다, 불만족스럽다 등 부정 표현이 중심인 경우

[판단 규칙]
- 여러 문장이 입력되면 전체 내용을 종합해 하나의 평가만 내린다.

[출력 형식]
- 설명이나 부연 없이 {"평가":"상"} 형식의 JSON 한 줄만 출력한다."""


# ============================================================
# 1부: Prefill — 응답의 시작을 강제
# ============================================================
# messages의 마지막에 assistant 메시지를 미리 넣으면,
# 모델은 그 텍스트 뒤에 이어서 응답을 생성합니다.
print("=" * 60)
print("1부: Prefill — 응답의 시작 강제")
print("=" * 60)

response = client.messages.create(
    model=MODEL,
    max_tokens=20,
    system=SYSTEM_PROMPT,
    messages=[
        {"role": "user", "content": "정말 맛있습니다."},
        {"role": "assistant", "content": '{"평가":"'},  # ← prefill
    ],
)
print(f'프리필:     {{"평가":"')
print(f"모델 생성:  {response.content[0].text!r}")
print("→ 모델이 프리필 뒤에서 이어 쓰기 때문에, 응답의 시작 형식이 고정됩니다.")


# ============================================================
# 2부: Prefill + stop_sequences — 시작과 끝을 모두 고정
# ============================================================
# stop_sequences에 지정한 문자열이 나오면, 그 문자열은 응답에 포함되지 않고 생성이 끝납니다.
# 프리필로 시작을 잡고 정지 문자열로 끝을 잡으면 모델은 가운데 "값"만 생성합니다.
#
#   {"평가":"     상     "}
#   └ prefill ┘ └모델┘ └ stop_sequence ┘
print()
print("=" * 60)
print("2부: Prefill + stop_sequences 조합")
print("=" * 60)


def classify(review: str) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=20,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": review},
            {"role": "assistant", "content": '{"평가":"'},  # 시작 고정
        ],
        stop_sequences=['"}'],                              # 끝 문자열이 나오면 생성 중단
    )
    grade = resp.content[0].text.strip()   # 모델이 실제로 생성한 내용은 값뿐입니다. (예: 상)
    # stop_reason을 확인하면 stop_sequence 때문에 생성이 멈췄는지 알 수 있습니다.
    #   resp.stop_reason == "stop_sequence", resp.stop_sequence == '"}'
    return f'{{"평가":"{grade}"}}'          # 프리필과 정지 문자열을 붙여 JSON으로 복원


tests = [
    "입맛에 맞지 않습니다",
    "맛집이네요",
    "음식이 맛있습니다. 간이 조금 센 것 같아요.",
    "무난합니다.",
    "정말 맛있습니다.",
]

for t in tests:
    result = classify(t)
    print(f"  {t!r:35s} → {result}")

# 복원한 문자열이 유효한 JSON인지 확인
print(f"\n  json.loads 검증: {json.loads(classify('맛집이네요'))}")


# ============================================================
# 정리
# ============================================================
print()
print("=" * 60)
print("정리: Prefill + stop_sequences")
print("=" * 60)
print("""
1. Prefill: 마지막 assistant 메시지 = 응답의 시작을 강제
2. stop_sequences: 지정 문자열에서 생성 중단 (정지 문자열은 응답에서 제외)
3. 둘을 조합하면 모델은 형식 사이의 "값"만 생성 → 토큰 절약 + 시작/끝 형식 고정

한계 (레거시인 이유):
- 값 자체는 검증하지 못함 ("최상"이라고 쓰면 그대로 통과)
- 잘린 문자열을 코드에서 다시 조립해야 함
- Claude 4.6+ 모델에서 prefill은 400 에러 → 07_structured_outputs.py 참고
""")
