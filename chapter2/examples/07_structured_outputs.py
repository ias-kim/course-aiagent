"""
Chapter 2-7: Structured Outputs — 스키마로 출력을 보장 (현대식)

06_prefill_stop_sequences.py의 목표(형식이 보장된 JSON 출력)를
최신 API 기능인 Structured Outputs로 다시 구현합니다.

- output_config.format에 JSON 스키마를 전달하면
  API가 스키마에 맞는 응답을 생성하도록 관리합니다.
- enum을 쓰면 허용한 값 안에서만 결과가 나옵니다.
- prefill과 달리 최신 모델(4.6+)에서도 동작하는 권장 방식입니다.

프롬프트(부탁) → prefill+stop(기계적 차단) → 스키마(API 보장)로
갈수록 강한 보장을 얻는 흐름을 비교해보세요.
실무형(검증·경계 방어)은 08_parse_pydantic.py에서 이어집니다.
"""

import json

from dotenv import load_dotenv
from anthropic import Anthropic

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
# 06과 달리 [출력 형식] 절이 없습니다. 응답 형식은 아래 JSON 스키마가 담당합니다.


# ============================================================
# 1부: 스키마로 분류 결과 보장
# ============================================================
# enum으로 "평가" 값의 후보를 상/중/하로 제한합니다.
print("=" * 60)
print("1부: enum 스키마로 분류")
print("=" * 60)

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "평가": {"type": "string", "enum": ["상", "중", "하"]},
    },
    "required": ["평가"],
    "additionalProperties": False,
}


def classify(review: str) -> dict:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=100,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": review}],
        output_config={"format": {"type": "json_schema", "schema": GRADE_SCHEMA}},
    )
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)   # 스키마가 응답 구조를 보장하므로 바로 파싱 가능


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


# ============================================================
# 2부: 스키마 확장 — 다중 필드도 그대로 보장
# ============================================================
# prefill+stop 조합은 단일 값 중심의 예제에 적합하지만,
# 스키마를 쓰면 필드가 늘어나도 전체 JSON 구조를 안정적으로 다룰 수 있습니다.
print()
print("=" * 60)
print("2부: 다중 필드 스키마 (prefill로는 불가능)")
print("=" * 60)

DETAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "평가": {"type": "string", "enum": ["상", "중", "하"]},
        "이유": {"type": "string", "description": "한 문장으로 요약한 판단 근거"},
        "긍정_표현": {"type": "array", "items": {"type": "string"}},
        "부정_표현": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["평가", "이유", "긍정_표현", "부정_표현"],
    "additionalProperties": False,
}

resp = client.messages.create(
    model=MODEL,
    max_tokens=300,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": "음식이 맛있습니다. 간이 조금 센 것 같아요."}],
    output_config={"format": {"type": "json_schema", "schema": DETAIL_SCHEMA}},
)
detail = json.loads(next(b.text for b in resp.content if b.type == "text"))
print(f"  평가:      {detail['평가']}")
print(f"  이유:      {detail['이유']}")
print(f"  긍정 표현: {detail['긍정_표현']}")
print(f"  부정 표현: {detail['부정_표현']}")


# ============================================================
# 정리
# ============================================================
print()
print("=" * 60)
print("정리: 출력 형식 제어 3단계 비교")
print("=" * 60)
print("""
| 방식                      | 보장 수준          | 비고                    |
|---------------------------|--------------------|------------------------|
| 프롬프트 지시 (04)        | 부탁 — 어길 수 있음 | 가장 유연, 가장 약함    |
| prefill + stop (06)       | 시작/끝만 기계적 차단 | 값 검증 불가, 4.6+ 불가 |
| Structured Outputs (07)   | 구조·값 모두 API 보장 | enum, 다중 필드, 권장   |

핵심:
1. output_config.format의 json_schema → 응답 구조를 스키마로 지정
2. enum → 허용된 값만 결과로 받도록 제한
3. required + additionalProperties: False → 필요한 필드만 명확하게 고정
4. 스키마는 필드가 늘어나도 전체 구조를 함께 관리할 수 있음
5. 실무형(messages.parse() + Pydantic 검증, 경계 방어)은
   08_parse_pydantic.py에서 이어집니다
""")
