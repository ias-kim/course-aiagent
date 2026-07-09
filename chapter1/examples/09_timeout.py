"""
Chapter 1-9: 타임아웃 실무 접근

외부 API를 시간 제한 없이 기다리는 실무 코드는 없습니다.
하지만 LLM API는 일반 REST API와 달리 "느린 것이 정상"일 수 있습니다.
짧은 타임아웃을 무작정 걸면 장애가 아니라 정상적인 긴 생성까지 끊어 버립니다.

따라서 타임아웃은 한 숫자로 끝나는 설정이 아니라, 어느 층의 시간을 제한할지
나누어 설계해야 합니다:

    1층: SDK/HTTP 레벨   — 연결, 읽기, 쓰기처럼 HTTP 동작이 멈췄는지 감시
    2층: 연산 레벨       — 여러 API 호출을 묶은 전체 작업의 마감 시간(SLA) 관리
    3층: 인프라 레벨     — nginx, 로드밸런서, 플랫폼의 요청 제한

이 파일은 1층(SDK/HTTP 레벨)을 중심으로 살펴보며, 2층과 어떻게 같이 쓰는지도
마지막에 정리합니다.

이 파일에서 볼 4가지:
    1. SDK 타임아웃 설정 — 클라이언트 기본값과 요청별 덮어쓰기
    2. 타임아웃 × 재시도 — "5초 타임아웃"이 실제로는 5초보다 길어지는 이유
    3. 스트리밍과 read 타임아웃 — 긴 생성은 살리고 멈춘 연결은 끊는 방법
    4. 진행 감시(SDK) vs 총량 감시(asyncio.timeout) — 둘을 겹쳐 쓰는 이유
"""

import time

import httpx
from dotenv import load_dotenv
from anthropic import Anthropic, APITimeoutError

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"


# ============================================================
# 1부: SDK 타임아웃 설정
# ============================================================
# anthropic SDK에는 요청당 타임아웃이 내장되어 있습니다(기본 10분).
# 직접 타이머 코드를 만들 필요 없이 클라이언트 설정으로 조정할 수 있습니다.
#
#   클라이언트 전체:  Anthropic(timeout=30.0)
#   특정 요청만:      client.with_options(timeout=5.0).messages.create(...)
#   세분화:           httpx.Timeout(60.0, connect=3.0)
#                     → 연결은 3초 안에 끝나야 함(서버 생사 확인은 빨리)
#                     → 읽기/쓰기 등 나머지 단계는 기본 60초까지 허용
#
# 여기서 주의할 점:
#   timeout=30.0은 "요청 전체를 30초 안에 끝내라"는 벽시계가 아닙니다.
#   SDK 내부의 HTTP 클라이언트(httpx)가 connect/read/write/pool 같은 단계마다
#   적용하는 제한입니다. 전체 작업 마감 시간은 4부의 asyncio.timeout()처럼
#   바깥에서 따로 잡아야 합니다.
#
# with_options(...)란?
#   - 기존 client를 직접 수정하지 않습니다.
#   - timeout, max_retries 같은 옵션만 덮어쓴 "새 클라이언트 뷰"를 반환합니다.
#   - 그래서 이 줄의 설정은 이 요청에만 적용되고, 원본 client 설정은 그대로입니다.
#
# 타임아웃이 실제로 초과되면?
#   - 조용히 실패값을 반환하지 않고 anthropic.APITimeoutError 예외가 발생합니다.
#   - 재시도가 켜져 있으면 재시도를 모두 소진한 뒤 마지막 실패가 예외로 올라옵니다.
#   - 따라서 타임아웃 설정과 try/except 처리는 한 세트로 생각해야 합니다.
print("=" * 60)
print("1부: SDK 타임아웃 설정")
print("=" * 60)

# 일부러 비현실적으로 짧은 0.2초를 걸어 타임아웃을 재현합니다.
# max_retries=0은 SDK 자동 재시도를 끄는 옵션입니다.
# 이렇게 해야 "타임아웃 1회"의 시간을 먼저 관찰하고, 2부의 재시도 케이스와
# 비교할 수 있습니다.
#
# 참고: 실제 소요 시간이 정확히 0.2초로 찍히지 않을 수 있습니다.
# float 타임아웃은 "요청 전체 시간"이 아니라 HTTP 단계(connect/read/write/pool)에
# 각각 적용되는 제한이기 때문입니다. 예를 들어 connect 단계가 제한 안에 통과한 뒤
# read 단계에서 다시 자기 제한 시간을 쓰면, 체감 시간은 0.2초보다 길어집니다.
# 전체 소요 시간을 벽시계처럼 자르는 방법은 4부에서 다룹니다.
print("\n--- 0.2초 타임아웃, 재시도 없음 ---")
start = time.time()
try:
    response = client.with_options(timeout=0.2, max_retries=0).messages.create(
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": "안녕"}],
    )
