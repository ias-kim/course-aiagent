"""
Chapter 2-9: 실무 종합 — call_llm() 스타일 가이드 (경계 계층 + Pydantic)

chapter1/10의 경계 계층 패턴과 chapter2/08의 Pydantic 검증을 결합한,
"실무에서 LLM 호출 함수를 이렇게 만든다"의 완성판입니다.

[가이드라인 체크리스트]
    ① 튜닝 상수(모델, 동시성, 타임아웃)는 상단에 모아둔다
    ② 클라이언트는 프로세스당 1개 — 커넥션 풀을 재사용한다
    ③ 전송 재시도는 SDK에 위임한다 — for문 재시도 루프를 만들지 않는다
    ④ asyncio.timeout은 "총량 마감" — 초과 시 재전송하지 않고 포기한다
    ⑤ LLM 출력은 Pydantic 모델로 스키마 강제 + 재검증한다 (신뢰 경계)
    ⑥ 실패는 예외가 아니라 값(LLMResult)으로 돌려준다 — 호출부에 try/except 없음
    ⑦ 실패 사유는 Literal 코드로 고정한다 — 오타 코드가 생성 시점에 걸림
    ⑧ 설정/코드 버그(400/401/404)는 잡지 않는다 — fail fast, 폴백으로 덮으면 사고 은폐
    ⑨ stop_reason을 확인한다 — "응답 도착 ≠ 완전한 응답"
    ⑩ 지연 시간과 토큰 사용량을 로그로 남긴다 — 운영 중 추적 가능하게

이 파일은 비동기 코드입니다 (부록 A-1~A-3 선행 권장).
"""

import asyncio
import logging
import time
from typing import Literal

import httpx
import anthropic
from dotenv import load_dotenv
from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

load_dotenv()
logger = logging.getLogger("llm")

# ── ① 튜닝 상수는 한곳에 ──────────────────────────────────
MODEL = "claude-sonnet-4-6"
MAX_CONCURRENCY = 3                                  # 동시 호출 제한 (rate limit 예방)
REQUEST_TIMEOUT = httpx.Timeout(30.0, connect=3.0)   # 진행 감시 — HTTP 시도당
TOTAL_DEADLINE = 60.0                                # 총량 마감 — 재시도 포함 상한

# ── ② 클라이언트는 프로세스당 1개, ③ 전송 재시도는 SDK에 ──
client = AsyncAnthropic(timeout=REQUEST_TIMEOUT, max_retries=3)
sem = asyncio.Semaphore(MAX_CONCURRENCY)


# ── ⑤ 신뢰 경계용 모델: LLM 출력의 스키마이자 검증기 ─────
# 이 모델에서 JSON 스키마가 자동 생성되어 서버로 가고(구조화 생성),
# 돌아온 응답이 같은 모델로 다시 검증됩니다 (08 참고).
class Answer(BaseModel):
    답변: str
    확신도: Literal["높음", "중간", "낮음"]   # enum 역할 — 세 값만 허용


# ── ⑥⑦ 내부 결과 타입: 실패를 값으로, 사유는 Literal로 ────
# LLM 출력(외부 데이터)과 달리 LLMResult는 우리 코드가 조립하는 내부 값이라
# 검증 필요는 없지만, FastAPI 등으로 그대로 직렬화해 내보내는 서비스라면
# Pydantic으로 통일하는 관례가 실무에 흔합니다 (내부 전용이면 dataclass도 충분 — ch1/10).
ErrorCode = Literal[
    "",                   # 성공 시 기본값
    "deadline_exceeded",  # 총량 마감 초과
    "rate_limited",       # SDK 재시도 소진 후에도 429
    "server_error",       # 5xx (재시도 소진)
    "connection",         # 네트워크/SDK 타임아웃
    "truncated",          # max_tokens로 잘림 (유효한 JSON 경계에서 잘린 드문 경우)
    "invalid_output",     # LLM 출력이 스키마 검증 실패 (잘린 JSON 대부분 포함)
]


class LLMResult(BaseModel):
    ok: bool
    answer: Answer | None = None    # 성공 시 검증 완료된 구조화 답변
    error: ErrorCode = ""


