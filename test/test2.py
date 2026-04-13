import os
import threading
import asyncio
import time

# async def test(): # call 하면 Coroutine 객체가 생성이 된다.
#     print("helo")

# asyncio.run(test()) # -> Event Loop와 Queue 생성, 첫 작업인 Task가 Qeue에 삽입이 되어야 한다.
# test() -> Coroutine 객체가 삽입된다.
#        -> Coroutine -> Task 객체로 랩핑.


async def make_coffee(menu: str)->None:
    print(f"{menu} 준비중")
    #asyncio.sleep(2) # 코루틴 객체가 만들어진다.
    await asyncio.sleep(2)
    print(f"{menu} 준비완료")

    return menu

async def main()->None:
    start_time = time.time()

    # 코루탄 -> Task로 등록 (이벤트 루프 대기열에 추가)
    task1 = asyncio.create_task(make_coffee("라뗴")) # Task 객체 -> Queuing
    task2 = asyncio.create_task(make_coffee("초코")) # Task 객체 -> Queuing
    task3 = asyncio.create_task(make_coffee("커피")) # Task 객체 -> Queuing

    # Task 완료 대기 (한 Task가 기다리면 이벤트 루프가 다른 Task를 실행함.)
    result1 = await task1
    result2 = await task2
    resutl3 = await task3
    
    print(f"완료 여부 {task1.done()}")
    print(f"결과값 {task1.result()}")
    print(result1, result2, resutl3)

# 실제 호출을 하는게 아니라 코루틴으로 감싼 객체를 호출하므로 실행이 안됨
# await가 있으면, 코루틴 객체가 만들어지지 않고 비동기 함수가 실행이 된다.

    elapsed = time.time() - start_time
    print(f"총 소요시간: {elapsed:.1f}")

if __name__ == "__main__":
    asyncio.run(main())


# 소켓 프로그래밍 비동기와 멀티프로세스