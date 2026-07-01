"""
Chapter 1-8: 구조화된 출력 (Structured Output)

LLM의 기본 응답은 사람이 읽기 좋은 자연어입니다.
하지만 Agent 코드는 응답에서 값을 꺼내 조건문, 저장, 도구 호출에 사용해야 합니다.
그래서 JSON처럼 코드가 읽기 쉬운 형식으로 답하게 만드는 방법을 배웁니다.

왜 중요한가?
- Agent = LLM + 코드. 코드가 응답을 파싱하려면 구조가 필요합니다.
- 자연어 "서울은 12도이고 맑습니다" → 코드에서 온도/날씨 추출이 어려움
- JSON {"temp": 12, "condition": "맑음"} → 바로 활용 가능
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 1부: System Prompt로 JSON 응답 유도하기
# ============================================================
# 핵심은 System Prompt에 원하는 출력 형식을 아주 분명하게 적는 것입니다.
#
#   1) 원하는 JSON 스키마를 예시로 보여준다
#   2) "반드시 JSON만 출력하라"고 명시한다
#   3) 추가 설명 없이 JSON만 반환하도록 제한한다

print("=" * 60)
print("1부: System Prompt로 JSON 응답 유도")
print("=" * 60)

# --- 예시 1: 단순 정보 추출 ---
print("\n--- 예시 1: 텍스트에서 정보 추출 ---")

response = client.messages.create(
    model=MODEL,
    max_tokens=256,
    system="""당신은 텍스트에서 정보를 추출하는 AI입니다.
사용자가 텍스트를 주면, 아래 JSON 형식으로만 응답하세요.
JSON 외에 다른 텍스트는 절대 포함하지 마세요.

출력 형식:
{"name": "이름", "age": 숫자, "job": "직업"}
""",
    messages=[
        {"role": "user", "content": "김민수는 28살 소프트웨어 엔지니어입니다."}
    ],
)

raw_text = response.content[0].text
print(f"LLM 원본 응답: {raw_text}")

# 문자열로 받은 JSON을 Python 객체로 파싱합니다.
data = json.loads(raw_text)
print(f"파싱 결과: 이름={data['name']}, 나이={data['age']}, 직업={data['job']}")
print(f"타입 확인: name={type(data['name']).__name__}, age={type(data['age']).__name__}")


# --- 예시 2: 분석 결과를 구조화 ---
print("\n--- 예시 2: 감성 분석 결과 구조화 ---")

reviews = [
    "이 제품 정말 최고예요! 배송도 빠르고 품질도 좋습니다.",
    "배송은 빨랐는데 제품 품질이 기대에 못 미쳐요.",
    "가격 대비 그냥 그래요. 보통입니다.",
]

response = client.messages.create(
    model=MODEL,
    max_tokens=512,
    system="""당신은 리뷰 감성 분석기입니다.
사용자가 리뷰 목록을 주면, 각 리뷰를 분석하여 아래 JSON 배열 형식으로만 응답하세요.

