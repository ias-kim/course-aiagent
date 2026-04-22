"""
비동기 처리 애니메이션 GIF 생성기 (고해상도)

01_sync_vs_async.py의 비동기 부분을
Event Loop, Task Queue, Task 상태 + 소스 코드를 함께 시각화합니다.

실행 방법:
    python appendix/async_basics/generate_async_animation.py

출력:
    appendix/async_basics/async_event_loop.gif
"""

from PIL import Image, ImageDraw, ImageFont

# 고해상도 (2x)
SCALE = 2
WIDTH = 1100 * SCALE
HEIGHT = 580 * SCALE
BG_COLOR = (25, 25, 35)

TASK_COLORS = {
    "아메리카노": (255, 150, 50),
    "라떼": (80, 190, 255),
    "카푸치노": (180, 130, 255),
}
QUEUE_COLOR = (50, 52, 65)
LOOP_COLOR = (80, 200, 120)
TEXT_COLOR = (235, 235, 240)
DIM_TEXT = (130, 130, 150)
HIGHLIGHT = (255, 220, 80)
CODE_BG = (18, 20, 28)
CODE_HIGHLIGHT_BG = (50, 50, 15)
LINE_NUM_COLOR = (70, 75, 100)
CODE_KEYWORD = (200, 120, 255)    # async, await, def, return
CODE_STRING = (130, 220, 130)     # 문자열
CODE_FUNC = (100, 200, 255)       # 함수명
CODE_NORMAL = (210, 210, 220)
CODE_DIM = (120, 120, 140)

# 폰트
FONT_CANDIDATES = [
    "malgun.ttf", "NanumGothic.ttf", "gulim.ttc", "arial.ttf",
]
FONT_CANDIDATES_BOLD = [
    "malgunbd.ttf", "malgungbd.ttf", "arialbd.ttf", "arial.ttf",
]


def load_font(size, bold=False):
    candidates = FONT_CANDIDATES_BOLD if bold else FONT_CANDIDATES
    for name in candidates:
        try:
            return ImageFont.truetype(name, size * SCALE)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


font_title = load_font(20, bold=True)
font_label = load_font(13, bold=True)
font_body = load_font(12)
font_small = load_font(11)
font_time = load_font(24, bold=True)
font_code = load_font(13)
font_code_bold = load_font(13, bold=True)
font_code_small = load_font(11)

S = SCALE  # 축약


# ============================================================
# 소스 코드 (구문 강조용 토큰)
# ============================================================
# 각 줄은 (token, color) 튜플의 리스트 + 태스크 태그

CODE_LINES = [
    # line 0
    ([("async def ", CODE_KEYWORD), ("order_coffee_async", CODE_FUNC), ("(name):", CODE_NORMAL)], None),
    # line 1
    ([("    print", CODE_NORMAL), ('(f"', CODE_NORMAL), ("{name} 주문 접수", CODE_STRING), ('")', CODE_NORMAL)], None),
    # line 2
    ([("    await ", CODE_KEYWORD), ("asyncio.sleep(2)", CODE_NORMAL)], None),
    # line 3
    ([("    print", CODE_NORMAL), ('(f"', CODE_NORMAL), ("{name} 완성!", CODE_STRING), ('")', CODE_NORMAL)], None),
    # line 4
    ([("    return ", CODE_KEYWORD), ('f"', CODE_NORMAL), ("{name} 완성", CODE_STRING), ('"', CODE_NORMAL)], None),
    # line 5
    ([], None),
    # line 6
    ([("async def ", CODE_KEYWORD), ("run_async", CODE_FUNC), ("():", CODE_NORMAL)], None),
    # line 7
    ([("    results = ", CODE_NORMAL), ("await ", CODE_KEYWORD), ("asyncio.gather(", CODE_NORMAL)], None),
    # line 8
    ([("        order_coffee_async", CODE_FUNC), ('("아메리카노"),', CODE_STRING)], "아메리카노"),
    # line 9
    ([("        order_coffee_async", CODE_FUNC), ('("라떼"),', CODE_STRING)], "라떼"),
    # line 10
    ([("        order_coffee_async", CODE_FUNC), ('("카푸치노"),', CODE_STRING)], "카푸치노"),
    # line 11
    ([("    )", CODE_NORMAL)], None),
]


# ============================================================
# 프레임 데이터
# ============================================================

