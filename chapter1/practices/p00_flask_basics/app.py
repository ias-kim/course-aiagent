"""
실습 P00: Flask 핵심 입문 (Claude 없이 Flask만)

p01, p02는 Flask 위에 Claude API를 얹은 웹 앱입니다.
이 실습은 그 "밑바탕"인 Flask의 핵심 사용법만 간결하게 익힙니다.
API 키가 필요 없습니다 — 순수 Flask이므로 그대로 실행하면 됩니다.

배우는 것 (뒤 실습들이 실제로 쓰는 최소 집합):
    1. 앱 만들기 + 라우트 + 실행      @app.route, app.run
    2. HTML 페이지 반환               render_template + templates/, static/
    3. HTTP 메서드                    GET / POST (methods=)
    4. 요청 데이터 받기               request.args(쿼리), request.json(JSON 본문)
    5. 응답 형태                      문자열 / dict(자동 JSON) / 상태코드

한 줄 개념:
    브라우저 ──요청(URL/메서드/데이터)──►  라우트 함수  ──반환값──►  브라우저
    Flask는 이 사이의 HTTP 처리를 대신해 줍니다. 우리는 "함수"만 씁니다.

실행:
    1) 처음 한 번, 프로젝트 루트에서 패키지를 설치합니다: pip install -e .
       ModuleNotFoundError: No module named 'flask'가 나오면 이 단계를 확인하세요.
    2) 프로젝트 루트에서 아래 명령을 실행합니다.
       python chapter1/practices/p00_flask_basics/app.py
    3) 터미널에 표시된 http://127.0.0.1:5000 주소를 브라우저에서 엽니다.
    4) 종료할 때는 서버를 실행한 터미널에서 Ctrl+C를 누릅니다.

폴더 역할:
    app.py               Python 서버와 URL별 처리 함수
    templates/index.html 서버가 렌더링할 HTML 템플릿
    static/style.css     브라우저가 별도로 요청하는 CSS 파일
"""

# Flask: 웹 애플리케이션 객체를 만드는 클래스
# render_template: templates/의 HTML을 읽고 값을 채우는 함수
# request: 현재 HTTP 요청의 URL, 쿼리, JSON 본문 등을 담은 객체
from flask import Flask, render_template, request

# ① 앱 만들기 — __name__은 Flask가 templates/ , static/ 폴더 위치를 찾는 기준입니다.
app = Flask(__name__)


# ============================================================
# 1. 라우트의 기본 — URL과 함수를 연결한다
# ============================================================
# @app.route("경로")를 함수 위에 붙이면, 그 URL로 들어온 요청을 이 함수가 처리합니다.
# 함수의 "반환값"이 곧 브라우저로 가는 응답입니다.
# 데코레이터 바로 아래 함수가 실제 처리 함수라는 점을 한 묶음으로 읽으세요.

@app.route("/")
def index():
    """메인 페이지. templates/index.html을 렌더링해 반환합니다."""
    # render_template: templates/ 폴더의 HTML 파일을 찾아 렌더링합니다.
    # 키워드 인자는 HTML 안으로 넘길 값입니다 (name → {{ name }} 자리에 들어감).
    return render_template("index.html", name="AI Agent 수강생")


@app.route("/hello")
def hello():
    """문자열을 그대로 반환하면 Flask가 HTML 응답으로 보냅니다."""
    return "안녕하세요! 이건 문자열을 그대로 돌려주는 가장 단순한 라우트입니다."


# ============================================================
# 2. 동적 URL — 경로의 일부를 변수로 받는다
# ============================================================
# <name>처럼 꺾쇠로 감싸면 URL의 그 부분이 함수 인자로 들어옵니다.
#   /greet/철수  →  name = "철수"

@app.route("/greet/<name>")
def greet(name):
    """URL 경로에서 받은 값을 그대로 사용하는 예시입니다."""
    return f"{name}님, 반갑습니다!"


# ============================================================
# 3. 쿼리 파라미터 받기 — request.args
# ============================================================
# URL 뒤 ?a=3&b=5 형태의 값은 request.args로 읽습니다.
#   GET /add?a=3&b=5  →  {"a":3, "b":5, "합":8}

@app.route("/add")
def add():
    """쿼리 파라미터 두 개를 더해 JSON으로 돌려줍니다."""
    # type=int를 주면 문자열을 정수로 바꿔 줍니다. 변환 실패/누락 시 None.
    a = request.args.get("a", type=int)
    b = request.args.get("b", type=int)

    # 입력 검증: 필요한 값이 없으면 400(잘못된 요청) 상태코드와 함께 오류를 알립니다.
    if a is None or b is None:
        return {"error": "정수 쿼리 파라미터 a, b가 모두 필요합니다"}, 400

    # dict를 반환하면 Flask가 자동으로 JSON 응답으로 바꿔 줍니다.
    return {"a": a, "b": b, "합": a + b}


# ============================================================
# 4. POST + JSON 본문 받기 — request.json
# ============================================================
# methods=["POST"]로 POST 요청을 받게 하고, 본문의 JSON은 request.get_json()으로 읽습니다.
# p01/p02가 브라우저의 fetch로 데이터를 보낼 때 쓰는 바로 그 방식입니다.

@app.route("/echo", methods=["POST"])
def echo():
    """JSON 본문 {"text": "..."}을 받아 되돌려줍니다."""
    # silent=True: 본문이 JSON이 아니어도 예외 대신 None을 반환 → 500 대신 우리가 처리.
    data = request.get_json(silent=True) or {}
    text = data.get("text")

    if not isinstance(text, str) or not text.strip():
        return {"error": "text 필드(문자열)가 필요합니다"}, 400

    # JSON 키를 영어로 쓰면 JavaScript에서 data.echo, data.length처럼 접근하기 쉽습니다.
    return {"echo": text, "length": len(text)}


# ============================================================
# 앱 실행
# ============================================================
# debug=True: 코드를 저장하면 서버가 자동 재시작되고, 오류 페이지가 자세히 나옵니다.
#             (개발 중에만 켜세요. 실제 배포에서는 끕니다.)
# 이 조건문 덕분에 이 파일을 직접 실행할 때만 개발 서버가 시작됩니다.
# 다른 Python 파일이 app을 import할 때는 서버가 자동으로 시작되지 않습니다.
if __name__ == "__main__":
    app.run(debug=True, port=5000)


# ============================================================
# REST API 명세 (직접 호출해 보며 확인하세요)
# ============================================================
#
# 1. GET /
#    templates/index.html 페이지를 반환합니다.  (브라우저로 접속)
#
# 2. GET /hello
#    문자열 응답.  예: "안녕하세요! ..."
#
# 3. GET /greet/<name>
#    경로 변수를 사용한 인사.  예: GET /greet/철수 → "철수님, 반갑습니다!"
#
# 4. GET /add?a=<정수>&b=<정수>
#    쿼리 파라미터 합산.
#    성공: {"a":3, "b":5, "합":8}
#    실패: {"error": "..."}  (HTTP 400)
#
# 5. POST /echo
#    Request  (application/json):  {"text": "안녕"}
#    성공: {"echo":"안녕", "length":2}
#    실패: {"error":"..."}  (HTTP 400)
#
# ─────────────────────────────────────────────────────────────
# 다음 단계:
#   여기서 배운 라우트·요청·JSON 응답 위에 Claude API 호출만 얹으면
#   p01(페르소나 챗봇), p02(모델 플레이그라운드)가 됩니다.
