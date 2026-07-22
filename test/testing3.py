import asyncio
from anthropic import AsyncAnthropic

# class Bar:
#     async def __enter__(self):
#         print("enter")
#         return self

#     async def __exit__(self, exc_type, exc, tb):
#         print("exit")

# async def main():
# async with Bar() as obj:
#     print("A")
# print("B")


# with open("/test/test.csv", "r", encoding="utf-8") as f_handler:
#     content = f_handler.read()
#     print(content)

# # 자원 흭득 from 운영체제
# file_handler = open("tests/test.csv", "r", encoding="utf-8")

# content = file_handler.read()

# print(content)

# print(file_handler)
# # 자원해제
# file_handler.close()

import asyncio, time

sem = asyncio.Semaphore(3)

async def call_llm(client: AsyncAnthropic, prompt: str, timeout:int=10) -> str:
    try:
        async with sem:
            async with asyncio.timeout(timeout):
                rsp = await client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=200,
                    messages=[{'role':'user', 'content': prompt}],
                )
                return rsp.content[0].text

    except Exception:
        print("타임 아웃")

async def main():
    client = AsyncAnthropic()
    print("프로그램 시작")
    prompt_list = ["한국 수도", "미국 수도", "일본 수도", "영국 수도", "파푸아뉴기니", "노르웨이"]

    start_time = time.time()

    result = await asyncio.gather(
        *[call_llm(client, prompt) for prompt in prompt_list]
        )
    
    for rsp in result:
        print(rsp)
    elapsed_time = time.time() - start_time
    print(elapsed_time)
    print("프로그램 종료")
    

if __name__ == "__main__":
    asyncio.run(main())