import asyncio

async def main():
    try:
        # __enter__ -> 타이머 생성 (2초)
        async with asyncio.timeout(2): 
        # 2초가 지난 경우 __exit__가 호출되어 예외 발생됨.
            await asyncio.sleep(3)
            print("hello")

    except TimeoutError:
        print("예외 발생")


if __name__== "__main__":
    asyncio.run(main())