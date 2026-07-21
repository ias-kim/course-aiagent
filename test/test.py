import asyncio
from anthropic import AsyncAnthropic, NotFoundError

MODEL = "claude-sonnet-4-6"


async def call_llm(client: AsyncAnthropic, promt:str, max_retry:int=3)->str:


    for retry in range(max_retry + 1) :
        
        try:
            rsp = await client.messages.create(
            model=MODEL,
            max_tokens=200,
            system="답변은 개조식",
            messages = [{"role": "user", "content": promt}]
            )

            return rsp.content[0].text
        
        except NotFoundError as e:
            raise e
        
        except Exception as e: # 예외의 종류를 가지고 구분을 해야함.
            print("예외 발생")

async def main():
    client = AsyncAnthropic(max_retries=3)

    prompt_list = ["시코쿠란?", "도쿠시마 특산물?", "고치 특산물?"]
    
    result = await asyncio.gather(
        *[call_llm(client, prompt) for prompt in prompt_list] # 언패킹 여러개의 개별 인자
        )
    for rsp in result:
        print(rsp)
        print()
    
    print("프로그램 종료")

if __name__ == "__main__":
    asyncio.run(main())