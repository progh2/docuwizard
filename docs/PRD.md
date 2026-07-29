# DocuWizard — Product Requirements Document (PRD)

| 항목 | 내용 |
|------|------|
| 제품명 | DocuWizard |
| 버전 | 0.1 (MVP 설계) |
| 최종 갱신 | 2026-07-29 |
| 상태 | Draft → Implementation |

---

## 1. 개요

### 1.1 한 줄 정의

사업·입찰·지침 문서를 **프로젝트 단위로 로컬에 보관·벡터화**하고, LLM으로 **근거(파일·위치)가 표시되는 질답**을 제공하는 크로스플랫폼 Python GUI 앱.

### 1.2 문제 정의

- 사업 준비 시 RFP·지침·기술서·양식이 많아 필요한 답을 찾기 어렵다.
- 외부 클라우드에 문서를 올리면 보안·기밀 이슈가 있다.
- 답변만 있고 **근거 위치**가 없으면 신뢰·검증이 어렵다.
- 중요한 질답·조항을 나중에 다시 찾기 어렵다.
- 과업 진행에 **꼭 알아둬야 할 포인트**를 문서 전체에서 스스로 추려내기 부담스럽다.

### 1.3 목표

1. 문서를 **여러 프로젝트**로 나누어 로컬 보관·인덱싱한다. 프로젝트마다 **여러 파일**을 등록한다.
2. **로컬 LLM(Ollama 등, gemma 포함)** 을 기본으로 쓰고, 선택적으로 **외부 API(OpenAI/Anthropic)** 로 고품질 답변을 얻는다.
3. 답변마다 **출처(파일명, 페이지/라인/셀 등)** 를 표시한다.
4. **질답 이력**을 남겨 이후에도 찾아볼 수 있게 한다.
5. **즐겨찾기(별표)** 로 중요 대화·답변을 모아볼 수 있게 한다.
6. 인덱싱된 자료를 바탕으로 **과업에 꼭 필요한 포인트를 추천·요약**한다.
7. OS 무관(Windows / macOS / Linux), **PySide6** GUI로 제공한다.
8. 메타·벡터·이력은 **오픈소스 로컬 파일 DB**(SQLite 계열)에 저장한다.

### 1.4 비목표 (v1)

- 팀 실시간 협업·클라우드 동기화
- 문서 편집기 / 입찰서 자동 작성·제출
- 멀티유저 권한 / SSO
- 모바일 앱

### 1.5 주요 사용자·시나리오

**사용자:** 사업·입찰 담당자, 기술 제안 작성자, 내부 규정·지침을 자주 참조하는 실무자.

1. 프로젝트 생성 — 예: `2026-○○사업-제안준비`
2. 자료 추가 — RFP PDF, 지침 HWPX, 양식 DOCX/XLSX, 참고 이미지, 메모 TXT
3. 인덱싱 — 파싱 → 청킹 → 임베딩 → 로컬 DB 저장
4. **필수 포인트 추천** — 마감·제출물·배점·주의사항 등 체크리스트형 요약
5. 질의 — “제출 서류 목록과 마감일은?”, “기술평가 배점 기준은?”
6. 근거 확인 — `RFP.pdf p.12 L45–62` 등 표시 후 원문 점프
7. 중요 답변·대화에 ★ → 즐겨찾기에서 재열람
8. 설정 — Ollama(gemma 등) 기본, 필요 시 Claude/OpenAI

---

## 2. 기능 요구사항

### 2.1 프로젝트 관리

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| P-01 | 프로젝트 생성 / 이름 변경 / 삭제(삭제 시 확인) | Must |
| P-02 | 프로젝트별 설명·태그·생성일 메타데이터 | Should |
| P-03 | 프로젝트 목록·검색·최근 사용 | Must |
| P-04 | 프로젝트 데이터는 앱 데이터 디렉터리에 격리 저장 | Must |
| P-10 | **여러 프로젝트를 동시에 보유**하고 목록에서 전환·검색 | Must |
| P-11 | 프로젝트마다 **파일 N개** 등록 가능(소프트 용량 가이드만) | Must |
| P-12 | 질의·검색·즐겨찾기·추천 요약은 **현재 프로젝트 범위로 격리** | Must |
| P-13 | 프로젝트 홈 요약: 파일 수, 마지막 질의, 즐겨찾기 수, 인덱싱 상태 | Should |

