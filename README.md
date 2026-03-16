# 글로벌시스템융합과 AI-Agent 교과목 실습자료

Claude API를 활용한 AI Agent 개발 실습 코드 모음입니다.
LLM과의 기본 통신부터 시작하여 Agent를 단계적으로 구축해나갑니다.

## 사전 준비

### 1. Python 환경

- Python 3.13 이상

### 2. 의존성 설치

```bash
pip install -e .
```

### 3. API 키 설정

프로젝트 루트에 `.env` 파일을 생성하고 수업시간에 배부된 API 키를 입력합니다.

```
ANTHROPIC_API_KEY=수업시간에_배부된_키
```

## 실습 목차

### Chapter 1: LLM 기본 통신

AI Agent와 LLM 사이의 기본적인 통신 방법을 배웁니다.

#### 예제 코드 (`chapter1/examples/`)

| 파일 | 주제 | 핵심 내용 |
|------|------|-----------|
| `01_basic_call.py` | API 기본 호출 | 클라이언트 생성, `messages.create()`, 응답 구조, 토큰 개념 |
| `02_system_prompt.py` | System Prompt | `system` 파라미터로 AI의 역할과 행동 방식 지정, 프롬프트 권한 계층 |
| `03_parameters.py` | 주요 파라미터 | `max_tokens`, `temperature` 실험 |
| `04_streaming.py` | 스트리밍 응답 | 실시간 토큰 수신, 이벤트 타입별 처리 |
| `05_stateless_and_agent.py` | Stateless → Agent | LLM의 무상태 특성, 대화 히스토리 관리, Agent 루프 |
| `06_message_format.py` | 메시지 포맷 | 요청/응답의 실제 구조, 멀티턴 메시지 흐름 |
| `07_error_handling.py` | 에러 핸들링 | 에러 타입별 처리, Exponential Backoff 재시도 |
| `08_structured_output.py` | 구조화된 출력 | JSON 응답 유도, 안전한 파싱, 파싱 실패 시 재시도 |
| `09_timeout.py` | 타임아웃 실무 접근 | SDK 타임아웃 설정, 재시도 상호작용, 스트리밍 read 감시, 진행 vs 총량 |
| `10_production_client.py` | 실무형 호출 함수 (종합) | 단일 진입점, Result 타입, Semaphore+deadline+SDK 3겹 방어, 로깅 |

> 권장 학습 순서: 01~06 → 08(응답 다루기) → 07(에러) → 09(타임아웃) → 10(종합).
> 10번은 비동기 코드이므로 부록 A-1~A-3을 먼저 보는 것을 권장합니다.

#### 실습 코드 (`chapter1/practices/`)

| 폴더 | 주제 | 핵심 내용 |
|------|------|-----------|
| `p00_flask_basics/` | Flask 핵심 입문 | 라우트·render_template·GET/POST·request·JSON 응답 (Claude 없이 Flask만, p01·p02 선행) |
| `p01_persona_chatbot/` | 페르소나 챗봇 | System Prompt로 AI 성격 설정, Flask + SSE 스트리밍 채팅 |
| `p02_model_playground/` | 모델 플레이그라운드 | 모델 비교(Haiku/Sonnet/Opus), 파라미터 실험, 토큰·응답시간 측정 |

### Chapter 2: 프롬프트 엔지니어링

LLM을 정밀하게 제어하는 기법을 배웁니다. Agent의 "두뇌 설계"에 해당합니다.

#### 예제 코드 (`chapter2/examples/`)

| 파일 | 주제 | 핵심 내용 |
|------|------|-----------|
| `01_few_shot.py` | Few-shot Prompting | 예시 기반 패턴 학습, Zero-shot/Few-shot 비교 |
| `02_chain_of_thought.py` | Chain of Thought | 프롬프트 기반 CoT, Extended Thinking (Reasoning Model), Agent 패턴 |
| `03_prompt_chaining.py` | Prompt Chaining | 작업 분할 및 연쇄, 검증 체인, 변환 체인 |
| `04_prompt_template.py` | Prompt Template | 변수 치환, 컨텍스트 주입, 조건부 템플릿 |
| `05_output_control.py` | 출력 제어 | 역할 고정, 제약 조건, 가드레일 |
| `06_prefill_stop_sequences.py` | Prefill + stop_sequences | 응답 시작/끝 강제 (레거시 기법, Sonnet 4.5) |
| `07_structured_outputs.py` | Structured Outputs | JSON 스키마·enum으로 출력 보장 (현대식, 권장) |
| `08_parse_pydantic.py` | 실무형 검증 (종합) | `messages.parse()` + Pydantic 재검증, stop_reason·예외 경계 방어 |

> 01~04는 프롬프트 작성 기법, 05~08은 출력 형식 제어를 API 기능으로 확장하는 아크입니다:
> 프롬프트로 부탁(05) → 기계적 차단(06, 레거시) → API 보장(07) → 검증·방어(08).

#### 실습 코드 (`chapter2/practices/`)

| 폴더 | 주제 | 핵심 내용 |
|------|------|-----------|
| `p01_code_reviewer/` | AI 코드 리뷰어 | Few-shot + 구조 지정 CoT + 가드레일 |
| `p02_news_pipeline/` | 뉴스 요약 파이프라인 | Prompt Chaining (4단계) + Prompt Template |
| `p03_student_counselor/` | 학생 상담 챗봇 | 조건부 템플릿 + 역할 고정 + Extended Thinking + Few-shot |
| `p04_review_scorer/` | 음식점 후기 평가기 | `messages.parse()` + Pydantic으로 별점·감정 JSON 보장(07·08 응용), 신뢰 경계 예외 처리, `.txt` 업로드 |

