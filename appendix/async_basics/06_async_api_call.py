"""
부록 A-6: 비동기 실전 — Claude API 비동기 호출

이 수업에서 비동기가 실제로 필요한 대표적인 상황:

    1. MCP 클라이언트가 서버와 통신할 때 (네트워크 I/O)
    2. 여러 LLM 호출을 동시에 보낼 때 (병렬 API 호출)
    3. 웹 서버(Flask/FastAPI)에서 요청을 처리할 때

이 예제에서는 Anthropic의 AsyncAnthropic 클라이언트로
Claude API를 비동기로 호출하는 방법을 보여줍니다.

여기서는 "동시 호출로 빨라진다"는 핵심만 봅니다.
각 질문은 서로 의존하지 않으므로 동시에 보내도 됩니다.
이처럼 독립적인 I/O 작업이 여러 개 있을 때 비동기의 효과가 가장 잘 드러납니다.

실무에 필요한 나머지(타임아웃, 동시 개수 제한, 예외를 값으로 수렴)는
chapter1/examples/10_production_client.py에서 이 코드를 강화한 형태로 다룹니다.
"""

import time
import asyncio
from dotenv import load_dotenv
from anthropic import Anthropic, AsyncAnthropic

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"  # 빠른 응답을 위해 Haiku 사용


# ============================================================
# 1. 동기 방식: 3개 질문을 순차적으로 호출
# ============================================================

def run_sync():
    """동기 클라이언트로 3개 질문을 하나씩 호출"""
    client = Anthropic()
    questions = [
        "Python을 한 문장으로 설명해줘",
        "JavaScript를 한 문장으로 설명해줘",
        "Rust를 한 문장으로 설명해줘",
    ]

    print("[동기 방식] 3개 질문 순차 호출")
    start = time.time()

    for q in questions:
        # create()가 끝날 때까지 다음 질문으로 넘어가지 않습니다.
        response = client.messages.create(
            model=MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": q}],
        )
        print(f"  Q: {q}")
        print(f"  A: {response.content[0].text[:50]}...")
        print()

    elapsed = time.time() - start
    print(f"→ 총 소요시간: {elapsed:.1f}초\n")


# ============================================================
# 2. 비동기 방식: 3개 질문을 동시에 호출
# ============================================================

async def ask(client: AsyncAnthropic, question: str) -> str:
    """비동기로 하나의 질문을 보내고 답변을 받는 함수"""
    response = await client.messages.create(   # 네트워크 응답을 기다리는 동안 다른 호출이 진행됩니다.
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text


async def run_async():
    """비동기 클라이언트로 3개 질문을 동시에 호출"""
    # 비동기 전용 클라이언트입니다.
    # 실무에서는 앱 시작 시 한 번 만들고 재사용하는 편이 좋습니다.
    client = AsyncAnthropic()
    questions = [
        "Python을 한 문장으로 설명해줘",
        "JavaScript를 한 문장으로 설명해줘",
        "Rust를 한 문장으로 설명해줘",
    ]

    print("[비동기 방식] 3개 질문 동시 호출")
    start = time.time()

    # 3개 질문을 동시에 전송합니다.
    # 결과는 gather에 넘긴 질문 순서대로 돌아옵니다.
    answers = await asyncio.gather(
        ask(client, questions[0]),
        ask(client, questions[1]),
        ask(client, questions[2]),
    )

    for q, a in zip(questions, answers):
        print(f"  Q: {q}")
        print(f"  A: {a[:50]}...")
        print()

    elapsed = time.time() - start
    print(f"→ 총 소요시간: {elapsed:.1f}초")
    print("  (대략 가장 오래 걸린 요청 시간에 가까워짐 — 3개 요청이 함께 진행되므로)\n")


# ============================================================
# 실행 비교
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    run_sync()

    print("=" * 60)
    asyncio.run(run_async())

    print("=" * 60)
    print("[핵심 차이점]")
    print("  동기:  Anthropic()         + client.messages.create()")
    print("  비동기: AsyncAnthropic()    + await client.messages.create()")
    print()
    print("[언제 비동기를 쓸까?]")
    print("  - 여러 API를 동시에 호출할 때 (이 예제)")
    print("  - MCP 서버/클라이언트 통신 (chapter4)")
    print("  - 웹 서버에서 여러 요청을 동시 처리할 때")
