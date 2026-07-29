# DocuWizard

로컬에서 문서를 벡터화하고, LLM으로 **근거 기반** 질의응답을 하는 데스크톱 앱입니다.  
사업·입찰 지침, RFP, 양식을 프로젝트에 모아 두고 준비 포인트와 의문점에 대해 안전하게 조언을 받을 수 있습니다.

## 왜 DocuWizard인가

- **로컬 우선** — 기본은 문서·임베딩·검색이 기기 안에서만 동작합니다.
- **다중 프로젝트** — 사업별로 프로젝트를 나누고, 프로젝트마다 여러 파일을 등록합니다.
- **다양한 포맷** — TXT, PDF, DOCX, HWPX, Excel, 이미지(OCR).
- **근거 표시** — 답변이 어떤 파일의 어느 위치(페이지/라인/셀 등)에 기반했는지 표시합니다.
- **질답 이력** — 대화가 남아 나중에 다시 찾아볼 수 있습니다.
- **즐겨찾기(★)** — 중요 대화·답변을 모아볼 수 있습니다.
- **필수 포인트 추천** — 과업 진행에 꼭 알아둬야 할 항목을 요약·추천하고 근거와 함께 보여 줍니다.
- **LLM 선택** — Ollama(gemma 등) 기본 + OpenAI / Anthropic 선택.

## 기술 스택 (예정)

| 영역 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| GUI | PySide6 |
| DB | SQLite (+ sqlite-vec 권장) |
| LLM | Ollama / OpenAI / Anthropic |
| 패키징 | 추후 확정 (PyInstaller 또는 Briefcase) |

## 상태

🚧 **M0 Foundation 진행 중** — 패키지 스캐폴드·데이터 경로·CI 뼈대 추가.

- 제품 요구사항: [docs/PRD.md](docs/PRD.md)
- GitHub 마일스톤·이슈 백로그: [docs/GITHUB_BACKLOG.md](docs/GITHUB_BACKLOG.md)
- 데이터 경로: [docs/DATA_PATHS.md](docs/DATA_PATHS.md)
- Project 보드: https://github.com/users/progh2/projects/19

## 빠른 시작

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -e ".[dev]"
python -m docuwizard
```

개발 검사:

```bash
ruff check src tests
pytest -q
```

Ollama 설치 후 예: `ollama pull gemma2` (모델명은 설정에서 변경)

## 보안 안내

- **기본 모드**에서는 문서가 외부로 전송되지 않습니다.
- 외부 API(ChatGPT / Claude 등)를 선택하면 **검색된 문서 조각**이 해당 제공자로 전송됩니다. 설정 시 경고를 확인하세요.
- API 키는 저장소에 커밋하지 마세요.

## 개발·기여

GitHub **Issues / Milestones / Projects**로 작업을 분해해 진행합니다.

1. [docs/GITHUB_BACKLOG.md](docs/GITHUB_BACKLOG.md)의 이슈를 GitHub에 등록
2. Milestone(M0–M7)·Label을 연결
3. Project 보드: Backlog → Ready → In Progress → Review → Done
4. PR은 이슈 번호를 포함하고 Acceptance Criteria를 충족해야 합니다.

## 라이선스

TBD (MIT 또는 Apache-2.0 예정)
