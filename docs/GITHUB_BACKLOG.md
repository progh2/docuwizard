# DocuWizard — GitHub Backlog

PRD([PRD.md](./PRD.md))를 구현하기 위한 **Milestone**과 **Issue** 초안입니다.  
GitHub에 Project / Milestone / Issue를 등록할 때 이 문서를 기준으로 복사하면 됩니다.

---

## Labels (권장)

| Label | 용도 |
|-------|------|
| `type:feat` | 기능 |
| `type:bug` | 버그 |
| `type:docs` | 문서 |
| `type:chore` | 인프라·정리 |
| `area:gui` | PySide UI |
| `area:ingest` | 파싱·인덱싱 |
| `area:rag` | 검색·프롬프트 |
| `area:llm` | Ollama/API |
| `area:security` | 키·프라이버시 |
| `area:history` | 대화 이력 |
| `area:favorites` | 즐겨찾기 |
| `area:essentials` | 필수 포인트 |
| `prio:P0` | MVP 필수 |
| `prio:P1` | 중요 |

---

## Project 보드 컬럼

`Backlog` → `Ready` → `In Progress` → `Review` → `Done`

---

## Milestones

| ID | 제목 | 목표 |
|----|------|------|
| M0 | Foundation | 저장소·문서·패키지 구조·CI 뼈대 |
| M1 | Projects & Files UI | 프로젝트 CRUD, 파일 복사 보관 |
| M2 | Ingest & DB | 파서 + SQLite 스키마 |
| M3 | RAG Core | 임베딩·검색·Ollama RAG·대화 영속화 |
| M4 | Citations & Favorites | 출처 UI·대화 검색·★ |
| M5 | Essentials & Formats | 필수 포인트·HWPX·OCR(선택) |
| M6 | External LLMs | OpenAI/Anthropic + 경고 |
| M7 | Ship | 패키징·문서·버그픽스 |

---

## Issues

각 이슈는 GitHub Issue 제목으로 그대로 써도 됩니다.  
본문에는 **Goal / Acceptance Criteria**를 넣습니다.

### M0 — Foundation

#### #1 Repo scaffold (pyproject, src layout, tooling)
- Labels: `type:chore`, `prio:P0`
- **AC**
  - `pyproject.toml`, `src/docuwizard/` 구조
  - ruff / pytest 설정
  - `python -m docuwizard` 진입점 스텁이 실행됨

#### #2 App data directory & config path
- Labels: `type:feat`, `area:security`, `prio:P0`
- **AC**
  - OS별 표준 데이터 경로 결정·문서화
  - 설정 파일 읽기/쓰기 스텁

#### #3 CI smoke (lint + test)
- Labels: `type:chore`, `prio:P1`
- **AC**
  - GitHub Actions에서 ruff + pytest 실행

---

### M1 — Projects & Files UI

#### #4 Project CRUD service
- Labels: `type:feat`, `prio:P0`
- **AC**
  - 생성/이름변경/삭제(확인)
  - 다중 프로젝트 목록·검색

#### #5 Project list GUI (PySide shell)
- Labels: `type:feat`, `area:gui`, `prio:P0`
- **AC**
  - 좌측 프로젝트 목록, 선택 시 상세 영역
  - 한글 UI 기본 문자열

#### #6 File import into `projects/<id>/files`
- Labels: `type:feat`, `area:ingest`, `prio:P0`
- **AC**
  - 파일 선택·드래그앤드롭으로 원본 복사
  - 파일 목록에 이름·크기·상태 표시

#### #7 Delete file / project cascade (filesystem)
- Labels: `type:feat`, `prio:P0`
- **AC**
  - 파일·프로젝트 삭제 시 디렉터리 정리
  - 확인 다이얼로그

---

### M2 — Ingest & DB

#### #8 SQLite schema + migrations
- Labels: `type:feat`, `prio:P0`
- **AC**
  - projects / files / chunks / conversations / messages / favorites / essentials 테이블
  - 마이그레이션 적용 가능

#### #9 TXT/MD parser + line metadata
- Labels: `type:feat`, `area:ingest`, `prio:P0`

#### #10 PDF parser + page metadata
- Labels: `type:feat`, `area:ingest`, `prio:P0`

#### #11 DOCX parser + paragraph/line approx
- Labels: `type:feat`, `area:ingest`, `prio:P0`

#### #12 XLSX parser + sheet/cell
- Labels: `type:feat`, `area:ingest`, `prio:P0`

#### #13 Chunking strategy + config
- Labels: `type:feat`, `area:ingest`, `prio:P0`
- **AC**
  - 청크 크기·오버랩 설정
  - chunk ↔ file/location 메타 연결

