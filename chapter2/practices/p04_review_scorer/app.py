"""
실습 P04: 음식점 후기 평가기 (Structured Outputs 실무형)

가게 후기(.txt)를 입력하면 LLM이 별점·감정·요약·키워드를 구조화된 결과로 반환하고,
브라우저가 이를 화면에 표시합니다.

이 실습의 중점은 프론트엔드가 아니라 Anthropic SDK와 출력 검증입니다.
    - output_format(Pydantic 모델)으로 응답의 스키마를 API가 보장하게 한다  → chapter2/07~08
    - messages.parse()가 스키마 생성 + 응답 재검증을 대신한다              → chapter2/08
    - LLM 출력은 "외부 데이터"이므로 신뢰 경계에서 방어한다               → chapter1/10
    - 실패(잘림/검증 실패/네트워크/HTTP)를 예외로 흘리지 않고 값으로 번역한다

동작 흐름:
    [브라우저] .txt 파일을 읽음(FileReader)
        └─ POST /evaluate {review: "..."} ──► [Flask]
                                                 └─ evaluate_review() 경계 함수
                                                      └─ client.messages.parse(output_format=Evaluation)
        ◄── {ok, evaluation | error} ──────────────────┘
    [브라우저] 결과 JSON을 받아 별점·감정·요약·키워드를 HTML로 렌더링

학습 목표:
    - System Prompt에 "평가 기준"을 넣어 채점 규칙을 고정한다
    - Pydantic 모델 하나로 스키마 정의 + 응답 검증 + 타입 힌트를 겸한다
    - 사용자 입력과 LLM 출력이라는 두 신뢰 경계를 각각 방어한다
"""

from typing import Literal

from flask import Flask, render_template, request
from dotenv import load_dotenv
from anthropic import Anthropic, APIConnectionError, APIStatusError
from pydantic import BaseModel, ValidationError

load_dotenv()

app = Flask(__name__)
client = Anthropic()

# ── 튜닝 상수는 한곳에 ────────────────────────────────────
MODEL = "claude-sonnet-4-6"      # 프로젝트 전체가 쓰는 모델 (README 기준)
MAX_TOKENS = 300                 # 간결한 JSON이면 충분 — 잘림 방지용 여유
MAX_REVIEW_CHARS = 2000          # 사용자 입력 상한 (비용·악용 방어)


# ============================================================
# 출력 스키마: Pydantic 모델이 스키마이자 검증기
# ============================================================
# 이 모델에서 JSON 스키마가 자동 생성되어 서버로 가고(구조화 생성),
# 돌아온 응답이 같은 모델로 다시 검증됩니다 (chapter2/08 참고).
# 점수·감정은 Literal(enum)이라 "허용된 값"만 나오도록 API가 보장합니다.
class Evaluation(BaseModel):
    점수: Literal[1, 2, 3, 4, 5]                    # 별점 — 다섯 값만 허용
    감정: Literal["긍정", "중립", "부정"]           # 세 값만 허용
    요약: str                                        # 한 문장 총평
    키워드: list[str]                                # 별점의 근거 표현 (3개 내외)


# ============================================================
# System Prompt: "후기를 어떻게 평가할지" 지침
# ============================================================
# 채점 기준을 구체적으로 적으면 평가의 일관성을 높일 수 있습니다.
# 생성 결과에는 여전히 변동이 있을 수 있으므로 "항상 같은 점수"를 보장하지는 않습니다.
SYSTEM_PROMPT = """당신은 음식점 후기를 분석해 별점(1~5)과 감정을 매기는 평가 전문가입니다.

[별점 기준]
- 5점: 맛·서비스·분위기 대부분이 만족스럽고 재방문/추천 의사가 뚜렷함
- 4점: 전반적으로 만족스러우나 사소한 아쉬움이 하나 정도 있음
- 3점: 좋은 점과 아쉬운 점이 비슷하게 섞여 있거나 특징 없이 무난함
- 2점: 불만이 우세하나 일부 긍정 요소가 남아 있음
- 1점: 맛·서비스·위생 등에 심각한 불만이 중심임

[감정 분류]
- 긍정: 만족·추천이 중심 (대체로 4~5점)
- 중립: 무난하거나 장단점이 비슷하게 섞임 (대체로 3점)
- 부정: 불만이 중심 (대체로 1~2점)

[판단 규칙]
- 여러 문장이 섞여 있으면 전체 맥락을 종합해 하나의 별점만 매긴다.
- 요약은 한 문장으로 핵심만 적는다.
- 키워드는 별점의 근거가 된 표현을 후기에서 3개 내외로 뽑는다."""


