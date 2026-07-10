"""
Chapter 1-10: 실무형 API 호출 함수 만들기 (종합)

지금까지 배운 조각들을 하나의 "단일 진입점 함수"로 조립합니다.
앱의 여러 곳에서 SDK를 직접 호출하면 timeout, 재시도, 로그, 에러 처리 방식이
곳곳에 흩어집니다. 실무에서는 보통 LLM 호출 경계를 함수 하나로 모아 둡니다.

이 파일의 목표는 "텍스트 응답을 받는 기본형 call_llm()"입니다.
구조화 출력과 Pydantic 검증까지 결합한 실무형은 chapter2/08에서 이어집니다.

앞에서 배운 내용과 연결하면:
    - 07_error_handling:  예외 타입 구분, 재시도
    - 09_timeout:         진행 감시(SDK) + 총량 감시(asyncio.timeout) 겹쳐 쓰기
    - 부록 A-8:           Semaphore 동시성 제한

실무 스타일의 핵심 결정 9가지:
    ① 튜닝 상수(모델, 동시성, 타임아웃)는 상단에 모아둔다
    ② 클라이언트는 프로세스당 1개 — 커넥션 풀을 재사용한다
    ③ 운영 중 생길 수 있는 실패는 예외가 아니라 "값"(Result 타입)으로 돌려준다
    ④ 옵션 인자는 키워드 전용(*)으로 받는다
    ⑤ 방어는 3겹: Semaphore → asyncio.timeout → SDK(재시도 내장)
    ⑥ 예외는 구체적 타입부터 순서대로 잡는다
    ⑦ stop_reason을 확인한다 — "응답이 왔다 ≠ 완전한 응답이다"
    ⑧ 지연 시간과 토큰 사용량을 로그로 남긴다
    ⑨ 설정/코드 버그(400/401/404)는 값으로 덮지 않는다 — fail fast

이 파일은 비동기 코드입니다. async/await가 처음이라면 부록 A-1~A-3을 먼저 보세요.
"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx
import anthropic
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

load_dotenv()
logger = logging.getLogger("llm")

# ── ① 튜닝 지점은 상수로 한곳에 ──────────────────────────
# 운영 중 조정할 가능성이 큰 값은 파일 상단에 모아 둡니다.
# 이렇게 해야 "어디서 timeout을 바꾸지?" 같은 추적 비용이 줄어듭니다.
MODEL = "claude-sonnet-4-6"
MAX_CONCURRENCY = 5                                   # 동시 호출 제한 (rate limit 예방)
REQUEST_TIMEOUT = httpx.Timeout(30.0, connect=3.0)    # 진행 감시 — 시도당 (09 참고)
TOTAL_DEADLINE = 90.0                                 # API 호출 구간 총량 — 재시도 포함 (초)

# ── ② 클라이언트는 프로세스당 1개 — 커넥션 풀 재사용 ──────
# 호출마다 AsyncAnthropic()을 만들면 TLS 핸드셰이크와 커넥션 풀이 매번 새로 만들어집니다.
# 앱 시작 시 한 번 만들고 재사용하는 편이 빠르고 안정적입니다.
# max_retries는 SDK의 전송 재시도입니다. 연결 실패, 429, 5xx 같은 일시적 실패를
# SDK가 백오프로 다시 시도하고, 그래도 실패하면 아래 except로 최종 예외가 올라옵니다.
client = AsyncAnthropic(timeout=REQUEST_TIMEOUT, max_retries=2)
_sem = asyncio.Semaphore(MAX_CONCURRENCY)


# ── ③ 실패를 "값"으로 돌려주는 결과 타입 ─────────────────
# 호출부 수십 곳에 try/except를 강요하지 않기 위한 설계입니다.
# 단, 모든 예외를 삼킨다는 뜻은 아닙니다.
# rate limit, timeout, 서버 오류처럼 운영 중 예상 가능한 실패는 LLMResult로 번역하고,
# 잘못된 API 키나 잘못된 모델명처럼 배포/코드 버그에 가까운 4xx는 그대로 터뜨립니다.
# error는 짧은 코드 문자열이라 분기와 모니터링 집계에 바로 쓸 수 있습니다.
@dataclass
class LLMResult:
    ok: bool
    text: str = ""
    error: str = ""


async def call_llm(
    prompt: str,
    *,                                    # ④ 옵션은 키워드 전용 — 위치 인자 사고 방지
    system: str | None = None,
    max_tokens: int = 1024,
    deadline: float = TOTAL_DEADLINE,
) -> LLMResult:
    """
    LLM 호출 단일 진입점.

    앱의 다른 코드는 SDK timeout, 재시도, 네트워크 예외를 직접 다루지 않습니다.
    호출부는 LLMResult(ok/text/error)만 보고 다음 행동을 결정합니다.

    예외적으로 400/401/404 같은 설정·코드 버그는 여기서 잡지 않습니다.
    그런 문제는 폴백으로 감추지 말고 배포 초기에 크게 실패시키는 편이 안전합니다.
    """
    start = time.monotonic()

    async with _sem:                                      # ⑤ 1겹: 동시성 제한
        # deadline은 Semaphore 자리를 얻은 뒤의 API 호출 구간에 적용됩니다.
        # 큐 대기 시간까지 SLA에 포함하고 싶다면 asyncio.timeout을 _sem 바깥으로 옮깁니다.
        try:
            async with asyncio.timeout(deadline):         # ⑤ 2겹: 총량 마감 (벽시계)
                resp = await client.messages.create(      # ⑤ 3겹: SDK 진행 감시 + 자동 재시도
                    model=MODEL,
                    max_tokens=max_tokens,
                    system=system or anthropic.NOT_GIVEN,  # None/빈 문자열이면 system 필드 생략
                    messages=[{"role": "user", "content": prompt}],
                )
        except TimeoutError:                              # ⑥ 총량 마감 초과 (벽시계 발동)
            # 이 timeout은 SDK 재시도와 백오프까지 포함한 바깥 마감입니다.
            # 마감이 지났는데 다시 전송하면 deadline의 의미가 없어지므로 여기서 포기합니다.
            logger.warning("총량 마감 초과 %.1fs", time.monotonic() - start)
            return LLMResult(ok=False, error="deadline_exceeded")
        except anthropic.RateLimitError:                  # SDK 재시도 소진 후의 최종 실패
            logger.warning("rate limit — 재시도 소진")
            return LLMResult(ok=False, error="rate_limited")
        except anthropic.APIStatusError as e:             # 그 외 HTTP 오류
            if e.status_code < 500:
                # 400: 요청 파라미터 오류, 401: API 키 문제, 404: 모델명/리소스 오류.
                # 이런 문제는 기다리거나 폴백해도 해결되지 않는 경우가 많습니다.
                # 값으로 덮지 않고 그대로 올려서 배포/설정 사고를 빨리 발견합니다.
                raise
            # 5xx는 서버 측 일시 장애일 수 있습니다.
            # SDK가 이미 재시도한 뒤에도 실패한 최종 결과만 여기로 옵니다.
            logger.error("HTTP %s request_id=%s", e.status_code, e.request_id)
            return LLMResult(ok=False, error=f"api_{e.status_code}")
        except anthropic.APIConnectionError:              # 네트워크 문제 (APITimeoutError 포함)
            # DNS, 연결 끊김, SDK read/connect timeout 같은 전송 계층 실패입니다.
            # 이것도 SDK 재시도를 거친 뒤의 최종 실패입니다.
            logger.error("연결 실패")
            return LLMResult(ok=False, error="connection")

    if resp.stop_reason == "max_tokens":                  # ⑦ 잘린 응답은 성공으로 보지 않음
        # HTTP 요청은 성공했고 텍스트도 왔지만, 모델이 max_tokens 상한에서 멈췄습니다.
        # 사용자에게 완성 답변처럼 보여주기보다 max_tokens 조정이나 재요청을 선택하게 합니다.
        logger.warning("응답 잘림 — max_tokens=%d 상향 검토", max_tokens)
        return LLMResult(ok=False, error="truncated")

    # 응답 content는 리스트입니다. 지금은 일반 텍스트 호출이므로 text 블록만 꺼냅니다.
    # Tool Use나 멀티모달 응답을 다루는 함수라면 여기의 추출 로직이 달라집니다.
    text = next((b.text for b in resp.content if b.type == "text"), "")
    logger.info(                                          # ⑧ 관측: 지연·토큰 기록
        "ok %.1fs in=%d out=%d",
        time.monotonic() - start,
        resp.usage.input_tokens,
        resp.usage.output_tokens,
    )
    return LLMResult(ok=True, text=text)


# ============================================================
# 사용 예 — 호출부에는 try/except가 없다는 점에 주목!
# 운영 중 예상 가능한 실패는 LLMResult 값으로 돌아오므로 UI/서비스 코드는 r.ok로 분기합니다.
# 설정·코드 버그성 4xx는 의도적으로 예외가 새도록 둡니다.
# ============================================================

async def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")

    print("=" * 60)
    print("1) 정상 호출 — 여러 개를 동시에 (Semaphore가 개수 제한)")
    print("관찰 포인트: 호출자는 SDK 예외 대신 동일한 LLMResult 인터페이스를 봅니다.")
    print("=" * 60)
    questions = [
        "파이썬이 뭐야? 한 문장으로.",
        "asyncio가 뭐야? 한 문장으로.",
        "Semaphore가 뭐야? 한 문장으로.",
    ]
    # call_llm이 운영 실패를 값으로 바꿔 주므로, 여기서는 return_exceptions가 필요 없습니다.
    results = await asyncio.gather(*(call_llm(q, max_tokens=200) for q in questions))
    for q, r in zip(questions, results):
        status = "성공" if r.ok else r.error
        print(f"  [{status}] {q}")
        if r.ok:
            preview = r.text.replace("\n", " ")[:60]
            print(f"         → {preview}")

    print()
    print("=" * 60)
    print("2) 실패 경로 — 예외가 아니라 값으로 수렴")
    print("=" * 60)

    # 잘린 응답: 긴 요청에 max_tokens 30 → stop_reason == "max_tokens"
    # 응답 객체는 왔지만 완성된 답변이 아니므로 error="truncated"로 처리합니다.
    r = await call_llm("AI의 역사를 아주 길고 자세히 설명해줘", max_tokens=30)
    print(f"  잘린 응답:  ok={r.ok}, error='{r.error}'")

    # 총량 마감 초과: 0.05초 안에 끝날 수 없음 → asyncio.timeout 발동
    # SDK 재시도 여부와 관계없이 바깥 벽시계가 전체 시간을 끊습니다.
    r = await call_llm("안녕", deadline=0.05)
    print(f"  마감 초과:  ok={r.ok}, error='{r.error}'")

    print()
    print("=" * 60)
    print("정리: 실무형 호출 함수의 계약")
    print("=" * 60)
    print("""
  이 함수 하나가 앱과 SDK 사이의 경계입니다:
    - 운영 중 예상 가능한 실패는 LLMResult로 번역
    - 설정·코드 버그성 4xx는 fail fast로 드러냄
    - 동시성·마감·재시도 정책이 전부 이 안에 있음
    - 로그에 지연·토큰·요청ID가 남아 운영 중 추적 가능

  변형이 필요할 때:
    - 구조화 출력  → messages.parse() + Pydantic (chapter2/08)
    - 긴 생성      → messages.stream() + read 타임아웃 (chapter1/09 3부)
                     스트리밍은 별도 함수로 분리 (한 함수에 다 넣지 않기)

  Pydantic 검증까지 결합한 실무형 → chapter2/08_parse_pydantic.py
""")


if __name__ == "__main__":
    asyncio.run(main())
