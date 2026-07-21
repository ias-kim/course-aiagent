import asyncio

async def call_llm(promt:str)->str:
    print(f"prompt: {promt}")
    await asyncio.sleep(2)
    return f"end prompt: {promt}"

async def main():
    print("hello world")
    result = await call_llm("한국의 수도는?")
    print(result)

    print("프로그램 종료")

if __name__ == "__main__":
    asyncio.run(main())