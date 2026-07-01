"""
Chapter 1-3: 주요 파라미터 이해

API 호출에서 자주 조절하는 파라미터를 직접 비교합니다.
- max_tokens: 최대 출력 토큰 수
- temperature: 응답의 창의성/무작위성 조절 (0.0 ~ 1.0)
- top_p, top_k: 토큰 샘플링 방식
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()


def call_claude(prompt: str, temperature: float = 1.0, max_tokens: int = 1024) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# --- 실험 1: max_tokens 제한 ---
# 같은 질문이라도 출력 토큰 상한이 작으면 답변이 짧거나 중간에 끊길 수 있습니다.
print("=== max_tokens 실험 ===")
print("\n[max_tokens=50]")
print(call_claude("Python의 장점 5가지를 설명해주세요.", max_tokens=50))

print("\n[max_tokens=500]")
print(call_claude("Python의 장점 5가지를 설명해주세요.", max_tokens=500))

# --- 실험 2: temperature 비교 ---
# temperature=0.0 → 가장 보수적인 설정. 같은 질문에 비슷한 답을 기대할 때 사용
# temperature=1.0 → 표현이 더 다양해짐. 아이디어 생성이나 글쓰기 실험에 적합
print("\n=== temperature 실험 ===")

creative_prompt = "'인공지능'을 주제로 한 줄 시를 써주세요."

print("\n[temperature=0.0] 동일 프롬프트 3회 호출:")
for i in range(3):
    result = call_claude(creative_prompt, temperature=0.0, max_tokens=100)
    print(f"  {i + 1}: {result}")

print("\n[temperature=1.0] 동일 프롬프트 3회 호출:")
for i in range(3):
    result = call_claude(creative_prompt, temperature=1.0, max_tokens=100)
    print(f"  {i + 1}: {result}")