#### #14 Background indexing UI (progress / cancel / retry)
- Labels: `type:feat`, `area:gui`, `prio:P0`

---

### M3 — RAG Core

#### #15 Ollama embedding client
- Labels: `type:feat`, `area:llm`, `prio:P0`

#### #16 Vector store insert/search (sqlite-vec)
- Labels: `type:feat`, `area:rag`, `prio:P0`
- **AC**
  - project_id 필터로 타 프로젝트 누수 없음

#### #17 RAG prompt with citation IDs
- Labels: `type:feat`, `area:rag`, `prio:P0`
- **AC**
  - `[doc:N]` 형태 인용
  - 컨텍스트 없으면 “모름” 정책

#### #18 Chat GUI + optional streaming
- Labels: `type:feat`, `area:gui`, `prio:P0`

#### #19 Conversation / message persistence
- Labels: `type:feat`, `area:history`, `prio:P0`
- **AC**
  - 프로젝트별 다중 스레드
  - 재시작 후 복원
  - 메시지에 model/provider/citations 저장

#### #20 Settings: Ollama connection test
- Labels: `type:feat`, `area:llm`, `prio:P0`

---

### M4 — Citations & Favorites

#### #21 Citation panel + click-to-preview
- Labels: `type:feat`, `area:rag`, `area:gui`, `prio:P0`
- **AC**
  - 파일명·페이지/라인/셀 표시
  - 가능 시 원문 스니펫 프리뷰

#### #22 Conversation list rename / delete / search
- Labels: `type:feat`, `area:history`, `area:gui`, `prio:P0`

#### #23 Star toggle on conversations & messages
- Labels: `type:feat`, `area:favorites`, `prio:P0`

#### #24 Favorites view (per project)
- Labels: `type:feat`, `area:favorites`, `area:gui`, `prio:P0`
- **AC**
  - ★ 대화 + ★ 답변 모아보기
  - 클릭 시 해당 대화로 이동

---

### M5 — Essentials & Formats

#### #25 Essentials report pipeline (retrieve → summarize → cite)
- Labels: `type:feat`, `area:essentials`, `prio:P0`
- **AC**
  - 카테고리별 항목 + citation
  - 근거 없으면 “확인 불가” 허용

#### #26 Essentials report UI + save / regenerate
- Labels: `type:feat`, `area:essentials`, `area:gui`, `prio:P0`

#### #27 Star on essentials report/items
- Labels: `type:feat`, `area:favorites`, `area:essentials`, `prio:P1`

#### #28 HWPX ingest
- Labels: `type:feat`, `area:ingest`, `prio:P0`
- **AC**
  - 본문 추출 또는 명확한 실패 메시지

#### #29 Image OCR ingest
- Labels: `type:feat`, `area:ingest`, `prio:P1`

---

### M6 — External LLMs

#### #30 Secure API key storage
- Labels: `type:feat`, `area:security`, `prio:P0`

#### #31 OpenAI provider
- Labels: `type:feat`, `area:llm`, `prio:P0`

#### #32 Anthropic provider
- Labels: `type:feat`, `area:llm`, `prio:P0`

#### #33 External API disclosure / confirm dialog
- Labels: `type:feat`, `area:security`, `area:gui`, `prio:P0`

---

### M7 — Ship

#### #34 Delete project cascade (DB + vectors + files)
- Labels: `type:feat`, `prio:P0`
- **AC**
  - DB·벡터·파일시스템 일관 삭제

#### #35 Packaging (installer)
- Labels: `type:chore`, `prio:P1`

#### #36 Sample fixtures + e2e smoke test
- Labels: `type:chore`, `prio:P1`

#### #37 LICENSE + dependency license check
- Labels: `type:docs`, `prio:P1`

---

## 등록 순서 권장

1. Labels 생성
2. Milestones M0–M7 생성
3. 위 Issue #1–#37 등록 후 Milestone·Label 연결
4. GitHub Project에 Backlog로 적재
5. M0부터 Ready로 이동하며 구현

### CLI 참고 (gh)

```bash
# 예시 — 저장소 원격 연결 후
gh label create "prio:P0" --color "B60205"
gh milestone create --title "M0 Foundation" --description "Repo, docs, package skeleton"

gh issue create --title "Repo scaffold (pyproject, src layout, tooling)" \
  --milestone "M0 Foundation" \
  --label "type:chore,prio:P0" \
  --body "## Goal
...
## Acceptance Criteria
- [ ] ..."
```

원격 저장소와 `gh` 인증이 준비되면 Agent에게 일괄 등록을 요청할 수 있습니다.
