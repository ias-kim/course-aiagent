"""
부록 A-7: 메인 Task와 종료 시 일괄 취소

asyncio.run(main())에 넘긴 코루틴은 "메인 Task"로 승격됩니다.
프로그램 전체의 수명은 이 메인 Task가 쥐고 있습니다:
메인 Task가 끝나면 이벤트 루프도 닫히고,
아직 끝나지 않은 나머지 Task는 전부 취소(cancel)됩니다.

asyncio.run()의 내부 동작 (단순화):
    1. 이벤트 루프 생성
    2. 코루틴을 메인 Task로 감싸서 실행    ← create_task와 동일
    3. 메인 Task가 끝날 때까지 루프 가동
    4. 남은 Task 전부 cancel()             ← 뒷정리 (이 파일의 주제!)
    5. 취소가 전파되도록 루프를 한 번 더 돌린 뒤 폐쇄

핵심 개념:
    - 메인 Task:      asyncio.run()이 코루틴을 감싸 만든 최상위 Task
    - CancelledError: cancel()된 Task의 await 지점에 던져지는 예외
    - 일괄 취소:      메인 Task 종료 → 남은 Task는 완주 보장이 없다
                      (완주시키려면 반드시 await/gather로 기다려야 함)
"""

import asyncio


async def make_coffee(menu: str) -> str:
    try:
        print(f"  {menu} 제조 시작")
        await asyncio.sleep(2)
        print(f"  {menu} 제조 완료")
        return f"{menu} 완료"
    except asyncio.CancelledError:
        # cancel()되면 await 지점(asyncio.sleep)에서 이 예외가 발생합니다.
        # 뒷정리(자원 반납 등)를 할 마지막 기회입니다.
        print(f"  [취소 통보] {menu} — 조리 중단하고 정리합니다")
        raise  # 취소를 삼키지 말고 다시 던져야 정상적으로 취소 처리됩니다


# ============================================================
# 1. 메인 Task의 정체 — main()도 결국 하나의 Task
# ============================================================

async def who_am_i():
    """asyncio.current_task()로 지금 실행 중인 Task를 확인할 수 있습니다."""
    print("[1] 메인 Task의 정체")

    me = asyncio.current_task()
    print(f"  현재 Task 이름: {me.get_name()}")        # Task-1 — run()이 만든 첫 Task
    print(f"  Task 객체인가?  {isinstance(me, asyncio.Task)}")
    print("  → asyncio.run()이 코루틴을 감싸 만든 '메인 Task'입니다\n")


# ============================================================
# 2. 수동 취소 — task.cancel()
# ============================================================

async def manual_cancel():
    """
    Task는 밖에서 중단시킬 수 있습니다.
    cancel()을 호출하면 Task의 await 지점에 CancelledError가 던져집니다.
    """
    print("[2] 수동 취소 — task.cancel()")

    task = asyncio.create_task(make_coffee("라떼"))
    await asyncio.sleep(1)      # 1초 뒤 손님이 주문 취소
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print("  → 주문이 취소되어 라떼는 나오지 않았습니다\n")


# ============================================================
# 3. 종료 시 일괄 취소 — await 없이 남겨진 Task의 운명
# ============================================================

async def abandoned_tasks():
    """
    create_task만 하고 await하지 않은 채 메인 Task가 끝나면?
    → asyncio.run()의 뒷정리 단계에서 전부 cancel됩니다.
    → 아래 [취소 통보] 출력은 main()이 끝난 "이후"에 나옵니다!
    """
    print("[3] 종료 시 일괄 취소 — await 없이 방치된 Task")

    asyncio.create_task(make_coffee("말차"))
    asyncio.create_task(make_coffee("아메리카노"))
    # await 없이 함수 종료 → 곧 메인 Task도 종료 → 두 Task는 일괄 취소됨


# ============================================================
# 실행
# ============================================================

async def main():
    print("=" * 50)
    await who_am_i()

    print("=" * 50)
    await manual_cancel()

    print("=" * 50)
    print("[정리]")
    print("  asyncio.run(coro)   → coro를 '메인 Task'로 승격해 실행")
    print("  메인 Task 종료      → 루프 종료 + 남은 Task 일괄 cancel")
    print("  cancel()            → await 지점에 CancelledError 주입")
    print("  except CancelledError → 뒷정리 기회 (반드시 raise로 재전파)")
    print("  완주가 필요한 Task  → 반드시 await / gather로 기다릴 것")

    print("=" * 50)
    await abandoned_tasks()
    print("main() 종료  ← 이 줄 다음에 나오는 출력이 '뒷정리 단계'입니다")


if __name__ == "__main__":
    asyncio.run(main())
    # 여기 도달했다는 것은: 메인 Task 종료 → 남은 Task 취소 → 루프 폐쇄까지 완료
