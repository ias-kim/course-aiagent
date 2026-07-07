"""
부록 A-8: 실무 동시성 제어 - timeout, Semaphore, TaskGroup

gather로 여러 코루틴을 동시에 실행하는 방법은 배웠습니다.
하지만 실제 API 호출에서는 "동시에 실행"만으로는 부족합니다:
    - 서버가 응답하지 않으면?       → 무한 대기 방지        → timeout
    - 요청 100개를 한 번에 보내면?  → rate limit 초과 방지  → Semaphore
    - 작업 묶음을 안전하게 관리하려면? → 완료 보장 + 예외 정리 → TaskGroup

이번 파일에서 볼 3가지 패턴:
    1. asyncio.timeout()  - 시간 제한 (3.11+, 구버전은 wait_for)
    2. Semaphore          - 동시 실행 개수 제한
    3. TaskGroup 조합     - 제한, 포기, 완료 보장을 함께 쓰는 형태
"""

import asyncio
import time


# ── 공통: LLM API 호출 시뮬레이션 ────────────────────

async def call_llm(prompt: str, delay: float = 1.0) -> str:
    await asyncio.sleep(delay)  # 네트워크 왕복 흉내
    return f"'{prompt}' 응답 도착"


# ============================================================
# 패턴 1: asyncio.timeout - 응답이 늦으면 포기
# ============================================================
# 외부 API를 호출할 때는 보통 "얼마나 기다릴지"를 먼저 정합니다.
# Python 3.11 미만에서는 await asyncio.wait_for(코루틴, timeout=초)를 씁니다.

async def pattern1():
    print("[패턴 1] asyncio.timeout: 시간 제한")

    # 정상 케이스: 1초 작업, 3초 제한
    async with asyncio.timeout(3):
        result = await call_llm("빠른 질문", delay=1)
        print(f"  성공: {result}")

    # 초과 케이스: 5초 작업, 1초 제한
    try:
        async with asyncio.timeout(1):
            await call_llm("무거운 질문", delay=5)
    except TimeoutError:
        print("  1초 안에 응답 없음 → 포기 (TimeoutError)")


# ============================================================
# 패턴 2: Semaphore - 동시 실행 개수 제한
# ============================================================
# 요청 6개를 한 번에 보내지 않고, 동시에 최대 2개만 실행되도록 조절합니다.
# API rate limit을 지키며 대량 호출을 처리할 때 자주 쓰는 패턴입니다.

async def pattern2():
    print("\n[패턴 2] Semaphore: 동시 실행 개수 제한")

    sem = asyncio.Semaphore(2)  # 동시에 최대 2개
    active = 0                  # 현재 실행 중인 개수 (관찰용)

    async def limited_call(n: int) -> str:
        nonlocal active
        async with sem:         # 자리가 날 때까지 여기서 대기
            active += 1
            print(f"  요청{n} 시작 (동시 실행: {active}개)")
            result = await call_llm(f"질문{n}", delay=1)
            active -= 1
            return result

    start = time.time()
    await asyncio.gather(*[limited_call(n) for n in range(1, 7)])
    print(f"  6개 완료: 소요 {time.time() - start:.1f}초 (2개씩 3턴 = 약 3초)")


# ============================================================
# 패턴 3: TaskGroup + Semaphore + timeout - 실무 조합
# ============================================================
# 실제 코드에서는 세 도구를 함께 쓰는 경우가 많습니다:
#   TaskGroup  → 블록을 빠져나올 때 모든 작업의 종료를 보장
#   Semaphore  → 동시에 실행되는 요청 수를 제한
#   timeout    → 너무 느린 요청은 기다리지 않고 포기
#
# 포인트: 타임아웃을 작업 내부에서 잡아 결과값으로 바꾸면,
#   일부 요청이 실패해도 나머지 요청은 계속 진행됩니다 (부분 실패 허용).
#   반대로 예외를 그대로 두면 TaskGroup이 관련 작업을 함께 취소합니다 (A-5 패턴 3).

async def pattern3():
    print("\n[패턴 3] TaskGroup + Semaphore + timeout 조합")

    sem = asyncio.Semaphore(2)

    async def safe_call(n: int, delay: float) -> str:
        async with sem:
            try:
                async with asyncio.timeout(1.5):
                    return await call_llm(f"질문{n}", delay=delay)
            except TimeoutError:
                return f"'질문{n}' 시간 초과: 기본값으로 대체"

    delays = [0.5, 2.5, 0.5, 1.0]  # 두 번째 요청은 타임아웃될 예정
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(safe_call(n, d)) for n, d in enumerate(delays, 1)]
    # 여기까지 왔다는 것은 4개 작업이 모두 종료되었다는 뜻입니다.

    for task in tasks:
        print(f"  {task.result()}")


# ============================================================
# 실행
# ============================================================

async def main():
    await pattern1()
    await pattern2()
    await pattern3()

    print()
    print("=" * 50)
    print("[정리]")
    print("  asyncio.timeout(초)   → 늦으면 TimeoutError로 포기")
    print("  Semaphore(n)          → 동시 실행을 n개로 제한")
    print("  TaskGroup             → 블록 종료 시 전원 완료 보장")
    print("  실무 = 세 가지를 겹쳐서: 제한 + 포기 + 완료 보장")


if __name__ == "__main__":
    asyncio.run(main())
