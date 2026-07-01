"""
Chapter 2-2: Chain of Thought (CoT) — 단계적 추론

CoT란?
  LLM이 바로 답만 내지 않고, 중간 풀이 과정을 거치게 하는 기법입니다.
  LLM은 다음 토큰을 예측하는 모델이므로, 중간 단계를 출력하면
  각 단계가 다음 단계의 맥락이 되어 더 정확한 결론에 도달합니다.

CoT를 구현하는 두 가지 방식:
  1. 프롬프트 기반 CoT
     - 프롬프트에 "단계별로 생각하세요" 등을 추가
     - 추론 과정이 응답 텍스트에 포함됨 → 출력 토큰으로 과금

  2. Extended Thinking (Reasoning Model)
     - 모델이 응답 전에 내부적으로 "생각"하는 단계를 거침
     - 추론 과정은 별도 thinking 블록에 담기고, 응답은 결론만 포함
     - 같은 모델이라도 thinking 파라미터로 활성화/비활성화 가능
     - 예: Claude (Extended Thinking), OpenAI o1/o3, DeepSeek R1

이 예제의 구성:
  1부: 프롬프트 기반 CoT — 추론 형식을 프롬프트로 제어
  2부: Extended Thinking — 모델 내장 추론과 thinking 블록 활용
  3부: Agent 실전 패턴 — 추론과 결과를 JSON으로 분리하여 코드에서 활용
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"

problem = """학교에 학생이 450명 있습니다.
남학생이 여학생보다 30명 많습니다.
여학생 중 40%가 안경을 쓰고 있습니다.
안경을 쓴 여학생은 몇 명입니까?"""


# ============================================================
# 1부: 프롬프트 기반 CoT
# ============================================================
# 프롬프트 문장만으로 풀이 방식과 답변 형식을 유도합니다.
# 같은 문제라도 어떤 지시를 주느냐에 따라 출력이 크게 달라집니다.
print("=" * 60)
print("1부: 프롬프트 기반 CoT")
print("=" * 60)

# --- 자유 형식 CoT ---
# "단계별로 풀어주세요"만 추가하면 모델이 스스로 풀이 형식을 정합니다.
# 간단하지만, 매번 형식이 조금씩 달라질 수 있습니다.
print("\n--- 자유 형식 CoT ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=512,
    messages=[{
        "role": "user",
        "content": f"{problem}\n\n단계별로 풀어주세요.",
    }],
)
print(response.content[0].text)
print(f"\n  [토큰: 입력 {response.usage.input_tokens} / 출력 {response.usage.output_tokens}]")

# --- 구조 지정 CoT ---
# System Prompt로 풀이 구조를 미리 정해 두면 출력이 더 일정해집니다.
# 대신 프롬프트가 길어지고, 너무 빡빡하면 답변이 부자연스러울 수 있습니다.
print("\n--- 구조 지정 CoT ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=512,
    system="""문제를 풀 때 반드시 다음 구조로 응답하세요:
