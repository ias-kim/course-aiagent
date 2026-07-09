"""
부록 A-9: TaskGroup 취소 전파와 태스크 상태 확인

TaskGroup은 함께 묶인 작업 중 하나가 실패하면,
아직 끝나지 않은 나머지 작업을 자동으로 취소합니다.

즉 TaskGroup은 "이 작업들은 한 세트다"라고 표현하는 도구입니다.
한 세트 안에서 실패가 나면 남은 일을 정리하고, 예외를 호출자에게 알려줍니다.

이 파일에서는 그 취소가 어떻게 전파되는지 눈으로 확인하고,
끝난 태스크의 상태(성공/실패/취소)를 안전하게 구분하는 방법을 다룹니다.

3가지 포인트:
    1. 하나가 실패하면 나머지는 자동 취소된다 (except* / else로 경로 분리)
    2. 성공·실패·취소 상태는 정해진 순서로 확인해야 한다
    3. gather는 TaskGroup과 달리 형제 태스크를 자동 취소하지 않는다
"""

import asyncio


# ============================================================
# 패턴 1: 하나 실패 → 전원 자동 취소
# ============================================================
# 우유 주문이 접수 직후 실패하면, 같은 TaskGroup에 있던 라떼와 아아도 취소됩니다.
#
# 주의: 취소 신호인 CancelledError는 except Exception으로 잡히지 않습니다.
#   Python 3.8부터 BaseException의 직속 자식이 되었기 때문입니다.
#   실수로 쓴 except Exception 때문에 취소 신호가 사라지지 않도록 한 설계입니다.
#   취소를 화면에 보여주려면 명시적으로 잡고, 처리 후 반드시 다시 raise해야 합니다.

async def make_order(item: str, taken_time: int) -> str:
    try:
        print(f"  {item} 주문 접수")
        if item == "우유":
            raise ValueError("우유 품절")
        await asyncio.sleep(taken_time)
        print(f"  {item} 조리 완료")
        return f"{item} 완료"
    except asyncio.CancelledError:
        print(f"  [취소] {item}: 다른 주문 실패로 함께 취소")
        raise                        # 취소 신호는 다시 전달해야 Task가 취소 상태로 남습니다.
    except Exception as e:
        print(f"  [실패] {item}: {e}")
        raise                        # TaskGroup이 예외를 수거하고 형제 Task를 정리하도록 재전파합니다.


async def pattern1():
    print("[패턴 1] 하나 실패 → 전원 자동 취소")
    try:
        async with asyncio.TaskGroup() as tg:
            task1 = tg.create_task(make_order("라떼", 4))
            task2 = tg.create_task(make_order("아아", 1))
            task3 = tg.create_task(make_order("우유", 3))
    except* ValueError as eg:
        # print(eg)는 "unhandled errors ..." 형태의 요약만 보여줍니다.
        # 실제 개별 예외는 eg.exceptions를 순회해야 확인할 수 있습니다.
        for e in eg.exceptions:
            print(f"  [그룹 예외] {e}")
    else:
        # 예외가 없을 때만 실행되는 성공 경로입니다.
        # TaskGroup 블록을 빠져나온 뒤라서 result()를 안전하게 호출할 수 있습니다.
        print(f"  {task1.result()}, {task2.result()}, {task3.result()}")


# ============================================================
# 패턴 2: 성공·실패·취소 - 세 상태를 안전하게 구분하기
# ============================================================
# 이번에는 우유가 3초 동안 일한 뒤 실패하도록 바꿉니다.
# 그러면 타임라인이 이렇게 갈라집니다:
#   1초: 아아 완료(성공) → 3초: 우유 실패 → 라떼는 조리 중 취소
# 즉, 성공·실패·취소 상태가 한 번에 공존합니다.
#
# 이때 확인 순서가 중요합니다. cancelled()를 가장 먼저 봐야 합니다.
# 취소된 태스크에 exception()이나 result()를 호출하면 CancelledError가 발생합니다.

async def slow_fail_order(item: str, taken_time: int) -> str:
    """일정 시간 뒤 성공하거나, 우유만 실패하는 주문 시뮬레이션입니다."""
    print(f"  {item} 주문 접수")
    await asyncio.sleep(taken_time)
    if item == "우유":
        raise ValueError("우유 품절")     # 3초 일한 뒤에 실패
    print(f"  {item} 조리 완료")
    return f"{item} 완료"


async def pattern2():
    print("\n[패턴 2] 성공/실패/취소 상태 구분")
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(slow_fail_order("라떼", 4), name="라떼"),
                tg.create_task(slow_fail_order("아아", 1), name="아아"),
                tg.create_task(slow_fail_order("우유", 3), name="우유"),
            ]
    except* ValueError:
        pass                             # 상태는 아래에서 일괄 확인

    for t in tasks:
        if t.cancelled():                # ① 취소 여부부터
            print(f"  {t.get_name()}: 취소됨")
        elif t.exception():              # ② 예외로 죽었나
            print(f"  {t.get_name()}: 실패 - {t.exception()}")
        else:                            # ③ 정상 완료
            print(f"  {t.get_name()}: {t.result()}")


# ============================================================
# 패턴 3: 비교 - gather는 형제를 취소하지 않는다
# ============================================================
# gather는 첫 번째 예외를 호출자에게 전달하지만,
# 이미 시작된 나머지 작업을 자동으로 취소하지는 않습니다.
# 예외를 받은 뒤에도 라떼가 "조리 완료"를 출력하는 것이 그 증거입니다.
# TaskGroup은 이런 작업 묶음을 더 안전하게 정리하기 위해 도입되었습니다.

async def pattern3():
    print("\n[패턴 3] gather는 취소하지 않음")
    try:
        await asyncio.gather(
            slow_fail_order("라떼", 2),
            slow_fail_order("우유", 1),
        )
    except ValueError as e:
        print(f"  [실패] {e}: 예외를 받은 시점. 라떼의 운명은?")

    await asyncio.sleep(2)               # main을 살려두어 라떼가 계속 도는지 관찰합니다.
    print("  → 라떼가 계속 돌고 있었음 (TaskGroup이었다면 취소됐을 것)")


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
    print("  TaskGroup: 하나 실패 → 나머지 '자동' 취소 (gather는 안 함)")
    print("  결과 조회는 블록 밖에서: else(성공 경로) 또는 상태 확인")
    print("  상태 확인 순서: cancelled() → exception() → result()")
    print("  CancelledError는 except Exception에 안 잡힘 → 명시적으로 잡고 재전파")


if __name__ == "__main__":
    asyncio.run(main())
