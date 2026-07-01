"""
실습 P02: 다국어 뉴스 요약 파이프라인

활용 기법: Prompt Chaining + Prompt Template
파이프라인: 원문 → 번역 → 요약 → 키워드 추출 → 감성 분석 (순차 체인)
실행: python chapter2/practices/p02_news_pipeline/app.py → http://localhost:5002
"""

import json
from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

app = Flask(__name__)
client = Anthropic()
MODEL = "claude-sonnet-4-6"


def call_llm(system: str, user_message: str) -> str:
    """파이프라인 각 단계에서 공통으로 사용하는 단일 LLM 호출 함수입니다."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# 파이프라인 단계 정의입니다. 각 단계의 system 문장이 하나의 Prompt Template입니다.
# {language}, {length} 자리에는 화면에서 고른 사용자 옵션이 들어갑니다.
PIPELINE_STEPS = [
    {
        "name": "번역",
        "system": "영어 텍스트를 {language}로 자연스럽게 번역하세요. 번역문만 출력하세요.",
    },
    {
        "name": "요약",
        "system": "텍스트를 {length} 이내로 요약하세요. 핵심 정보만 포함하세요. 요약문만 출력하세요.",
    },
    {
        "name": "키워드 추출",
        "system": "텍스트에서 핵심 키워드 5개를 콤마로 구분하여 나열하세요. 키워드만 출력하세요.",
    },
    {
        "name": "감성 분석",
        "system": "텍스트의 전체 논조를 분석하세요. 반드시 다음 형식으로만 응답하세요: 긍정/부정/중립 — 한 줄 근거",
    },
]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """파이프라인을 실행하고 각 단계의 시작/완료 결과를 SSE로 순서대로 보냅니다."""
    data = request.json
    article = data["article"]
    language = data.get("language", "한국어")
    length = data.get("length", "3문장")

    def generate():
        # 각 단계의 출력이 다음 단계의 입력이 됩니다. 이것이 Prompt Chaining의 핵심입니다.
        current_text = article

        for i, step in enumerate(PIPELINE_STEPS):
            system = step["system"].format(language=language, length=length)

            yield f"data: {json.dumps({'step': i + 1, 'name': step['name'], 'status': 'start'})}\n\n"

            result = call_llm(system, current_text)

            yield f"data: {json.dumps({'step': i + 1, 'name': step['name'], 'status': 'done', 'result': result})}\n\n"

            # 방금 나온 결과를 다음 단계 입력으로 넘겨 체인을 이어갑니다.
            current_text = result

        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, port=5002)