async def call_llm(
    question: str,
    *,                                   # 옵션은 키워드 전용 — 위치 인자 사고 방지
    max_tokens: int = 300,
    deadline: float = TOTAL_DEADLINE,
) -> LLMResult:
    """경계 함수 — 앱과 SDK 사이의 유일한 관문.

    전송 실패(SDK 재시도 소진 후의 최종 실패)와 검증 실패를 모두 값으로 번역합니다.
    설정/코드 버그(401 인증, 404 모델명, 400 요청 오류)는 잡지 않고 크게
    실패시킵니다(fail fast) — 폴백으로 덮으면 배포 사고가 은폐됩니다.
    """
    start = time.monotonic()

    async with sem:                                       # 방어 1겹: 동시성 제한
        try:
            async with asyncio.timeout(deadline):         # 방어 2겹: 총량 마감 (벽시계)
                rsp = await client.messages.parse(        # 방어 3겹: SDK 진행 감시 + 자동 재시도
                    model=MODEL,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": question}],
                    output_format=Answer,                 # ⑤ Pydantic 모델 = 스키마 + 검증기
                )
        except TimeoutError:
            # ④ 총량 마감 초과 = 예산 소진. 재전송하면 마감의 의미가 없어지므로 포기.
            logger.warning("총량 마감 초과: %s", question)
            return LLMResult(ok=False, error="deadline_exceeded")
        except ValidationError as e:
            # 응답은 왔지만(HTTP 200) 스키마 검증 실패 — 잘린 JSON도 대부분 여기로.
            # 전송 실패가 아니라 "의미 계층" 실패이므로 SDK는 재시도하지 않습니다.
            # (필요하면 이 지점이 피드백 재요청 같은 의미 계층 재시도의 자리입니다)
            logger.warning("출력 검증 실패 %d건: %s", e.error_count(), question)
            return LLMResult(ok=False, error="invalid_output")
        except anthropic.RateLimitError:
            # SDK가 백오프로 재시도한 뒤에도 429 → 최종 실패로 번역.
            return LLMResult(ok=False, error="rate_limited")
        except anthropic.APIStatusError as e:
            if e.status_code < 500:
                raise            # ⑧ 400/401/404 등 설정·코드 버그 → fail fast (잡지 않음)
            return LLMResult(ok=False, error="server_error")
        except anthropic.APIConnectionError:
            # 네트워크 실패·SDK 타임아웃(APITimeoutError 포함) — 재시도 소진 후 도착.
            return LLMResult(ok=False, error="connection")

    if rsp.stop_reason == "max_tokens":                   # ⑨ 잘린 응답은 성공이 아니다
        return LLMResult(ok=False, error="truncated")

    logger.info(                                          # ⑩ 관측: 지연·토큰 기록
        "ok %.1fs in=%d out=%d",
        time.monotonic() - start,
        rsp.usage.input_tokens,
        rsp.usage.output_tokens,
    )
    return LLMResult(ok=True, answer=rsp.parsed_output)   # 검증 완료된 Answer 인스턴스


# ============================================================
# 사용 예 — 호출부에는 try/except가 없다는 점에 주목!
# ============================================================

async def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(name)s: %(message)s")

    print("=" * 60)
    print("성공/실패가 모두 값(LLMResult)으로 수렴")
    print("=" * 60)

    results = await asyncio.gather(          # 경계가 값을 보장 → return_exceptions 불필요
        call_llm("한국의 수도는?"),                            # 정상 경로
        call_llm("파이썬이란?", deadline=1),                   # 총량 마감 초과 유도
        call_llm("파이썬의 역사를 아주 자세히", max_tokens=60),  # 잘림 → 검증 실패 유도
    )

    labels = ["정상", "마감 1초", "max_tokens 60"]
    for label, r in zip(labels, results):
        if r.ok:
            print(f"  [{label}] 성공 (확신도: {r.answer.확신도}) {r.answer.답변[:40]}")
        else:
            print(f"  [{label}] 실패 — {r.error}")

    # Pydantic 통일의 실익: FastAPI라면 `return r`로 끝 (직렬화 공짜)
    print("\nJSON 직렬화 예시:")
    print(f"  {results[0].model_dump_json(exclude_none=True)}")

    print()
    print("=" * 60)
    print("정리: call_llm() 실무 가이드라인")
    print("=" * 60)
    print("""
  "SDK는 던지고, 경계는 번역하고, 호출부는 분기한다"

  1. 전송 재시도(연결·429·5xx)  → SDK에 위임 (max_retries)
  2. 총량 마감(SLA)             → asyncio.timeout, 초과 시 재전송 없이 포기
  3. LLM 출력(신뢰 경계)        → Pydantic 모델로 스키마 강제 + 재검증
  4. 일시적 실패                → 값(ErrorCode)으로 번역
  5. 설정/코드 버그(4xx)        → 잡지 않음, fail fast
  6. 호출부                     → r.ok로 분기만, try/except 없음
""")


if __name__ == "__main__":
    asyncio.run(main())
