"""
Chapter 1-10: 실무형 API 호출 함수 만들기 (종합)

지금까지 배운 조각들을 하나의 "단일 진입점 함수"로 조립합니다.
앱의 여러 곳에서 SDK를 직접 호출하지 않고, 이 함수 하나를 통해 호출하게 만드는 것이
실무 코드의 출발점입니다.

앞에서 배운 내용과 연결하면:
    - 07_error_handling:  예외 타입 구분, 재시도
    - 09_timeout:         진행 감시(SDK) + 총량 감시(asyncio.timeout) 겹쳐 쓰기
    - 부록 A-8:           Semaphore 동시성 제한

실무 스타일의 핵심 결정 8가지:
    ① 튜닝 상수(모델, 동시성, 타임아웃)는 상단에 모아둔다
    ② 클라이언트는 프로세스당 1개 — 커넥션 풀을 재사용한다
    ③ 실패를 예외가 아니라 "값"(Result 타입)으로 돌려준다
    ④ 옵션 인자는 키워드 전용(*)으로 받는다
    ⑤ 방어는 3겹: Semaphore → asyncio.timeout → SDK(재시도 내장)
    ⑥ 예외는 구체적 타입부터 순서대로 잡는다
    ⑦ stop_reason을 확인한다 — "응답이 왔다 ≠ 완전한 응답이다"
    ⑧ 지연 시간과 토큰 사용량을 로그로 남긴다

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
TOTAL_DEADLINE = 90.0                                 # 총량 SLA — 재시도 포함 (초)

# ── ② 클라이언트는 프로세스당 1개 — 커넥션 풀 재사용 ──────
# 호출마다 AsyncAnthropic()을 만들면 TLS 핸드셰이크와 커넥션 풀이 매번 새로 만들어집니다.
# 앱 시작 시 한 번 만들고 재사용하는 편이 빠르고 안정적입니다.
client = AsyncAnthropic(timeout=REQUEST_TIMEOUT, max_retries=2)
_sem = asyncio.Semaphore(MAX_CONCURRENCY)


# ── ③ 실패를 "값"으로 돌려주는 결과 타입 ─────────────────
# 호출부 수십 곳에 try/except를 강요하지 않기 위한 설계입니다.
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

    앱의 다른 코드는 SDK 예외나 timeout 세부 설정을 몰라도 되고,
    LLMResult(ok/text/error)만 보고 다음 행동을 결정합니다.
    """
    start = time.monotonic()

    async with _sem:                                      # ⑤ 1겹: 동시성 제한
        try:
            async with asyncio.timeout(deadline):         # ⑤ 2겹: 총량 마감 (벽시계)
                resp = await client.messages.create(      # ⑤ 3겹: SDK 진행 감시 + 자동 재시도
                    model=MODEL,
                    max_tokens=max_tokens,
                    system=system or anthropic.NOT_GIVEN,  # None이면 system 필드 자체를 생략
                    messages=[{"role": "user", "content": prompt}],
                )
        except TimeoutError:                              # ⑥ 총량 마감 초과 (벽시계 발동)
            logger.warning("총량 마감 초과 %.1fs", time.monotonic() - start)
            return LLMResult(ok=False, error="deadline_exceeded")
        except anthropic.RateLimitError:                  # SDK 재시도 소진 후의 최종 실패
            logger.warning("rate limit — 재시도 소진")
            return LLMResult(ok=False, error="rate_limited")
        except anthropic.APIStatusError as e:             # 그 외 HTTP 오류 (4xx/5xx)
            logger.error("HTTP %s request_id=%s", e.status_code, e.request_id)
            return LLMResult(ok=False, error=f"api_{e.status_code}")
        except anthropic.APIConnectionError:              # 네트워크 문제 (APITimeoutError 포함)
            logger.error("연결 실패")
            return LLMResult(ok=False, error="connection")

    if resp.stop_reason == "max_tokens":                  # ⑦ 잘린 응답은 성공으로 보지 않음
        logger.warning("응답 잘림 — max_tokens=%d 상향 검토", max_tokens)
        return LLMResult(ok=False, error="truncated")

    # 응답 content는 리스트입니다. 텍스트 블록만 골라 첫 번째 텍스트를 꺼냅니다.
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
# 실패도 LLMResult 값으로 돌아오므로 UI/서비스 코드는 r.ok만 확인하면 됩니다.
# ============================================================

async def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")

    print("=" * 60)
    print("1) 정상 호출 — 여러 개를 동시에 (Semaphore가 개수 제한)")
    print("=" * 60)
    questions = [
        "파이썬이 뭐야? 한 문장으로.",
        "asyncio가 뭐야? 한 문장으로.",
        "Semaphore가 뭐야? 한 문장으로.",
    ]
    results = await asyncio.gather(*(call_llm(q, max_tokens=200) for q in questions))
    for q, r in zip(questions, results):
        status = "성공" if r.ok else r.error
        print(f"  [{status}] {q}")
        if r.ok:
            print(f"         → {r.text[:60]}")

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
    - 어떤 실패도 예외로 새지 않고 LLMResult로 수렴
    - 동시성·마감·재시도 정책이 전부 이 안에 (호출부는 몰라도 됨)
    - 로그에 지연·토큰·요청ID가 남아 운영 중 추적 가능

  변형이 필요할 때:
    - 구조화 출력  → messages.parse() + Pydantic (chapter2/08)
    - 긴 생성      → messages.stream() + read 타임아웃 (chapter1/09 3부)
                     스트리밍은 별도 함수로 분리 (한 함수에 다 넣지 않기)
""")


if __name__ == "__main__":
    asyncio.run(main())