### 2.2 파일 관리

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| F-01 | 지원 형식: TXT/MD, PDF, DOCX, HWPX, XLSX/XLS, 이미지(PNG/JPG/WEBP 등) | Must |
| F-02 | 드래그앤드롭·파일 선택으로 추가 | Must |
| F-03 | 추가 시 프로젝트 `files/` 하위에 원본 복사 보관 | Must |
| F-04 | 파일 목록(이름, 크기, 상태: 대기/인덱싱중/완료/실패) | Must |
| F-05 | 파일 삭제 시 원본·인덱스·청크 일괄 정리 | Must |
| F-06 | 동일 파일 재추가 시 해시 기반 중복/재인덱싱 정책 | Should |
| F-07 | HWPX: 오픈소스 파서로 본문 추출(실패 시 명확한 오류) | Must |
| F-08 | 이미지: 로컬 OCR로 텍스트 추출 후 인덱싱 | Should (v1.1 가능) |

### 2.3 인덱싱·벡터 저장

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| I-01 | 문서 → 텍스트 추출 → 청킹(오버랩 포함) | Must |
| I-02 | 청크 메타: project_id, file_id, path, page/line/cell, char offset | Must |
| I-03 | 로컬 임베딩(Ollama 임베딩 또는 sentence-transformers 등) | Must |
| I-04 | 벡터+메타는 오픈소스 로컬 DB에 저장 (**권장: SQLite + sqlite-vec**) | Must |
| I-05 | 백그라운드 인덱싱, GUI 진행률·취소 | Must |
| I-06 | 인덱싱 실패 파일만 재시도 | Must |

**기술 권장**

- 메타 / 프로젝트 / 채팅 / 즐겨찾기 / 리포트: **SQLite**
- 벡터: **sqlite-vec** (단일 파일, 배포 단순) — 대용량 이슈 시 LanceDB 재검토
- 파서: pypdf, python-docx, openpyxl, hwpx 관련 오픈소스, OCR(pytesseract 또는 rapidocr)

### 2.4 질의응답 (RAG)

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| Q-01 | 프로젝트 선택 후 채팅형 Q&A | Must |
| Q-02 | 검색 → 상위 K 청크 → 컨텍스트 주입 → LLM 응답 | Must |
| Q-03 | 스트리밍 응답(지원 모델/API에 한해) | Should |
| Q-04 | 대화 히스토리 프로젝트별 저장 | Must |
| Q-05 | “이 프로젝트 문서만” 범위 고정 (다른 프로젝트 누수 금지) | Must |
| Q-06 | 관련 문서 없을 때 추측 금지·부족 명시 프롬프트 정책 | Must |

### 2.5 근거(Citation) 표시

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| C-01 | 답변에 사용된 청크별 출처 카드 표시 | Must |
| C-02 | 표시: 파일명 + 형식별 위치(PDF 페이지·대략 라인, TXT/DOCX 라인 범위, XLSX 시트·셀, HWPX 문단/섹션 best-effort) | Must |
| C-03 | 출처 클릭 시 원문 프리뷰/하이라이트 | Should |
| C-04 | LLM이 citation ID를 출력하도록 프롬프트·파싱 (예: `[doc:3]`) | Must |
| C-05 | citation과 실제 검색 청크 불일치 시 “미검증” 표시 | Should |
| C-06 | PDF 등은 **페이지 + 텍스트 스니펫**을 1차 근거로, 라인은 best-effort로 UI에 명시 | Must |

### 2.6 질답 이력 (히스토리)

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| H-01 | 프로젝트별 **대화(스레드) 목록** 영구 저장 | Must |
| H-02 | 한 프로젝트 안 **여러 대화 스레드** 생성 (예: “제출서류”, “배점기준”) | Must |
| H-03 | 메시지 단위 저장: 질문, 답변, 시각, 모델/제공자, 인용 청크 ID | Must |
| H-04 | 대화 목록 검색(키워드)·날짜 필터 | Must |
| H-05 | 대화 이름 변경·삭제(확인), 삭제 시 즐겨찾기 연결 정리 | Must |
| H-06 | 재열람 시 citation도 그대로 복원 | Must |
| H-07 | 앱 재시작 후에도 동일 프로젝트에서 이력 이어서 열람 | Must |