FRAMES = [
    {
        "time": "T=0.0s",
        "loop_action": "asyncio.gather() 호출",
        "queue": ["아메리카노", "라떼", "카푸치노"],
        "tasks": {
            "아메리카노": "PENDING",
            "라떼": "PENDING",
            "카푸치노": "PENDING",
        },
        "desc": "gather()가 3개 코루틴을 Task로 감싸서 큐에 등록",
        "running": None,
        "code_highlight": [7, 8, 9, 10, 11],
    },
    {
        "time": "T=0.0s",
        "loop_action": "큐에서 아메리카노 꺼냄",
        "queue": ["라떼", "카푸치노"],
        "tasks": {
            "아메리카노": "RUNNING",
            "라떼": "PENDING",
            "카푸치노": "PENDING",
        },
        "desc": "아메리카노: print('주문 접수') 실행 중",
        "running": "아메리카노",
        "code_highlight": [1],
    },
    {
        "time": "T=0.0s",
        "loop_action": "await sleep → 양보 → 라떼 꺼냄",
        "queue": ["카푸치노"],
        "tasks": {
            "아메리카노": "SUSPENDED",
            "라떼": "RUNNING",
            "카푸치노": "PENDING",
        },
        "desc": "아메리카노 await sleep(2) → 양보 → 라떼 시작",
        "running": "라떼",
        "code_highlight": [2],
    },
    {
        "time": "T=0.0s",
        "loop_action": "await sleep → 양보 → 카푸치노 꺼냄",
        "queue": [],
        "tasks": {
            "아메리카노": "SUSPENDED",
            "라떼": "SUSPENDED",
            "카푸치노": "RUNNING",
        },
        "desc": "라떼도 await sleep(2) → 양보 → 카푸치노 시작",
        "running": "카푸치노",
        "code_highlight": [2],
    },
    {
        "time": "T=0.0s",
        "loop_action": "모두 await 중 → I/O 대기",
        "queue": [],
        "tasks": {
            "아메리카노": "SUSPENDED",
            "라떼": "SUSPENDED",
            "카푸치노": "SUSPENDED",
        },
        "desc": "3개 모두 sleep 중 → 이벤트 루프가 OS에 I/O 완료 대기 요청",
        "running": None,
        "code_highlight": [2],
    },
    {
        "time": "T=2.0s",
        "loop_action": "sleep 완료! → 아메리카노 재개",
        "queue": ["라떼", "카푸치노"],
        "tasks": {
            "아메리카노": "RUNNING",
            "라떼": "READY",
            "카푸치노": "READY",
        },
        "desc": "2초 경과! sleep 완료 → 아메리카노부터 재개 (FIFO)",
        "running": "아메리카노",
        "code_highlight": [3, 4],
    },
    {
        "time": "T=2.0s",
        "loop_action": "아메리카노 완료 → 라떼 재개",
        "queue": ["카푸치노"],
        "tasks": {
            "아메리카노": "DONE",
            "라떼": "RUNNING",
            "카푸치노": "READY",
        },
        "desc": "아메리카노 print('완성!') → return → 라떼 재개",
        "running": "라떼",
        "code_highlight": [3, 4],
    },
    {
        "time": "T=2.0s",
        "loop_action": "라떼 완료 → 카푸치노 재개",
        "queue": [],
        "tasks": {
            "아메리카노": "DONE",
            "라떼": "DONE",
            "카푸치노": "RUNNING",
        },
        "desc": "라떼 완료 → 카푸치노 재개",
        "running": "카푸치노",
        "code_highlight": [3, 4],
    },
    {
        "time": "T=2.0s",
        "loop_action": "모든 Task 완료!",
        "queue": [],
        "tasks": {
            "아메리카노": "DONE",
            "라떼": "DONE",
            "카푸치노": "DONE",
        },
        "desc": "총 소요시간: 약 2초 (3잔 동시 제조!)",
        "running": None,
        "code_highlight": [11],
    },
]

STATE_COLORS = {
    "PENDING": (90, 90, 110),
    "RUNNING": (60, 185, 100),
    "SUSPENDED": (240, 170, 40),
    "READY": (80, 180, 245),
    "DONE": (70, 70, 90),
}

STATE_LABELS = {
    "PENDING": "대기",
    "RUNNING": "실행 중",
    "SUSPENDED": "await 중",
    "READY": "재개 대기",
    "DONE": "완료",
}

CODE_PANEL_W = 420 * S
RIGHT_X = CODE_PANEL_W + 20 * S