출력 형식:
[
  {"review_index": 0, "sentiment": "positive|negative|neutral", "confidence": 0.0~1.0, "keywords": ["키워드1", "키워드2"]}
]
""",
    messages=[
        {"role": "user", "content": "\n".join(f"리뷰 {i}: {r}" for i, r in enumerate(reviews))}
    ],
)

raw_text = response.content[0].text
print(f"LLM 원본 응답:\n{raw_text}\n")

results = json.loads(raw_text)
for item in results:
    print(f"  리뷰 {item['review_index']}: {item['sentiment']} (신뢰도: {item['confidence']}) - {item['keywords']}")


# ============================================================
# 2부: JSON 파싱 실패 처리와 재시도
# ============================================================
# LLM이 항상 완벽한 JSON만 반환한다고 가정하면 위험합니다.
# Agent 코드는 파싱 실패에 대비해야 안정적으로 동작합니다.
#
#   실패 원인 예시:
#   - JSON 앞뒤에 ```json ... ``` 마크다운이 붙는 경우
#   - 설명 텍스트가 함께 포함되는 경우
#   - JSON 문법 오류 (trailing comma 등)
print()
print("=" * 60)
print("2부: 안전한 JSON 파싱")
print("=" * 60)


def parse_json_response(text):
    """
    LLM 응답에서 JSON 부분을 최대한 안전하게 추출합니다.

    처리하는 케이스:
    1. 순수 JSON 문자열
    2. ```json ... ``` 마크다운 블록으로 감싸진 경우
    3. JSON 앞뒤에 불필요한 텍스트가 있는 경우
    """
    text = text.strip()

    # 1) 가장 먼저, 응답 전체가 JSON인지 그대로 시도합니다.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) ```json 코드 블록으로 감싼 경우에는 안쪽 내용만 꺼내 봅니다.
    if "```" in text:
        # ```json ... ``` 또는 ``` ... ``` 패턴을 처리합니다.
        lines = text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                json_lines.append(line)
        try:
            return json.loads("\n".join(json_lines))
        except json.JSONDecodeError:
            pass

    # 3) 앞뒤 설명이 섞인 경우 JSON처럼 보이는 구간만 잘라 봅니다.
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

    # 여기까지 왔다면 자동 복구가 어려운 응답입니다.
    raise ValueError(f"JSON 파싱 실패: {text[:100]}...")


# 파싱 함수가 흔한 응답 형태를 처리하는지 확인합니다.
test_cases = [
    '{"name": "테스트"}',                           # 정상 JSON
    '```json\n{"name": "테스트"}\n```',              # 마크다운 블록
    '결과입니다:\n{"name": "테스트"}\n이상입니다.',     # 앞뒤 텍스트
]

for i, test in enumerate(test_cases):
    try:
        result = parse_json_response(test)
        print(f"  테스트 {i + 1}: 성공 → {result}")
    except ValueError as e:
        print(f"  테스트 {i + 1}: 실패 → {e}")


# ============================================================
# 3부: 재시도 패턴 - 파싱 실패 시 LLM에게 다시 요청
# ============================================================
# 파싱이 실패하면 이전 응답을 보여주며 "JSON 형식으로 다시 답해 달라"고 요청합니다.
print()
print("=" * 60)
print("3부: 파싱 실패 시 재시도 패턴")
print("=" * 60)


def get_structured_response(prompt, system_prompt, max_retries=2):
    """
    구조화된 JSON 응답을 받아오되, 파싱 실패 시 피드백을 주고 재시도합니다.
    """
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(max_retries + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        )
        raw_text = response.content[0].text

        try:
            return parse_json_response(raw_text)
        except ValueError:
            if attempt < max_retries:
                print(f"  [파싱 실패] 재시도 {attempt + 1}/{max_retries}")
                # 이전 응답과 수정 요청을 히스토리에 넣어 모델이 무엇을 고칠지 알게 합니다.
                messages.append({"role": "assistant", "content": raw_text})
                messages.append({
                    "role": "user",
                    "content": "응답이 올바른 JSON 형식이 아닙니다. "
                               "설명 없이 순수 JSON만 출력해주세요.",
                })
            else:
                print(f"  [파싱 실패] 최대 재시도 초과")
                return None


# 테스트: 영화 정보 추출
print("\n--- 영화 정보 추출 ---")
result = get_structured_response(
    prompt="영화 '기생충'에 대해 알려줘",
    system_prompt="""영화 정보를 JSON으로만 응답하세요.
형식: {"title": "제목", "director": "감독", "year": 연도, "genre": ["장르1", "장르2"]}""",
)

if result:
    print(f"  제목: {result['title']}")
    print(f"  감독: {result['director']}")
    print(f"  연도: {result['year']}")
    print(f"  장르: {', '.join(result['genre'])}")


# ============================================================
# 정리: 구조화된 출력 핵심 원칙
# ============================================================
print()
print("=" * 60)
print("정리: 구조화된 출력 핵심 원칙")
print("=" * 60)
print("""
1. System Prompt에 출력 형식을 명확히 지정하라
   - JSON 스키마 예시를 제공
   - "JSON만 출력하라"고 명시

2. 파싱 실패에 항상 대비하라
   - json.loads()를 try/except로 감싸기
   - 마크다운 블록, 앞뒤 텍스트 등 전처리

3. 실패 시 LLM에게 피드백하고 재시도하라
   - "JSON이 아니다"라고 알려주면 대부분 수정된 응답을 반환

4. Agent에서의 의미:
   - LLM은 "생각"하고, Agent(코드)는 "행동"한다
   - 구조화된 출력 = LLM의 생각을 Agent가 이해할 수 있는 형태로 변환
   - 이것이 Chapter 4 Tool Use의 기반이 된다
""")