### 2.7 즐겨찾기(별표)

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| Fav-01 | 대화 스레드에 ★ 토글 | Must |
| Fav-02 | 개별 메시지(주로 답변)에 ★ 토글 | Must |
| Fav-03 | 프로젝트 내 **「즐겨찾기」뷰**: 별표 대화 + 별표 답변 모아보기 | Must |
| Fav-04 | 전역(모든 프로젝트) 즐겨찾기 + 프로젝트 필터 | Should |
| Fav-05 | ★ 항목은 목록 상단 고정 또는 별도 탭으로 빠른 접근 | Must |
| Fav-06 | 출처 청크/파일 ★ (중요 조항 북마크) | Could (v1.1) |
| Fav-07 | 필수 포인트 리포트·개별 항목에 ★ | Should |

### 2.8 과업 필수 포인트 추천·요약

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| R-01 | 프로젝트 단위 **「필수 포인트 추천」** 실행 | Must |
| R-02 | 카테고리 예: 일정·마감, 제출물, 자격/제한, 평가·배점, 의무·금지, 리스크·주의, 추가 확인 권장 | Must |
| R-03 | 각 항목: **짧은 요약 + 근거 citation** 필수 | Must |
| R-04 | 결과를 프로젝트 **리포트로 저장**해 이후 재열람 | Must |
| R-05 | 리포트·개별 항목 ★ 가능 | Should |
| R-06 | 파일 추가/재인덱싱 후 **다시 생성**(이전 버전 보관 또는 덮어쓰기 선택) | Should |
| R-07 | 로컬 LLM으로 생성 가능, 고품질은 외부 API 선택(전송 경고 동일) | Must |
| R-08 | 근거 부족 시 “확인 불가/추가 자료 필요” 명시, 추측으로 채우지 않음 | Must |

**동작 개요**

1. 프로젝트 청크에서 키워드·임베딩으로 후보 구간 회수
2. LLM에 구조화 요약 + citation ID 요청
3. 체크리스트형 리포트로 표시 → 저장 → ★ / 이력과 연동

### 2.9 LLM 연동 설정

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| L-01 | Ollama 엔드포인트·모델(예: gemma) 설정·연결 테스트 | Must |
| L-02 | 임베딩 모델 별도 지정 | Must |
| L-03 | OpenAI / Anthropic API 키·모델 선택 | Must |
| L-04 | API 키는 OS 키체인 또는 로컬 암호화 저장, 평문 로그 금지 | Must |
| L-05 | 제공자: 로컬만 / 로컬+외부 선택 UI | Must |
| L-06 | 외부 API 사용 시 “문서 조각이 외부로 전송됨” 경고 확인 | Must |

### 2.10 보안·프라이버시

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| S-01 | 기본 모드: 문서·임베딩·검색은 완전 로컬 | Must |
| S-02 | 텔레메트리 / 자동 업로드 없음 | Must |
| S-03 | 외부 LLM 호출 시에만 선택된 컨텍스트 전송 | Must |
| S-04 | 프로젝트 export/import(암호화 zip) | Could |

### 2.11 GUI (PySide6)

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| U-01 | 좌측: 프로젝트 / 파일·대화·즐겨찾기·필수포인트 / 중앙: 본문 / 우측·하단: 출처 | Must |
| U-02 | 설정 다이얼로그 (LLM, 경로, 임베딩, OCR) | Must |
| U-03 | 한글 UI Must, 다크/라이트 Should | Must / Should |
| U-04 | 인덱싱·응답 중 논블로킹 UI | Must |

**탭 구조 (프로젝트 선택 후)**

`파일` | `대화` | `즐겨찾기` | `필수 포인트`

---

## 3. 시스템 아키텍처 (논리)

```
[PySide6 GUI]
    │
    ├─ ProjectService / FileService
    ├─ IngestPipeline (parse → chunk → embed → store)
    ├─ RetrievalService (vector search + metadata filter)
    ├─ RAGOrchestrator (prompt + citations)
    ├─ EssentialsReportService (필수 포인트 추천)
    ├─ ConversationService / FavoriteService
    ├─ LLMProvider (Ollama | OpenAI | Anthropic)
    └─ Settings / SecureStore
         │
         ▼
[App Data Dir]
  projects/<id>/files/...   # 원본
  docuwizard.db             # SQLite (+ vec)
```

---

## 4. 데이터 모델 (초안)

