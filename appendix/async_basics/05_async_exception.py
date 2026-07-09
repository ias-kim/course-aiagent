"""
부록 A-5: 비동기 예외 처리

비동기 코드에서 에러가 발생하면 어떻게 될까?
동시에 실행 중인 여러 작업 중 하나가 실패했을 때의 처리 방법을 다룹니다.

핵심 질문은 두 가지입니다:
    - 하나가 실패해도 나머지를 계속 돌릴 것인가?
    - 아니면 묶음 전체를 실패로 보고 함께 멈출 것인가?

4가지 패턴:
    1. 개별 try/except      — 각 코루틴이 자체적으로 에러 처리
    2. gather + return_exceptions — 전부 실행 후 성공/실패 분류
    3. TaskGroup            — 하나 실패 시 나머지 자동 취소
    4. 재시도 (Retry)       — 일시적 오류에 N회 재시도
"""

import asyncio


# ── 공통: API 호출 시뮬레이션 ────────────────────

async def call_api(name: str, fail: bool = False) -> str:
    """1초 뒤 성공하거나, fail=True이면 ConnectionError를 발생시킵니다."""
    await asyncio.sleep(1)
    if fail:
        raise ConnectionError(f"{name} 서버 연결 실패")
    return f"{name} 응답 OK"


# ============================================================
# 패턴 1: 개별 try/except
# ============================================================
# 각 작업이 독립적이고, 하나가 실패해도 나머지는 계속 진행해야 할 때 사용합니다.

async def safe_call(name: str) -> str:
    try:
        return await call_api(name, fail=(name == "결제"))
    except ConnectionError as e:
        # 예외를 여기서 값으로 바꾸면 gather 입장에서는 "성공한 작업"처럼 보입니다.
        print(f"  [에러] {e}")
        return f"{name} 실패 — 기본값 반환"


async def pattern1():
    print("[패턴 1] 개별 try/except")
    results = await asyncio.gather(
        safe_call("인증"),
        safe_call("결제"),     # 실패해도 다른 작업 정상 진행
        safe_call("알림")
    )
    for r in results:
        print(f"  결과: {r}")


# ============================================================
# 패턴 2: gather + return_exceptions
# ============================================================
# 모든 작업을 실행한 뒤, 성공과 실패를 한꺼번에 분류할 때 사용합니다.
#
# return_exceptions=False (기본값):
#   → 하나라도 실패하면 gather 자체가 예외를 던짐
#
# return_exceptions=True:
#   → 예외 객체를 결과 리스트에 포함, gather는 중단되지 않음

async def pattern2():
    print("\n[패턴 2] gather + return_exceptions=True")
    results = await asyncio.gather(
        call_api("인증"),
        call_api("결제", fail=True),
        call_api("알림"),
        return_exceptions=True,         # 예외를 던지지 않고 결과 리스트에 담습니다.
    )
    for r in results:
        if isinstance(r, Exception):
            print(f"  [실패] {r}")
        else:
            print(f"  [성공] {r}")


# ============================================================
# 패턴 3: TaskGroup — 하나 실패 시 전체 취소 (Python 3.11+)
# ============================================================
# 전부 성공해야 의미 있는 작업 (예: 트랜잭션)
#
# 여기서는 "묶어서 잡는 법(except*)"까지만 봅니다.
# 취소가 어떻게 전파되는지, 태스크별 성공/실패/취소 상태 확인,
# gather와의 차이는 09_taskgroup_cancellation.py에서 자세히 다룹니다.

async def pattern3():
    print("\n[패턴 3] TaskGroup — 하나 실패 → 전체 취소")
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(call_api("인증"))
            tg.create_task(call_api("결제", fail=True))  # 실패 → 나머지 취소
            tg.create_task(call_api("알림"))
    except* ConnectionError as eg:
        # TaskGroup에서 여러 예외가 동시에 나올 수 있으므로 except*로 묶어서 처리합니다.
        for e in eg.exceptions:
            print(f"  [그룹 실패] {e}")


# ============================================================
# 패턴 4: 재시도 (Retry)
# ============================================================
# 네트워크 오류 등 일시적 실패에 대해 N회 재시도합니다.
# 실제 서비스에서는 지수 백오프와 최대 대기 시간도 함께 둡니다.

async def call_with_retry(name: str, max_retries: int = 3) -> str:
    for attempt in range(1, max_retries + 1):
        try:
            fail = (attempt < 3)  # 시뮬레이션: 1, 2번째 실패 후 3번째 성공
            result = await call_api(name, fail=fail)
            print(f"  {name}: {attempt}번째 시도 성공")
            return result
        except ConnectionError:
            print(f"  {name}: {attempt}번째 시도 실패")
            if attempt == max_retries:
                raise
            await asyncio.sleep(0.5)  # 바로 재시도하지 않고 잠깐 대기합니다.


async def pattern4():
    print("\n[패턴 4] 재시도 (Retry)")
    result = await call_with_retry("결제")
    print(f"  최종 결과: {result}")


# ============================================================
# 실행
# ============================================================

async def main():
    await pattern1()
    await pattern2()
    await pattern3()
    await pattern4()

    print()
    print("=" * 50)
    print("[정리]")
    print("  패턴 1: 개별 try/except    → 실패해도 다른 작업 계속")
    print("  패턴 2: return_exceptions  → 전부 실행 후 성공/실패 분류")
    print("  패턴 3: TaskGroup          → 하나 실패 시 전체 취소")
    print("  패턴 4: Retry              → 일시적 오류에 재시도")


if __name__ == "__main__":
    asyncio.run(main())