def draw_code_panel(draw, frame_data):
    """좌측 코드 패널"""
    y0 = 48 * S

    # 배경
    draw.rectangle([(0, y0), (CODE_PANEL_W, HEIGHT)], fill=CODE_BG)

    # 헤더
    draw.rectangle([(0, y0), (CODE_PANEL_W, y0 + 32 * S)], fill=(30, 32, 42))
    draw.text((14 * S, y0 + 8 * S), "01_sync_vs_async.py  (비동기 부분)", font=font_label, fill=(160, 160, 180))

    # 구분선
    draw.line([(CODE_PANEL_W, y0), (CODE_PANEL_W, HEIGHT)], fill=(55, 55, 75), width=2 * S)

    highlighted = set(frame_data.get("code_highlight", []))
    line_h = 32 * S
    code_y = y0 + 40 * S

    for i, (tokens, tag) in enumerate(CODE_LINES):
        ly = code_y + i * line_h
        is_hl = i in highlighted

        # 하이라이트 배경
        if is_hl:
            draw.rectangle([(0, ly), (CODE_PANEL_W - 2 * S, ly + line_h)], fill=CODE_HIGHLIGHT_BG)
            # 실행 화살표
            draw.text((4 * S, ly + 7 * S), ">", font=font_code_bold, fill=HIGHLIGHT)

        # 줄 번호
        line_num = str(i + 1).rjust(2)
        num_color = HIGHLIGHT if is_hl else LINE_NUM_COLOR
        draw.text((18 * S, ly + 7 * S), line_num, font=font_code, fill=num_color)

        # 구문 강조 토큰 렌더링
        tx = 46 * S
        for text, color in tokens:
            if is_hl:
                # 하이라이트 시 더 밝게
                bright = tuple(min(255, c + 40) for c in color)
                draw.text((tx, ly + 7 * S), text, font=font_code_bold, fill=bright)
            else:
                draw.text((tx, ly + 7 * S), text, font=font_code, fill=color)
            tx += draw.textlength(text, font=font_code)

        # 태스크 컬러 도트
        if tag and tag in TASK_COLORS:
            tc = TASK_COLORS[tag]
            dot_x = CODE_PANEL_W - 22 * S
            dot_r = 6 * S
            draw.ellipse(
                [(dot_x, ly + 10 * S), (dot_x + dot_r * 2, ly + 10 * S + dot_r * 2)],
                fill=tc,
            )