# ============================================================
# 경계 함수: 앱과 SDK 사이의 유일한 관문
# ============================================================
# 두 개의 신뢰 경계를 모두 방어합니다.
#   1) 사용자 입력(review)  — 빈 값/과도한 길이를 먼저 걸러냄
#   2) LLM 출력             — 스키마 검증 + 잘림/네트워크/HTTP 실패를 값으로 번역
# 실패를 예외로 흘리지 않고 dict(ok/error)로 돌려주어 호출부를 단순하게 만듭니다.
def evaluate_review(review: str) -> dict:
    review = review.strip()

    # ── 경계 1: 사용자 입력 검증 ──
    if not review:
        return {"ok": False, "error": "empty"}
    if len(review) > MAX_REVIEW_CHARS:
        return {"ok": False, "error": "too_long"}

    # ── 경계 2: LLM 호출 + 출력 방어 ──
    try:
        resp = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": review}],
            output_format=Evaluation,        # Pydantic 모델 = 스키마 + 검증기
        )
    except ValidationError:
        # 응답은 왔지만(HTTP 200) 스키마 검증 실패 — 잘린 JSON도 대부분 여기로.
        return {"ok": False, "error": "invalid_output"}
    except APIConnectionError:
        # 네트워크 실패·SDK 타임아웃 (재시도 소진 후 도착)
        return {"ok": False, "error": "connection"}
    except APIStatusError as e:
        if e.status_code < 500:
            # 400/401/404 등 설정·코드 버그 → 값으로 덮지 않고 크게 실패시킴 (fail fast)
            raise
        return {"ok": False, "error": "server_error"}

    if resp.stop_reason == "max_tokens":     # 잘린 응답은 성공이 아니다
        return {"ok": False, "error": "truncated"}

    # parsed_output은 검증을 통과한 Evaluation 인스턴스입니다.
    # 브라우저로 보내기 위해 dict로 직렬화합니다.
    return {"ok": True, "evaluation": resp.parsed_output.model_dump()}


# ============================================================
# 라우트
# ============================================================
@app.route("/")
def index():
    """후기 업로드 UI를 보여줍니다."""
    return render_template("index.html")


@app.route("/evaluate", methods=["POST"])
def evaluate():
    """
    후기 텍스트를 받아 평가 결과(JSON)를 돌려줍니다.

    호출부(이 함수)에는 try/except가 없습니다 — 경계 함수가 운영 실패를
    모두 값으로 바꿔 주기 때문입니다. (설정·코드 버그성 4xx만 예외로 새어 500이 됩니다.)
    """
    data = request.get_json(silent=True) or {}
    review = data.get("review", "")
    if not isinstance(review, str):
        return {"ok": False, "error": "bad_request"}, 400

    return evaluate_review(review)


if __name__ == "__main__":
    app.run(debug=True, port=5000)


# ============================================================
# REST API 명세
# ============================================================
#
# 1. GET /
#    후기 업로드 화면(index.html)을 반환합니다.
#
#    Response: text/html
#
# ─────────────────────────────────────────────────────────────
#
# 2. POST /evaluate
#    후기 텍스트를 받아 LLM 평가 결과를 JSON으로 반환합니다.
#
#    Request:
#      Content-Type: application/json
#      Body:
#      {
#        "review": (string, 필수) 평가할 음식점 후기 원문
#      }
#
#    Response (성공): application/json
#      {
#        "ok": true,
#        "evaluation": {
#          "점수":   4,                       # 1~5
#          "감정":   "긍정",                  # 긍정 | 중립 | 부정
#          "요약":   "양념이 좋았으나 소음이 아쉬운 곳",
#          "키워드": ["양념이 딱 좋았어요", "만족", "조금 시끄러웠지만"]
#        }
#      }
#
#    Response (실패): application/json  (HTTP 200, 실패는 값으로 수렴)
#      {"ok": false, "error": "<코드>"}
#
#      error 코드:
#        empty          — 빈 후기
#        too_long       — 입력 길이 초과 (MAX_REVIEW_CHARS)
#        invalid_output — LLM 출력이 스키마 검증 실패
#        truncated      — max_tokens로 응답이 잘림
#        connection     — 네트워크/타임아웃 실패
#        server_error   — API 5xx (재시도 소진)
#        bad_request    — 요청 형식 오류 (HTTP 400)
#
#    ※ 설정·코드 버그성 4xx(401 인증, 404 모델명 등)는 의도적으로 잡지 않아
#      서버 500으로 드러납니다(fail fast).
