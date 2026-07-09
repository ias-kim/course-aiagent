"""
부록 A-3: Task와 Future — 동시 실행의 핵심

await만으로는 "순차 실행"밖에 안 됩니다.
동시에 여러 작업을 돌리려면 코루틴을 Task로 만들어
이벤트 루프의 대기열에 등록해야 합니다.

중요한 구분:
    - 코루틴: 실행할 수 있는 일의 설명서
    - Task: 그 설명서를 이벤트 루프에 맡긴 실행 단위

핵심 개념:
    - Future: 아직 결과가 없지만, 나중에 결과가 채워질 "빈 상자"
    - Task:   Future + 코루틴을 실행하는 기능 (Future의 하위 클래스)
    - create_task(): 코루틴 → Task로 감싸서 이벤트 루프에 등록

    1 Task = 1 코루틴 (항상 1:1 관계)
"""

import asyncio


async def make_coffee(menu: str) -> str:
    """2초 걸리는 커피 제조 작업을 흉내냅니다."""
    print(f"  {menu} 제조 시작")
    await asyncio.sleep(2)
    print(f"  {menu} 제조 완료")
    return menu


# ============================================================
# 1. await만 사용 — 순차 실행 (약 6초)
# ============================================================

async def sequential():
    print("[1] await만 사용 — 순차 실행")

    # await는 결과가 나올 때까지 현재 코루틴을 멈춥니다.
    # 그래서 아래 세 줄은 차례대로 실행되어 총 6초 정도 걸립니다.
    r1 = await make_coffee("아메리카노")  # 2초 대기
    r2 = await make_coffee("라떼")        # 2초 대기
    r3 = await make_coffee("카푸치노")    # 2초 대기

    print(f"  결과: {r1}, {r2}, {r3}\n")


# ============================================================
# 2. create_task — 동시 실행 (약 2초)
# ============================================================

async def concurrent():
    """
    create_task()로 코루틴을 Task로 만들면:
      1. 이벤트 루프 대기열에 등록됨 (바로 다음 줄 실행)
      2. 현재 코루틴이 await로 양보할 때 Task가 실행됨
      3. await task로 결과를 받을 수 있음
    """
    print("[2] create_task — 동시 실행")

    # 3개를 동시에 이벤트 루프에 등록합니다.
    # create_task()는 "이 작업도 진행해 줘"라고 루프에 맡기는 동작입니다.
    task1 = asyncio.create_task(make_coffee("아메리카노"))
    task2 = asyncio.create_task(make_coffee("라떼"))
    task3 = asyncio.create_task(make_coffee("카푸치노"))
    # 이 시점에서 3개 Task가 대기열에 들어갔습니다.
    # 현재 코루틴이 await로 제어권을 넘기면 루프가 이 Task들을 진행시킵니다.

    # await task는 "해당 Task가 끝날 때까지 기다리고 결과를 받겠다"는 뜻입니다.
    r1 = await task1
    r2 = await task2
    r3 = await task3

    print(f"  결과: {r1}, {r2}, {r3}\n")


# ============================================================
# 3. Task 상태 확인 — done(), result()
# ============================================================

async def task_status():
    """Task는 Future를 상속하므로 상태와 결과를 확인할 수 있습니다."""
    print("[3] Task 상태 확인")

    task = asyncio.create_task(make_coffee("아메리카노"))

    print(f"  완료 여부: {task.done()}")     # False — 아직 결과가 없음

    await task                                # 완료될 때까지 기다림

    print(f"  완료 여부: {task.done()}")     # True
    print(f"  결과값:   {task.result()}")    # "아메리카노"
    print()


# ============================================================
# 4. 주의: create_task만 하고 await 안 하면?
# ============================================================

async def no_await():
    """
    create_task만 하고 await하지 않으면:
    메인 Task가 먼저 끝날 수 있고, 그 경우 남은 Task는 완주하지 못합니다.

    정확한 동작: 프로그램이 끝나기 직전에 Task들이 "첫 스텝만" 실행되고
    ("제조 시작"까지 출력됨) asyncio.run()의 뒷정리 단계에서 일괄 취소됩니다.
    → 이 파일을 실행하면 맨 마지막 [정리] 출력 뒤에 "제조 시작" 두 줄이
      늦게 나타나는 이유가 바로 이것입니다.
    → 이 현상의 자세한 원리(메인 Task, 일괄 취소)는
      07_main_task_and_cancel.py에서 다룹니다.
    """
    print("[4] create_task만 하고 await 안 하면?")

    asyncio.create_task(make_coffee("아메리카노"))
    asyncio.create_task(make_coffee("라떼"))
    # await 없이 함수 종료 → main도 곧 종료 → Task들은 완주하지 못하고 취소될 수 있습니다.
    print("  → 함수가 바로 종료됨 (Task들은 완주하지 못함 — 맨 끝의 늦은 출력 참고)\n")


# ============================================================
# 실행
# ============================================================

async def main():
    import time

    print("=" * 50)
    start = time.time()
    await sequential()
    print(f"  소요시간: {time.time() - start:.1f}초")

    print("=" * 50)
    start = time.time()
    await concurrent()
    print(f"  소요시간: {time.time() - start:.1f}초")

    print("=" * 50)
    await task_status()

    print("=" * 50)
    await no_await()

    print("=" * 50)
    print("[정리]")
    print("  await func()        → 끝날 때까지 멈춤 (순차)")
    print("  create_task(func()) → 루프에 등록, 바로 다음 줄 (동시)")
    print("  await task          → Task 완료 대기 + 결과 수신")
    print("  task.done()         → 완료 여부 확인")
    print("  task.result()       → 완료 후 결과값 가져오기")


if __name__ == "__main__":
    asyncio.run(main())
