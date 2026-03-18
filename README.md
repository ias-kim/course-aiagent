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

#### 실습 코드 (`chapter1/practices/`)

| 폴더 | 주제 | 핵심 내용 |
|------|------|-----------|
| `p01_persona_chatbot/` | 페르소나 챗봇 | System Prompt로 AI 성격 설정, Flask + SSE 스트리밍 채팅 |
| `p02_model_playground/` | 모델 플레이그라운드 | 모델 비교(Haiku/Sonnet/Opus), 파라미터 실험, 토큰·응답시간 측정 |

### Chapter 2: 프롬프트 엔지니어링

LLM을 정밀하게 제어하는 기법을 배웁니다. Agent의 "두뇌 설계"에 해당합니다.

#### 예제 코드 (`chapter2/examples/`)

| 파일 | 주제 | 핵심 내용 |
|------|------|-----------|
| `01_few_shot.py` | Few-shot Prompting | 예시 기반 패턴 학습, Zero-shot/Few-shot 비교 |
| `02_chain_of_thought.py` | Chain of Thought | 단계적 추론 유도, CoT + 구조화된 출력 |
| `03_prompt_chaining.py` | Prompt Chaining | 작업 분할 및 연쇄, 검증 체인, 변환 체인 |
| `04_output_control.py` | 출력 제어 | 역할 고정, 제약 조건, 가드레일 |
| `05_prompt_template.py` | Prompt Template | 변수 치환, 컨텍스트 주입, 도구 선택 템플릿 |

#### 실습 코드 (`chapter2/practices/`)

_준비 중_

### 실행 방법

```bash
python chapter1/examples/01_basic_call.py
```

## 기술 스택

- **LLM**: Claude API (Anthropic)
- **언어**: Python 3.13+
- **주요 라이브러리**: `anthropic`, `flask`, `python-dotenv`
