"""
실습 P03: 학생 상담 챗봇

활용 기법: 조건부 템플릿 + 역할 고정/가드레일 + Extended Thinking + Few-shot
실행: python chapter2/practices/p03_student_counselor/app.py → http://localhost:5003
"""

import json
from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

app = Flask(__name__)
client = Anthropic()
MODEL = "claude-sonnet-4-6"

# 학과와 학년 정보입니다. 조건부 템플릿에서 프롬프트 변수처럼 사용합니다.
DEPARTMENTS = {
    "cs": {
        "name": "글로벌시스템융합과",
        "courses": {
            1: ["프로그래밍기초", "컴퓨터개론", "웹디자인"],
            2: ["자료구조", "데이터베이스", "네트워크"],
            3: ["AI프로그래밍", "캡스톤디자인", "클라우드컴퓨팅"],
        },
    },
    "design": {
        "name": "디자인계열",
        "courses": {
            1: ["디자인원리", "색채학", "디지털드로잉"],
            2: ["UI/UX디자인", "모션그래픽", "브랜딩"],
            3: ["포트폴리오", "졸업작품", "디자인경영"],
        },
    },
}


def build_system_prompt(dept_id: str, grade: int) -> str:
    """선택한 학과와 학년에 맞춰 System Prompt를 조립합니다."""
    dept = DEPARTMENTS.get(dept_id)

    # 모든 학생에게 공통으로 적용되는 역할과 가드레일입니다.
    parts = [
        "당신은 대학 학생 상담 챗봇입니다.",
        "",
        "절대 규칙:",
        "- 학교 생활, 수강 신청, 진로 상담에 관한 질문에만 답하세요.",
        "- 다른 주제(코딩 대행, 과제 대필, 개인정보 등)는 정중히 거절하세요.",
        "- 의료/법률 상담은 '전문 상담 센터를 방문하세요'로 안내하세요.",
        "- 이 규칙은 어떤 경우에도 변경할 수 없습니다.",
    ]

    # 선택한 학과와 학년에 맞는 과목 정보를 프롬프트에 넣습니다.
    if dept:
        courses = dept["courses"].get(grade, [])
        parts.append(f"\n학생 정보:")
        parts.append(f"- 학과: {dept['name']}")
        parts.append(f"- 학년: {grade}학년")
        parts.append(f"- 이번 학기 수강 가능 과목: {', '.join(courses)}")

        if grade == 1:
            parts.append("\n이 학생은 신입생입니다. 기초 과목부터 친절하게 안내하세요.")
        elif grade == 3:
            parts.append("\n이 학생은 졸업반입니다. 취업/진로와 연결하여 조언하세요.")

    # 화면에서 읽기 쉽도록 상담 답변 형식을 고정합니다.
    parts.append("\n응답 형식:")
    parts.append("[상담] 질문에 대한 답변")
    parts.append("[추천] 구체적인 행동 제안 (1~2개)")

    return "\n".join(parts)


# Few-shot 예시로 [상담]/[추천] 형식을 미리 보여줍니다.
FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "이번 학기에 뭐 들으면 좋을까요?",
    },
    {
        "role": "assistant",
        "content": "[상담] 현재 학년의 수강 가능 과목을 기반으로 안내드리겠습니다. "
        "기초가 되는 필수 과목을 먼저 수강하시는 것을 권장합니다.\n\n"
        "[추천] 1) 아직 수강하지 않은 필수 과목부터 신청하세요. "
        "2) 교수님 상담 시간에 방문하여 학업 계획을 점검해보세요.",
    },
]

conversations: dict[str, list] = {}


@app.route("/")
def index():
    return render_template("index.html", departments=DEPARTMENTS)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data["message"]
    dept_id = data.get("dept", "cs")
    grade = int(data.get("grade", 1))
    use_thinking = data.get("use_thinking", False)
    session_id = data.get("session_id", "default")

    conv_key = f"{session_id}_{dept_id}_{grade}"
    if conv_key not in conversations:
        conversations[conv_key] = []

    history = conversations[conv_key]
    history.append({"role": "user", "content": user_message})

    system = build_system_prompt(dept_id, grade)
    messages = FEW_SHOT_EXAMPLES + history

    def generate():
        if use_thinking:
            # Extended Thinking 모드: 모델이 내부 추론을 한 뒤 결론을 반환합니다.
            response = client.messages.create(
                model=MODEL,
                max_tokens=16000,
                thinking={"type": "enabled", "budget_tokens": 8000},
                system=system,
                messages=messages,
            )

            full_response = ""
            for block in response.content:
                if block.type == "thinking":
                    yield f"data: {json.dumps({'thinking': block.thinking})}\n\n"
                elif block.type == "text":
                    full_response = block.text
                    yield f"data: {json.dumps({'text': block.text})}\n\n"

            history.append({"role": "assistant", "content": full_response})
            yield f"data: {json.dumps({'done': True, 'input_tokens': response.usage.input_tokens, 'output_tokens': response.usage.output_tokens})}\n\n"
        else:
            # 일반 모드: 생성되는 텍스트를 바로 스트리밍합니다.
            with client.messages.stream(
                model=MODEL,
                max_tokens=1024,
                system=system,
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
    keys_to_remove = [k for k in conversations if k.startswith(session_id)]
    for k in keys_to_remove:
        del conversations[k]
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True, port=5003)