### Chapter 3: Tool Use (Function Calling)

LLM이 외부 도구를 호출하여 실제 행동하는 Agent를 만듭니다.

#### 예제 코드 (`chapter3/examples/`)

| 파일 | 주제 | 핵심 내용 |
|------|------|-----------|
| `00_tool_use_6steps.py` | Tool Use 6단계 | 함수 구현 → Schema 정의 → API 호출 → Routing → Result 주입 → 테스트 |
| `01_tool_use_basic.py` | Tool Use 기본 | 도구 정의(JSON Schema), tool_use/tool_result 흐름 |
| `02_multiple_tools.py` | 다중 도구 | 여러 도구 중 LLM이 상황에 맞게 선택 |
| `03_tool_use_loop.py` | Agent 루프 | tool_use → tool_result → 반복의 Agent 루프 패턴 |
| `04_sequential_tools.py` | 순차 도구 호출 | 도구 A 결과를 도구 B 입력으로 체이닝 |
| `05_tool_error_handling.py` | 에러 처리 | is_error 플래그, 도구 실패 시 Agent 대응 패턴 |

#### 실습 코드 (`chapter3/practices/`)

| 폴더 | 주제 | 핵심 내용 |
|------|------|-----------|
| `p01_multi_tool_assistant/` | 멀티툴 어시스턴트 | 다중 도구 Agent 루프, 도구 호출 과정 실시간 시각화, 에러 처리 |

### Chapter 4: MCP (Model Context Protocol)

도구를 표준 프로토콜로 분리하여 재사용 가능한 Agent를 만듭니다.

#### 예제 코드 (`chapter4/examples/`)

| 파일 | 주제 | 핵심 내용 |
|------|------|-----------|
| `01_mcp_concept.py` | MCP 개념 | 프로토콜 구조, Ch3(Tool Use) 대비 장점 비교 |
| `02_mcp_server.py` | MCP 서버 | `@mcp.tool()` 데코레이터로 도구 노출, JSON Schema 자동 생성 |
| `03_mcp_client.py` | MCP 클라이언트 | 서버 연결, 도구 목록 자동 조회, `session.call_tool()` |
| `04_multi_server.py` | 다중 서버 | 여러 MCP 서버 동시 연결, 도구→서버 라우팅 |
| `05_mcp_chatbot.py` | MCP 대화형 Agent | Agent 루프 + MCP 통합, 대화 히스토리 관리 |

#### 실습 코드 (`chapter4/practices/`)

| 폴더 | 주제 | 핵심 내용 |
|------|------|-----------|
| `p01_schedule_agent/` | 일정 관리 Agent | MCP 서버(SQLite) + Flask Agent, 자연어로 일정 CRUD |

### 부록: 비동기(Async) 프로그래밍 기초

MCP 등 네트워크 기반 코드를 이해하기 위한 Python 비동기 프로그래밍 기초입니다.

#### 예제 코드 (`appendix/async_basics/`)

| 파일 | 주제 | 핵심 내용 |
|------|------|-----------|
| `01_sync_vs_async.py` | 동기 vs 비동기 | 왜 비동기가 필요한가? 커피 주문 비유, 시간 비교 |
| `02_async_syntax.py` | 비동기 문법 핵심 | `async def`, `await`, `asyncio.run()` 3가지 키워드 |
| `03_task_and_future.py` | Task와 Future | `create_task`, Task 상태/결과, 동시 실행의 핵심 |
| `04_async_patterns.py` | 자주 쓰는 패턴 | `gather`, `TaskGroup`, `async with` |
| `05_async_exception.py` | 비동기 예외 처리 | 개별 try/except, `return_exceptions`, TaskGroup, 재시도 |
| `06_async_api_call.py` | 실전 API 호출 | `AsyncAnthropic`으로 Claude API 동시 호출 |
| `07_main_task_and_cancel.py` | 메인 Task와 종료 시 취소 | `asyncio.run()` 내부 동작, `cancel()`, `CancelledError`, 일괄 취소 |
| `08_concurrency_control.py` | 실무 동시성 제어 | `asyncio.timeout`, `Semaphore`, TaskGroup 조합 패턴 |
| `09_taskgroup_cancellation.py` | TaskGroup 취소 전파 | 자동 취소, 성공·실패·취소 상태 구분, gather와의 차이 |

> 권장 학습 순서: 01 → 02 → 03 → 07(Task 심화·취소) → 04 → 05 → 09(취소 심화) → 08(실무 제어) → 06(실전 API).
> 번호는 파일 관리용이며, 취소(cancel) 개념이 05·08·09의 선행 지식이라 07을 먼저 보는 것을 권장합니다.


#### 실습 코드 (`chapter1/practices/`)

| 폴더 | 주제 | 핵심 내용 |
|------|------|-----------|
| `p01_persona_chatbot/` | 페르소나 챗봇 | System Prompt로 AI 성격 설정, Flask + SSE 스트리밍 채팅 |

### 실행 방법

```bash
python chapter1/examples/01_basic_call.py
```

## 기술 스택

- **LLM**: Claude API (Anthropic)
- **언어**: Python 3.13+
- **주요 라이브러리**: `anthropic`, `flask`, `mcp`, `python-dotenv`