except APITimeoutError:
    print(f"  APITimeoutError 발생 — 소요 {time.time() - start:.1f}초")
    print("  → 0.2초 안에 응답이 시작될 수 없으므로 항상 실패합니다")


# ============================================================
# 2부: 타임아웃 × 재시도 상호작용
# ============================================================
# max_retries의 동작 절차(SDK가 자동으로 수행):
#   1) 요청 실패 → "재시도할 가치가 있는 실패"인지 분류
#        재시도 O: 연결 실패, 타임아웃, 408/409/429, 500 이상 (일시적일 수 있음)
#        재시도 X: 400(요청 오류), 401(인증), 404(모델 없음) 등 → 즉시 예외
#   2) 지수 백오프 + 지터만큼 대기 (429는 서버의 retry-after 헤더를 존중)
#   3) 같은 요청을 자동으로 다시 전송
#   4) max_retries 소진까지 1~3 반복 → 그래도 실패하면 그때 예외가 올라옴
#   → except에서 잡는 예외는 "재시도가 모두 끝난 뒤의 최종 실패"입니다.
#
# 주의: 타임아웃도 재시도 대상입니다(기본 2회).
# 따라서 사용자가 체감하는 최대 대기 시간은 단순히 timeout 값이 아니라
#
#   timeout × (max_retries + 1) + 백오프 대기
#
# 가 됩니다. 타임아웃을 설계할 때 재시도 횟수를 함께 계산해야 하는 이유입니다.
print()
print("=" * 60)
print("2부: 타임아웃 × 재시도 상호작용")
print("=" * 60)

print("\n--- 같은 0.2초 타임아웃, 기본 재시도(2회) ---")
start = time.time()
try:
    response = client.with_options(timeout=0.2).messages.create(  # max_retries 기본값 2
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": "안녕"}],
    )
except APITimeoutError:
    elapsed = time.time() - start
    print(f"  APITimeoutError 발생 — 소요 {elapsed:.1f}초")
    print("  → 1부(1회)보다 훨씬 오래 걸림: 3회 시도 + 시도 사이 백오프 대기")
    print("  → '타임아웃 5초'로 설정해도 체감은 그 몇 배일 수 있다는 뜻!")


# ============================================================
# 3부: 긴 생성의 권장 패턴 — 스트리밍 + read 타임아웃
# ============================================================
# 긴 답변 생성은 수십 초가 걸려도 정상일 수 있습니다.
# 이때 단순히 전체 타임아웃을 크게 늘리면 "정상적으로 느린 요청"과
# "연결이 멈춘 요청"을 구분하기 어렵습니다.
#
# 실무에서는 긴 생성일수록 스트리밍을 우선 고려합니다.
# 스트리밍은 전체 답변을 한 번에 기다리지 않고, 생성되는 조각을 받는 방식입니다.
# 다만 스트리밍이라고 해서 타임아웃이 필요 없어지는 것은 아닙니다.
#
# 스트리밍에서는 read 타임아웃의 의미가 바뀝니다:
#   - read는 응답 조각(chunk) 사이의 공백을 재는 시계입니다.
#   - 첫 조각이 늦거나, 생성 중간에 조각이 더 이상 오지 않으면 APITimeoutError.
#   - 조각이 계속 도착하면 read 시계는 계속 리셋됩니다.
#
# 즉 read 타임아웃은 "전체 답변 시간 제한"이 아니라
# "첫 조각이 오고 있는가, 생성이 계속 진행 중인가"를 보는 진행 감시자입니다.
print()
print("=" * 60)
print("3부: 스트리밍 — read 타임아웃 = 진행 감시자")
print("=" * 60)

# 연결은 3초 안에 성공해야 하고, 응답 조각 사이 공백은 15초를 넘기면 안 됩니다.
# 단, SDK read 타임아웃만으로는 전체 완료 시간을 제한하지 않습니다.
stream_client = client.with_options(
    timeout=httpx.Timeout(15.0, connect=3.0),
)

start = time.time()
first_token_at = None
char_count = 0

with stream_client.messages.stream(
    model=MODEL,
    max_tokens=500,
    messages=[{"role": "user", "content": "AI Agent가 뭔지 다섯 문장으로 설명해주세요."}],
) as stream:
    for text in stream.text_stream:
        if first_token_at is None:
            first_token_at = time.time() - start   # 첫 응답 조각이 도착한 시각
        char_count += len(text)

