"""
부록 A-2: 비동기 문법 핵심 3가지

Python 비동기의 핵심 키워드는 딱 3개입니다:

    1. async def  — "이 함수는 비동기 함수입니다" 선언
    2. await      — "여기서 기다릴 테니 다른 일 해도 돼" 표시
    3. asyncio.run() — 비동기 세계의 시작점 (진입점)

비유:
    - async def  = "나는 진동벨을 받을 수 있는 사람이야"
    - await      = "진동벨 누를 때까지 다른 일 하고 있을게"
    - asyncio.run() = "카페 문 열기" (이벤트 루프 시작)

처음에는 "async 함수는 호출만으로 실행되지 않고, await 또는 asyncio.run()을 만나야
실행된다"는 점만 확실히 잡으면 됩니다.
"""

import asyncio


# ============================================================
# 1. async def — 비동기 함수 정의
# ============================================================
# 일반 함수와 모양은 비슷하지만, 호출 결과가 다릅니다.
# 일반 함수는 바로 결과를 만들고, 비동기 함수는 실행 준비 상태인 코루틴 객체를 만듭니다.

def normal_function():
    """일반 함수: 호출하면 바로 실행됨"""
    return "일반 결과"


async def async_function():
    """비동기 함수: 호출하면 '코루틴 객체'를 반환 (바로 실행되지 않음)"""
    return "비동기 결과"


async def demo_difference():
    print("[1] async def 이해하기")
    print()

    # 일반 함수: 호출 즉시 실행, 결과 반환
    result1 = normal_function()
    print(f"  일반 함수 호출 결과: {result1}")
    print(f"  타입: {type(result1)}")
    print()

    # 비동기 함수: 호출하면 코루틴 객체 반환 (아직 실행 안 됨!)
    coroutine = async_function()  # await 없이 호출
    print(f"  비동기 함수 호출 결과: {coroutine}")
    print(f"  타입: {type(coroutine)}")
    print()

    # await를 붙여야 실제로 실행되고 결과를 받을 수 있습니다.
    result2 = await async_function()
    print(f"  await로 실행한 결과: {result2}")
    print(f"  타입: {type(result2)}")

    # 위에서 await 없이 만든 코루틴도 정리합니다.
    # 코루틴 객체를 만들고 끝까지 await하지 않으면 RuntimeWarning이 날 수 있습니다.
    await coroutine


# ============================================================
# 2. await — "여기서 기다리되, 다른 일 해도 돼"
# ============================================================

async def fetch_data(name: str, seconds: int) -> str:
    """데이터 조회 시뮬레이션"""
    print(f"  📡 {name} 조회 시작... ({seconds}초 소요)")
    await asyncio.sleep(seconds)  # 여기서 기다리는 동안 다른 코루틴이 실행될 수 있습니다.
    print(f"  ✅ {name} 조회 완료!")
    return f"{name}_data"


async def demo_await():
    print("\n[2] await 이해하기")
    print()

    # 순차 await: 하나가 끝난 뒤 다음 것을 시작하므로 동기 코드와 비슷하게 보입니다.
    print("  --- 순차 await ---")
    result1 = await fetch_data("유저정보", 1)
    result2 = await fetch_data("주문내역", 1)
    print(f"  결과: {result1}, {result2}")
    print()

    # 동시 실행: gather가 두 코루틴을 함께 시작하고, 둘 다 끝날 때까지 기다립니다.
    print("  --- 동시 실행 (gather) ---")
    result1, result2 = await asyncio.gather(
        fetch_data("유저정보", 1),
        fetch_data("주문내역", 1),
    )
    print(f"  결과: {result1}, {result2}")


# ============================================================
# 3. asyncio.run() — 비동기 세계의 시작점
# ============================================================
# 일반 코드(동기)에서 비동기 코드로 들어가는 대표 진입점입니다.
# 한 프로그램의 최상위에서 보통 한 번만 호출합니다.

async def main():
    """비동기 프로그램의 메인 함수"""
    await demo_difference()
    await demo_await()

    print()
    print("=" * 50)
    print("[정리]")
    print("  async def  → 비동기 함수 선언")
    print("  await      → 비동기 함수 실행 (기다리면서 양보)")
    print("  asyncio.run() → 동기 세계에서 비동기 세계로 진입")
    print()
    print("[주의사항]")
    print("  - await는 async def 안에서만 사용 가능")
    print("  - 일반 함수에서 비동기 함수를 호출하려면 asyncio.run() 사용")
    print("  - asyncio.run()은 이미 이벤트 루프가 있으면 에러 발생")


if __name__ == "__main__":
    asyncio.run(main())  # ← 여기서 비동기 세계 시작!