def draw_frame(frame_data, frame_idx):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ── 타이틀 바 ──
    draw.rectangle([(0, 0), (WIDTH, 47 * S)], fill=(35, 37, 48))
    draw.text((18 * S, 12 * S), "asyncio Event Loop 시각화", font=font_title, fill=TEXT_COLOR)
    # 시간 표시
    time_text = frame_data["time"]
    tw = draw.textlength(time_text, font=font_time)
    draw.text((WIDTH - tw - 20 * S, 10 * S), time_text, font=font_time, fill=HIGHLIGHT)

    # ── 좌측 코드 패널 ──
    draw_code_panel(draw, frame_data)

    # ── 우측 시각화 ──
    rx = RIGHT_X
    rw = WIDTH - rx - 18 * S

    # Event Loop 바
    ely = 58 * S
    draw.rounded_rectangle(
        [(rx, ely), (WIDTH - 18 * S, ely + 38 * S)],
        radius=8 * S, fill=(45, 47, 60), outline=LOOP_COLOR, width=2 * S,
    )
    draw.text((rx + 12 * S, ely + 9 * S), "Event Loop:", font=font_label, fill=LOOP_COLOR)
    draw.text((rx + 135 * S, ely + 10 * S), frame_data["loop_action"], font=font_body, fill=TEXT_COLOR)

    # Task Queue
    qy = 106 * S
    draw.text((rx, qy), "Task Queue (FIFO)", font=font_label, fill=DIM_TEXT)
    draw.rounded_rectangle(
        [(rx, qy + 22 * S), (WIDTH - 18 * S, qy + 62 * S)],
        radius=8 * S, fill=QUEUE_COLOR, outline=(70, 72, 85), width=S,
    )

    if frame_data["queue"]:
        item_w = min(145 * S, (rw - 30 * S) // len(frame_data["queue"]))
        for i, item in enumerate(frame_data["queue"]):
            ix = rx + 12 * S + i * (item_w + 8 * S)
            color = TASK_COLORS.get(item, (150, 150, 150))
            draw.rounded_rectangle(
                [(ix, qy + 28 * S), (ix + item_w, qy + 56 * S)],
                radius=6 * S, fill=color,
            )
            itw = draw.textlength(item, font=font_body)
            draw.text((ix + (item_w - itw) / 2, qy + 33 * S), item, font=font_body, fill=(25, 25, 35))
    else:
        draw.text((rx + rw // 2 - 30 * S, qy + 34 * S), "(비어 있음)", font=font_small, fill=DIM_TEXT)

    # Tasks 카드
    ty = 180 * S
    draw.text((rx, ty), "Tasks", font=font_label, fill=DIM_TEXT)

    tasks = frame_data["tasks"]
    card_gap = 12 * S
    card_w = (rw - card_gap * 2) // 3
    card_h = 215 * S

    for i, (name, state) in enumerate(tasks.items()):
        cx = rx + i * (card_w + card_gap)
        cy = ty + 24 * S
        color = TASK_COLORS.get(name, (150, 150, 150))
        state_color = STATE_COLORS.get(state, (100, 100, 100))
        is_running = frame_data.get("running") == name

        # 카드 배경
        outline_c = HIGHLIGHT if is_running else (60, 62, 78)
        outline_w = 3 * S if is_running else S
        draw.rounded_rectangle(
            [(cx, cy), (cx + card_w, cy + card_h)],
            radius=12 * S, fill=(40, 42, 55), outline=outline_c, width=outline_w,
        )

        # 이름 바
        draw.rounded_rectangle(
            [(cx + 8 * S, cy + 8 * S), (cx + card_w - 8 * S, cy + 40 * S)],
            radius=6 * S, fill=color,
        )
        ntw = draw.textlength(name, font=font_label)
        draw.text(
            (cx + (card_w - ntw) / 2, cy + 14 * S),
            name, font=font_label, fill=(25, 25, 35),
        )

        # 상태 뱃지
        state_label = STATE_LABELS.get(state, state)
        badge_w = 100 * S
        badge_x = cx + (card_w - badge_w) // 2
        draw.rounded_rectangle(
            [(badge_x, cy + 52 * S), (badge_x + badge_w, cy + 78 * S)],
            radius=14 * S, fill=state_color,
        )
        slw = draw.textlength(state_label, font=font_body)
        draw.text(
            (badge_x + (badge_w - slw) / 2, cy + 56 * S),
            state_label, font=font_body, fill=(20, 20, 30),
        )

        # 영문 상태
        elw = draw.textlength(state, font=font_small)
        draw.text(
            (cx + (card_w - elw) / 2, cy + 88 * S),
            state, font=font_small, fill=DIM_TEXT,
        )

        # 코드 힌트 박스
        draw.rounded_rectangle(
            [(cx + 8 * S, cy + 108 * S), (cx + card_w - 8 * S, cy + 168 * S)],
            radius=6 * S, fill=(28, 28, 38),
        )

        if state == "RUNNING" and frame_data["time"] == "T=2.0s":
            hints = ['print(f"{name} 완성!")', 'return f"{name} 완성"']
        elif state == "RUNNING":
            hints = ['print(f"{name}', '         주문 접수")']
        elif state == "SUSPENDED":
            hints = ["await", "  asyncio.sleep(2)"]
        elif state == "DONE":
            hints = ['return', f'  f"{name} 완성"']
        elif state == "READY":
            hints = ["sleep 완료", "재개 대기 중"]
        else:
            hints = ["큐에서", "대기 중"]

        for hi, hint in enumerate(hints):
            hcolor = CODE_STRING if state in ("RUNNING", "DONE") else CODE_NORMAL
            if state == "SUSPENDED":
                hcolor = CODE_KEYWORD
            elif state in ("PENDING", "READY"):
                hcolor = DIM_TEXT
            draw.text(
                (cx + 16 * S, cy + 116 * S + hi * 20 * S),
                hint, font=font_code_small, fill=hcolor,
            )

        # 실행 표시
        if is_running:
            marker = ">>> 실행 중"
            mw = draw.textlength(marker, font=font_small)
            draw.text(
                (cx + (card_w - mw) / 2, cy + 180 * S),
                marker, font=font_small, fill=HIGHLIGHT,
            )

    # ── 하단 설명 바 ──
    desc_y = HEIGHT - 58 * S
    draw.rectangle([(0, desc_y), (WIDTH, HEIGHT)], fill=(35, 37, 48))
    step_text = f"Step {frame_idx + 1}/{len(FRAMES)}"
    draw.text((18 * S, desc_y + 10 * S), step_text, font=font_label, fill=HIGHLIGHT)
    draw.text((120 * S, desc_y + 11 * S), frame_data["desc"], font=font_body, fill=TEXT_COLOR)
    draw.text(
        (WIDTH - 230 * S, desc_y + 34 * S),
        "Single Thread (MainThread)",
        font=font_small, fill=(90, 90, 110),
    )

    return img


# ============================================================
# GIF 생성
# ============================================================
if __name__ == "__main__":
    frames = []
    for i, frame_data in enumerate(FRAMES):
        img = draw_frame(frame_data, i)
        frames.append(img)

    output_path = "appendix/async_basics/async_event_loop.gif"
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=2500,
        loop=0,
    )
    print(f"GIF 생성 완료: {output_path}")
    print(f"  프레임 수: {len(frames)}")
    print(f"  크기: {WIDTH}x{HEIGHT}")