total = time.time() - start
print(f"  첫 응답 조각까지: {first_token_at:.1f}초   (read 15초 제한이 감시 중)")
print(f"  전체 완료:       {total:.1f}초 ({char_count}자) — SDK read 기준 총량 제한 없음")
print("  → 전체 시간 타임아웃은 '느리지만 정상'인 긴 생성을 죽입니다.")
print("  → read 타임아웃은 '멈춤'만 잡고 '느린 정상'은 통과시킵니다.")

# --- 진행 감시가 실제로 작동하는지 확인: 말도 안 되는 read 0.1초 ---
print("\n--- read 제한을 0.1초로 줄이면? (첫 응답 조각이 그 안에 올 수 없음) ---")
try:
    with client.with_options(
        timeout=httpx.Timeout(10.0, read=0.1, connect=3.0),
        max_retries=0,
    ).messages.stream(
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": "안녕"}],
    ) as stream:
        for text in stream.text_stream:
            pass
except APITimeoutError:
    print("  APITimeoutError — 첫 응답 조각이 0.1초 안에 오지 않아 중단")


# ============================================================
# 4부: 진행 감시(SDK) vs 총량 감시(asyncio.timeout)
# ============================================================
# SDK 타임아웃과 asyncio.timeout()(부록 A-8)은 서로를 대체하지 않습니다.
# 둘은 서로 다른 질문에 답합니다:
#
#   SDK/httpx 타임아웃 = 진행 감시 — "HTTP 동작이 멈췄는가?"
#     - connect/read/write/pool 같은 단계별 제한
#     - 스트리밍에서는 조각이 도착할 때마다 read 시계가 리셋됨
#     - 재시도 루프 안에서 시도마다 새로 적용 (2부에서 확인)
#
#   asyncio.timeout() = 총량 감시 — "전체 작업이 기한 안에 끝났는가?"
#     - 진행 여부와 무관하게 마감 시각에 절단
#     - 재시도, 백오프 대기, 여러 API 호출을 모두 포함한 SLA
#
# 프로덕션 비동기 코드에서는 보통 둘을 겹쳐 씁니다:
#
#   client = AsyncAnthropic(timeout=30.0, max_retries=2)   # 안: 진행 감시
#   async with asyncio.timeout(45):                        # 밖: 총량 SLA
#       resp = await client.messages.create(...)
#
# 하나만 쓰면 사각지대가 남습니다:
#   SDK만     → 조각이 계속 오면 전체 시간이 너무 길어질 수 있음
#   asyncio만 → 죽은 연결을 전체 마감 시각까지 붙들고 있을 수 있음
print()
print("=" * 60)
print("4부: 진행 감시(SDK) vs 총량 감시(asyncio.timeout)")
print("=" * 60)
print("""
  SDK 타임아웃      = 조각 시계 — "멈췄는가?" (조각마다 리셋, 시도마다 적용)
  asyncio.timeout() = 벽시계   — "늦었는가?" (진행 중이어도 마감에 절단)

  프로덕션 = 겹쳐 쓰기:
    안쪽  AsyncAnthropic(timeout=30)  → 죽은 연결 감지 + 재시도
    바깥  asyncio.timeout(45)         → 재시도 포함 총량 SLA

  (이 파일은 동기 코드라 개념만 정리 — 비동기 실행 예시는 부록 A-8 참고)
""")


# ============================================================
# 정리
# ============================================================
print()
print("=" * 60)
print("정리: 타임아웃 실무 설계")
print("=" * 60)
print("""
┌──────────────────────────┬────────────────────────────────────┐
│ 상황                     │ 실무 선택                           │
├──────────────────────────┼────────────────────────────────────┤
│ 단발 API 호출            │ SDK 설정: Anthropic(timeout=30.0)   │
│ 특정 요청만 다르게       │ client.with_options(timeout=...)    │
│ 연결/읽기 분리           │ httpx.Timeout(60.0, connect=3.0)    │
│ 긴 답변 생성             │ 스트리밍 + read 타임아웃(진행 감시)   │
│ 여러 호출 묶음의 SLA     │ asyncio.timeout() (부록 A-8)         │
└──────────────────────────┴────────────────────────────────────┘

핵심 원칙:
1. LLM은 "느린 것이 정상" — 일반 API 감각으로 짧게 잡지 말 것
2. 체감 시간 = timeout × (재시도+1) + 백오프 — 재시도와 함께 계산
3. 긴 생성은 타임아웃 상향이 아니라 스트리밍 + read 감시로 전환
4. 연결(connect)은 짧게, 읽기(read)는 길게 — 장애 감지와 인내를 분리
5. SDK = 진행 감시(조각 시계), asyncio.timeout = 총량 감시(벽시계)
   — 프로덕션은 안팎으로 겹쳐 쓴다
""")
