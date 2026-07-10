"""
Chapter 2-8: 실무형 Structured Outputs — messages.parse() + Pydantic 검증

07_structured_outputs.py의 json.loads 방식은 작동 원리를 보여주는 최소 예제입니다.
실무 코드에서는 스키마를 지정하는 것에 더해, 다음과 같은 예외 상황도 처리해야 합니다:
    - stop_reason == "max_tokens" → JSON이 중간에서 잘릴 수 있음
    - API 오류 (429, 5xx, 네트워크) → 응답 자체를 받지 못할 수 있음
    - 검증 실패 → 드물지만, 프로그램이 중단되지 않도록 복구 경로가 필요함

SDK의 messages.parse()는 Pydantic 모델을 받아서:
    ① 모델에서 JSON 스키마를 자동 생성해 서버에 전달합니다.  (서버 측 구조화)
    ② 돌아온 응답을 같은 모델로 다시 검증합니다.             (클라이언트 측 검증)

실무 구성 = 서버 측 구조화(1차) + 클라이언트 재검증(2차) + 예외 처리(3차)
"""

from typing import Literal

from dotenv import load_dotenv
from anthropic import Anthropic, APIConnectionError, APIStatusError
from pydantic import BaseModel, ValidationError

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """당신은 음식 후기를 분석해 "상", "중", "하" 중 하나로 분류하는 분류기입니다.

[평가 기준]
- 상: 맛있다, 정말 좋다, 추천한다, 만족한다 등 긍정 표현이 중심인 경우
- 중: 무난하다, 보통이다, 괜찮다, 약간 아쉽다 등 중립이거나 긍정과 부정이 섞인 경우
- 하: 맛없다, 입맛에 맞지 않는다, 불만족스럽다 등 부정 표현이 중심인 경우

[판단 규칙]
- 여러 문장이 입력되면 전체 내용을 종합해 하나의 평가만 내린다."""


# ============================================================
# 1부: messages.parse() — Pydantic 모델이 스키마이자 검증기
# ============================================================
# 07에서는 dict로 JSON 스키마를 직접 작성했습니다.
# 여기서는 Pydantic 모델을 정의하고, parse()가 스키마 생성과 응답 검증을 맡게 합니다.
print("=" * 60)
print("1부: messages.parse() 기본")
print("관찰 포인트: 반환값은 dict가 아니라 타입 검증을 마친 Pydantic 객체입니다.")
print("=" * 60)


class ReviewGrade(BaseModel):
    평가: Literal["상", "중", "하"]        # enum처럼 세 값만 허용
    이유: str
    긍정_표현: list[str]
    부정_표현: list[str]


resp = client.messages.parse(
    model=MODEL,
    max_tokens=300,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": "음식이 맛있습니다. 간이 조금 센 것 같아요."}],
    output_format=ReviewGrade,             # Pydantic 모델을 출력 형식으로 지정
)
result = resp.parsed_output                # 검증을 통과한 ReviewGrade 인스턴스

# dict 키가 아니라 속성으로 접근하므로 IDE 자동완성과 타입 검사의 도움을 받을 수 있습니다.
print(f"  평가: {result.평가}")
print(f"  이유: {result.이유}")
print(f"  반환 타입: {type(result).__name__} (검증 완료된 Pydantic 모델)")


# ============================================================
# 2부: 경계 방어 — 실패 경로를 값으로 수렴시키기
# ============================================================
# 스키마 기반 출력도 "정상적으로 완료된 응답"을 전제로 합니다.
# 응답이 잘리거나, API 호출이 실패하거나, 검증에 실패하는 경우는 별도로 처리해야 합니다.
# 이 함수는 실패 상황을 예외로 흘려보내지 않고 None으로 돌려주어 호출부를 단순하게 만듭니다.
print()
print("=" * 60)
print("2부: 경계 방어를 갖춘 실무형 함수")
print("관찰 포인트: 성공 결과와 잘림·검증·통신 실패 경로를 모두 정의합니다.")
print("=" * 60)


def classify_safe(review: str) -> ReviewGrade | None:
    """구조화 출력, 재검증, 예외 처리를 함께 갖춘 실무형 분류 함수"""
    try:
        resp = client.messages.parse(
            model=MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": review}],
            output_format=ReviewGrade,
        )
        if resp.stop_reason == "max_tokens":  # 토큰 제한 때문에 응답이 잘린 경우
            print("  [경고] 응답이 잘림 — max_tokens 상향 필요")
            return None
        return resp.parsed_output
    except ValidationError as e:               # Pydantic 모델 검증 실패
        print(f"  [검증 실패] {e.error_count()}건 — 재시도 대상")
        return None
    except APIConnectionError:                 # 네트워크 문제로 응답을 받지 못한 경우
        print("  [네트워크 오류] 연결 실패")
        return None
    except APIStatusError as e:                # 429, 5xx 같은 HTTP 오류
        print(f"  [API 오류] HTTP {e.status_code}")
        return None


tests = [
    "입맛에 맞지 않습니다",
    "맛집이네요",
    "무난합니다.",
]

for t in tests:
    r = classify_safe(t)
    if r is not None:
        print(f"  {t!r:25s} → {r.평가} ({r.이유[:30]}...)")
    else:
        print(f"  {t!r:25s} → 분류 실패 (폴백 처리)")


# ============================================================
# 정리
# ============================================================
print()
print("=" * 60)
print("정리: 실무형 Structured Outputs")
print("=" * 60)
print("""
1. Pydantic 모델 하나가 세 가지 역할을 겸함:
   스키마 정의 + 응답 검증 + 타입 힌트

2. messages.parse()는 Pydantic 모델을 기준으로:
   - 서버에 전달할 JSON 스키마를 만들고
   - 응답을 같은 모델로 다시 검증함

3. 다음 예외 상황은 여전히 코드에서 처리해야 함:
   - stop_reason == "max_tokens" → 잘린 응답
   - ValidationError → 검증 실패 (재시도 대상)
   - APIConnectionError / APIStatusError → 네트워크·HTTP 오류

4. 실패를 None(또는 폴백 값)으로 통일하면 호출하는 쪽 코드가 단순해짐
""")
