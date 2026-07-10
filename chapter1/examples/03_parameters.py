"""
Chapter 1-3: 주요 파라미터 이해

API 호출에서 자주 조절하는 파라미터를 직접 비교합니다.
- max_tokens: 최대 출력 토큰 수
- temperature: 응답의 창의성/무작위성 조절 (0.0 ~ 1.0)

주의: top_p, top_k도 샘플링 관련 파라미터이지만, 처음에는 max_tokens와
temperature만 확실히 이해해도 충분합니다.
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()


def call_claude(prompt: str, temperature: float = 1.0, max_tokens: int = 1024) -> str:
    """같은 호출 코드를 재사용하기 위한 작은 helper 함수입니다."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# --- 실험 1: max_tokens 제한 ---
# max_tokens는 "입력+출력 전체"가 아니라 "모델이 생성할 출력"의 상한입니다.
# 같은 질문이라도 이 값이 작으면 답변이 짧아지거나 중간에 끊길 수 있습니다.
print("=== max_tokens 실험 ===")
print("\n[max_tokens=50]")
print(call_claude("Python의 장점 5가지를 설명해주세요.", max_tokens=50))

print("\n[max_tokens=500]")
print(call_claude("Python의 장점 5가지를 설명해주세요.", max_tokens=500))

# --- 실험 2: temperature 비교 ---
# temperature는 정답의 "품질"이나 창의성을 보장하는 스위치가 아니라,
# 다음 토큰을 선택할 때 확률 분포를 얼마나 다양하게 사용할지 조절하는 값입니다.
# temperature=0.0 → 가장 보수적. 같은 질문에 비슷한 답을 기대할 때 사용
# temperature=1.0 → 표현이 더 다양해짐. 아이디어 생성이나 글쓰기 실험에 적합
print("\n=== temperature 실험 ===")

creative_prompt = "'인공지능'을 주제로 한 줄 시를 써주세요."

print("\n[temperature=0.0] 동일 프롬프트 3회 호출 (비슷한 표현이 나오는지 관찰):")
for i in range(3):
    result = call_claude(creative_prompt, temperature=0.0, max_tokens=100)
    print(f"  {i + 1}: {result}")

print("\n[temperature=1.0] 동일 프롬프트 3회 호출 (표현 다양성이 커지는지 관찰):")
for i in range(3):
    result = call_claude(creative_prompt, temperature=1.0, max_tokens=100)
    print(f"  {i + 1}: {result}")