[정보 정리] 주어진 조건을 나열
[풀이] 단계별 계산 과정
[최종 답] 숫자만""",
    messages=[{"role": "user", "content": problem}],
)
print(response.content[0].text)
print(f"\n  [토큰: 입력 {response.usage.input_tokens} / 출력 {response.usage.output_tokens}]")


# ============================================================
# 2부: Extended Thinking (Reasoning Model)
# ============================================================
# Claude에서는 thinking 파라미터를 켜면 모델이 별도의 추론 단계를 사용합니다.
# 같은 모델(claude-sonnet-4-6)이지만 동작 방식이 달라집니다:
#
#   프롬프트 CoT: [프롬프트] → [추론 + 답이 섞인 응답]
#   Extended Thinking: [프롬프트] → [내부 thinking] → [결론만 응답]
#
# thinking의 type 옵션:
#   "enabled"  — 항상 thinking을 수행. budget_tokens로 사고량 조절 (1024 이상).
#   "adaptive" — 모델이 문제 난이도를 판단하여 thinking 여부를 스스로 결정.
#                간단한 질문에는 건너뛰고, 복잡한 문제에만 thinking 수행.
#                → 불필요한 thinking 토큰 비용을 절약할 수 있음.
#   "disabled" — thinking을 사용하지 않음 (기본값, 파라미터 생략과 동일).
#
# 주의사항:
#   - Extended Thinking 사용 시 temperature는 1로 고정 (변경 불가)
#   - max_tokens는 thinking + 응답 전체의 상한이므로 넉넉하게 설정
print()
print("=" * 60)
print("2부: Extended Thinking (Reasoning Model)")
print("=" * 60)

print("\n--- 같은 문제를 Extended Thinking으로 풀기 ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000,
    },
    messages=[{"role": "user", "content": problem}],
)

# 응답 content에는 thinking 블록과 text 블록이 나뉘어 들어옵니다.
for block in response.content:
    if block.type == "thinking":
        print(f"[thinking 블록 — 내부 추론 과정]")
        print(f"{block.thinking}\n")
    elif block.type == "text":
        print(f"[text 블록 — 최종 응답]")
        print(f"{block.text}")

print(f"\n  [토큰: 입력 {response.usage.input_tokens} / 출력 {response.usage.output_tokens}]")
# → 프롬프트에 "단계별로"라고 쓰지 않아도 모델이 충분히 생각한 뒤 답합니다.
# → 추론 과정(thinking)과 최종 응답(text)을 따로 볼 수 있습니다.


# ============================================================
# 3부: Agent 실전 패턴 — 추론과 결과를 JSON으로 분리
# ============================================================
# Agent가 결정을 내릴 때는 "왜 그렇게 판단했는지"를 나중에 확인할 수 있어야 합니다.
# JSON에 reasoning 필드를 포함시키면:
#   - reasoning → 로깅/디버깅용 (판단 근거 추적)
#   - 나머지 필드 → 코드에서 활용 (분기 처리, 라우팅 등)
#
# Extended Thinking도 thinking/text 분리를 자동으로 해주지만,
# 프롬프트 기반 JSON 방식은 모든 LLM에서 범용적으로 사용 가능합니다.
# (이 예제에서는 프롬프트 기반 패턴을 보여주기 위해 Extended Thinking을 사용하지 않습니다)
print()
print("=" * 60)
print("3부: Agent 실전 패턴 (추론 + 결과 분리)")
print("=" * 60)

print("\n--- 고객 문의 분류 Agent ---")
response = client.messages.create(
    model=MODEL,
    max_tokens=512,
    system="""당신은 고객 문의를 분류하는 Agent입니다.
문의를 분석하고 아래 JSON 형식으로만 응답하세요. 마크다운 코드블록 없이 순수 JSON만 출력하세요.

{
  "reasoning": "판단 근거를 단계별로 서술",
  "category": "환불|배송|제품문의|기술지원|기타",
  "priority": "high|medium|low",
  "suggested_action": "추천 대응 방법"
}""",
    messages=[{
        "role": "user",
        "content": "3일 전에 주문한 노트북이 아직 배송되지 않았고, 내일 발표가 있어서 급합니다.",
    }],
)

raw = response.content[0].text
print(f"LLM 원본 응답:\n{raw}\n")

# 모델이 JSON을 마크다운 코드 블록으로 감싸는 경우가 있어 한 번 정리합니다.
cleaned = raw.strip()
if cleaned.startswith("```"):
    cleaned = cleaned.split("\n", 1)[1]
    cleaned = cleaned.rsplit("```", 1)[0].strip()

result = json.loads(cleaned)

# Agent 코드에서는 reasoning은 로그로, 나머지 필드는 실제 분기 처리에 쓸 수 있습니다.
print("[로깅용] 추론 과정:", result["reasoning"])
print("[코드용] 분류:", result["category"])
print("[코드용] 우선순위:", result["priority"])
print("[코드용] 추천 대응:", result["suggested_action"])


# ============================================================
# 정리
# ============================================================
print()
print("=" * 60)
print("정리: Chain of Thought")
print("=" * 60)
print("""
1. 프롬프트 기반 CoT
   - "단계별로 생각하세요" → 간단하지만 형식이 불안정
   - 구조 지정 ([분석] → [풀이] → [답]) → 일관된 출력
   - JSON reasoning 필드 → 추론과 결과를 코드에서 분리 가능

2. Extended Thinking (Reasoning Model)
   - thinking 파라미터로 활성화 (같은 모델에서 켜고 끄기 가능)
   - thinking 블록(추론)과 text 블록(결론)이 자동 분리
   - type 옵션: enabled(항상) / adaptive(자동 판단) / disabled(끔)
   - 복잡한 추론에서 정확도가 더 높음

3. 선택 가이드
   - 간단한 분류/변환 → 프롬프트 CoT로 충분
   - 복잡한 수학/논리/코드 분석 → Extended Thinking 권장
   - Agent 의사결정 로깅 → JSON reasoning 또는 thinking 블록 활용
""")
