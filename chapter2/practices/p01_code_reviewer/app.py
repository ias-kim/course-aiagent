"""
실습 P01: AI 코드 리뷰어

활용 기법: Few-shot + 구조 지정 CoT + 가드레일
실행: python chapter2/practices/p01_code_reviewer/app.py → http://localhost:5004
"""

import json
from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

app = Flask(__name__)
client = Anthropic()
MODEL = "claude-sonnet-4-20250514"

# 구조 지정 CoT + 가드레일을 포함한 System Prompt
SYSTEM_PROMPT = """당신은 시니어 Python 코드 리뷰어입니다.

리뷰 규칙:
- 코드가 아닌 입력이 들어오면 "코드를 입력해주세요. 일반 텍스트는 리뷰할 수 없습니다."라고만 답하세요.
- 리뷰는 반드시 아래 구조로 작성하세요:

[분석] 코드가 하는 일을 1~2문장으로 요약
[문제점] 버그, 성능, 가독성 이슈를 항목별로 나열 (없으면 "없음")
[개선안] 구체적인 수정 코드와 설명
[점수] 10점 만점 (정수)"""

# Few-shot: 리뷰 형식을 예시로 고정
FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": """def add(a, b):
    return a + b

result = add("1", 2)
print(result)""",
    },
    {
        "role": "assistant",
        "content": """[분석] 두 값을 더하는 함수입니다.

[문제점]
- 타입 안전성: 문자열 "1"과 정수 2를 더하면 TypeError 발생
- 타입 힌트 없음: 함수 파라미터의 기대 타입이 불명확

[개선안]
```python
def add(a: int | float, b: int | float) -> int | float:
    return a + b

result = add(1, 2)  # 문자열 대신 정수 사용
print(result)
```

[점수] 4""",
    },
]

conversations: dict[str, list] = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data["message"]
    session_id = data.get("session_id", "default")

    if session_id not in conversations:
        conversations[session_id] = []

    history = conversations[session_id]
    history.append({"role": "user", "content": user_message})

    # Few-shot 예시를 대화 앞에 붙여서 형식 유도
    messages = FEW_SHOT_EXAMPLES + history

    def generate():
        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            full_response = ""
            for text in stream.text_stream:
                full_response += text
                yield f"data: {json.dumps({'text': text})}\n\n"

            history.append({"role": "assistant", "content": full_response})
            usage = stream.get_final_message().usage
            yield f"data: {json.dumps({'done': True, 'input_tokens': usage.input_tokens, 'output_tokens': usage.output_tokens})}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream")


@app.route("/reset", methods=["POST"])
def reset():
    session_id = request.json.get("session_id", "default")
    conversations.pop(session_id, None)
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True, port=5004)
