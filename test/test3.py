import asyncio
import time 


async def make_coffee(menu: str) -> str:
    print(f"{menu} 준비중")
    if menu == "라뗴 2":
        raise Exception("라뗴 2 실패")
    #asyncio.sleep(2) # 코루틴 객체가 만들어진다.
    await asyncio.sleep(2)
    print(f"{menu} 준비완료")
    return f"{menu}"

async def main():
    result = None
    try :
        result = await asyncio.gather(make_coffee("라뗴 1"),
                                      make_coffee("라뗴 2"),
                                      make_coffee("라뗴 3"),
                                      return_exceptions=True) # 예외처리한 값 전체를 가져옴.
    except Exception as e:
        # 비동기는 병렬으로 처리할 시 예외처리를 발생시켜야함.
        # 하나가 실패해도 성공한 다른 값을 가져올 수 있어야 한다.
        print(e)
    
    print(result)
    # task1 = asyncio.create_task(make_coffee("라뗴 1"))
    # task2 = asyncio.create_task(make_coffee("라뗴 2"))
    # task3 = asyncio.create_task(make_coffee("라뗴 3"))
    # #await asyncio.sleep(5) # blocking 잠시 멈추고 뒤쪽에 있는 레디큐를 실행시킴

    # print(await task1) # await의 역할 현재 실행을 멈추고 다른 태스크의 제어권을 전달하는 역할을 한다. 
    # print(await task2)
    # print(await task3)

    print("완료")

if __name__ == "__main__":
    asyncio.run(main())