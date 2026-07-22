import asyncio
from anthropic import AsyncAnthropic, NotFoundError

MODEL = "claude-sonnet-4-6"


async def call_llm(client: AsyncAnthropic, promt:str, max_retry:int=3)->str:
    # 최대 max_retry+1번 시도. 성공하면 return으로 즉시 빠져나가고,
    # 실패가 계속되면 루프가 그냥 끝나 None을 반환한다 (실패 시 값 미보장 상태).
    for retry in range(max_retry + 1) :

        try:
            rsp = await client.messages.create(
            model=MODEL,
            max_tokens=200,
            system="답변은 개조식",
            messages = [{"role": "user", "content": promt}]
            )

            return rsp.content[0].text

        # 모델 ID가 잘못된 경우처럼 재시도해도 절대 성공할 수 없는 에러는
        # 즉시 위로 다시 던져서 재시도 루프를 낭비하지 않는다.
        except NotFoundError as e:
            raise e

        # 예외의 종류를 가지고 구분을 해야함.
        # 지금은 네트워크 타임아웃/RateLimit처럼 재시도할 가치가 있는 예외와
        # 그렇지 않은 예외를 구분하지 않고 전부 무시(print만)한 뒤 다음 루프로 넘어간다.
        except Exception as e:
            print("예외 발생")

async def main():
    client = AsyncAnthropic(max_retries=3)

    prompt_list = ["시코쿠란?", "도쿠시마 특산물?", "고치 특산물?"]

    # [call_llm(...) for p in prompt_list] → 코루틴 객체 3개짜리 리스트 생성 (아직 미실행)
    # asyncio.gather(*[...]) → 리스트를 개별 인자로 언패킹해 각각을 별도 Task로 스케줄링,
    #                          3개를 동시에 실행하고 전부 끝날 때까지 기다린다.
    result = await asyncio.gather(
        *[call_llm(client, prompt) for prompt in prompt_list]
        )
    for rsp in result:
        print(rsp)
        print()

    print("프로그램 종료")

if __name__ == "__main__":
    # asyncio.run(): 새 이벤트 루프 생성 → main()을 Task로 감싸 실행 완료까지 대기 → 루프 종료(close)
    asyncio.run(main())