- **projects**: id, name, description, created_at, updated_at
- **files**: id, project_id, rel_path, original_name, mime, size, content_hash, status, error
- **chunks**: id, file_id, project_id, text, page, line_start, line_end, sheet, cell_range, embedding_ref
- **conversations**: id, project_id, title, created_at, updated_at, is_starred
- **messages**: id, conversation_id, role, content, model, provider, created_at, is_starred
- **message_citations**: message_id, chunk_id, rank
- **essentials_reports**: id, project_id, version, created_at, model, provider, is_starred
- **essentials_items**: id, report_id, category, summary, is_starred
- **essentials_item_citations**: item_id, chunk_id
- **settings**: provider configs (secrets 분리 저장)

---

## 5. UX·프롬프트 정책

- 시스템 프롬프트: “제공된 컨텍스트만 사용. 없으면 모른다고 답하고 추가 확인 문서 제안.”
- 답변 구조 권장: 요약 → 세부 → 주의사항 → 출처
- 사업 준비 특화 템플릿(선택): 체크리스트, 리스크, 제출물, 일정
- 필수 포인트: 카테고리별 bullet + 각 항목 citation 필수

---

## 6. 성공 지표 (MVP)

- TXT / PDF / DOCX / XLSX 안정 인덱싱
- HWPX 본문 추출 성공률을 샘플 셋 기준으로 측정·개선
- 동일 프로젝트 질의에 출처 포함 답변
- 대화 이력·★·필수 포인트 리포트가 재시작 후에도 유지
- 외부 네트워크 차단 환경에서 Ollama만으로 Q&A 가능
- Windows 설치·실행 스모크 통과 (이후 macOS / Linux)

---

## 7. 마일스톤

| Milestone | 감안 기간 | 범위 |
|-----------|-----------|------|
| M0 | 1주 | 저장소·README·PRD·패키지 구조·CI 뼈대 |
| M1 | 1–2주 | PySide 셸: 프로젝트 CRUD, 파일 복사 보관 |
| M2 | 2주 | 파서(TXT/PDF/DOCX/XLSX) + SQLite 스키마 |
| M3 | 2주 | 임베딩 + 벡터검색 + 기본 RAG(Ollama) + 대화 영속화 |
| M4 | 1–2주 | Citation UI + 대화 목록/검색 + ★ 즐겨찾기 |
| M5 | 1–2주 | 필수 포인트 리포트 + HWPX + (선택) OCR |
| M6 | 1주 | OpenAI/Anthropic + 보안 경고 |
| M7 | 1주 | 패키징, 문서, 버그픽스 |

상세 이슈 목록: [GITHUB_BACKLOG.md](./GITHUB_BACKLOG.md)

---

## 8. GitHub 운영

- **Projects**: 칸반 — Backlog / Ready / In Progress / Review / Done
- **Milestones**: M0–M7
- **Labels**: `type:feat|bug|docs`, `area:gui|ingest|rag|llm|security|history|favorites|essentials`, `prio:P0|P1`
- **Issue 규칙**: 하나의 이슈 = 하나의 검증 가능한 산출물 + Acceptance Criteria

---

## 9. 리스크·제약

| 리스크 | 대응 |
|--------|------|
| HWPX 파서 품질 편차 | 실패 UX + 텍스트 변환본 수동 첨부 가이드 |
| 라인 번호 부정확(PDF/한글) | 페이지+구간 1차, 라인은 best-effort 명시 |
| 로컬 모델 환각 | citation 강제·근거 없는 주장 억제 |
| API 키 유출 | 키체인/암호화, .gitignore, 로그 마스킹 |
| 대용량 문서 | 청크 배치·진행률·파일당 제한 안내 |
| 필수 포인트 누락 | 카테고리 템플릿 + “확인 불가” 허용 + 재생성 |

---

## 10. 라이선스·오픈소스

- 앱 코드: MIT 또는 Apache-2.0 (팀 확정)
- 의존성 라이선스 호환성 체크(상용 배포 시)
- 사용자 문서는 사용자 기기 로컬 소유 — 앱이 소유권 주장 안 함

---

## 11. 미결 결정 (Open Questions)

1. 벡터 저장소 최종: sqlite-vec vs LanceDB
2. 앱 데이터 경로: OS별 표준 (`%APPDATA%`, `~/Library`, `~/.local/share`)
3. 패키징: PyInstaller vs Briefcase
4. 라이선스 최종 선택
5. HWPX / OCR을 MVP 필수에 포함할지, M5 Should로 둘지
