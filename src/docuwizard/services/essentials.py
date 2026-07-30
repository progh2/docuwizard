"""Essential points report generation and persistence (issues #25–#27)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docuwizard.config import load_settings
from docuwizard.db import db_session
from docuwizard.llm.ollama import OllamaClient, OllamaConfig, OllamaError
from docuwizard.models import utc_now_iso
from docuwizard.rag import vectors
from docuwizard.rag.prompt import format_location
from docuwizard.services import projects as project_service


class EssentialsError(Exception):
    """Raised when essentials report generation fails."""


# (category key, display name, retrieval query)
CATEGORIES: list[tuple[str, str, str]] = [
    ("deadline", "일정·마감", "제출 마감일 기한 접수 기간 일정 스케줄"),
    ("deliverables", "제출물·산출물", "제출 서류 산출물 결과물 제출 방법 양식"),
    ("eligibility", "자격·제한", "참가 자격 요건 제한 결격 사유 조건"),
    ("evaluation", "평가·배점", "평가 기준 배점 심사 항목 가점 감점"),
    ("obligations", "의무·금지", "의무 사항 준수 금지 위반 제재 책임"),
    ("risks", "리스크·주의", "주의 사항 유의 불이익 실격 위험 페널티"),
]

CATEGORY_NAMES: dict[str, str] = {key: name for key, name, _ in CATEGORIES}

_SYSTEM_PROMPT = (
    "당신은 사업 문서에서 과업 수행에 꼭 필요한 정보를 추려 주는 도우미입니다.\n"
    "제공된 컨텍스트만 사용하세요. 컨텍스트에 없는 내용은 만들지 마세요.\n"
    "각 항목은 '- 요약 [doc:N]' 형식의 bullet 한 줄로 쓰세요. "
    "N은 컨텍스트에 표시된 번호입니다."
)

_DOC_REF = re.compile(r"\[doc:(\d+)\]")


@dataclass
class EssentialsItem:
    id: str
    report_id: str
    category: str
    summary: str
    is_starred: bool = False
    citation_ids: list[str] = field(default_factory=list)

    @property
    def category_name(self) -> str:
        return CATEGORY_NAMES.get(self.category, self.category)


@dataclass
class EssentialsReport:
    id: str
    project_id: str
    version: int
    created_at: str
    model: str | None = None
    provider: str | None = None
    is_starred: bool = False
    items: list[EssentialsItem] = field(default_factory=list)


def generate_report(
    project_id: str,
    *,
    client: OllamaClient | None = None,
    settings: dict[str, Any] | None = None,
    db: Path | None = None,
    on_status=None,
) -> EssentialsReport:
    """Retrieve per-category context, summarize with the LLM, and persist."""
    project_service.get_project(project_id)
    cfg = settings or load_settings()
    ollama = client or OllamaClient(OllamaConfig.from_settings(cfg))
    top_k = max(int(cfg.get("rag", {}).get("top_k", 5)), 3)
    embed_model = ollama.config.embed_model

    def status(message: str) -> None:
        if on_status:
            on_status(message)

    report = EssentialsReport(
        id=uuid.uuid4().hex,
        project_id=project_id,
        version=_next_version(project_id, db=db),
        created_at=utc_now_iso(),
        model=ollama.config.chat_model,
        provider="ollama",
    )

    any_context = False
    for idx, (key, name, query) in enumerate(CATEGORIES, start=1):
        status(f"[{idx}/{len(CATEGORIES)}] {name} 분석 중…")
        try:
            query_vecs = ollama.embed([query])
        except OllamaError as exc:
            raise EssentialsError(str(exc)) from exc
        chunks = vectors.search_project(
            project_id,
            query_vecs[0],
            top_k=top_k,
            model=embed_model,
            db=db,
        )
        if not chunks:
            continue
        any_context = True
        messages = _build_messages(name, chunks)
        try:
            text = ollama.chat(messages, stream=False)
        except OllamaError as exc:
            raise EssentialsError(str(exc)) from exc
        for summary, refs in _parse_items(text):
            citation_ids = [
                chunks[n - 1].chunk_id for n in refs if 1 <= n <= len(chunks)
            ]
            report.items.append(
                EssentialsItem(
                    id=uuid.uuid4().hex,
                    report_id=report.id,
                    category=key,
                    summary=summary,
                    citation_ids=list(dict.fromkeys(citation_ids)),
                )
            )

    if not any_context:
        raise EssentialsError(
            "인덱싱된 문서가 없습니다. 파일을 추가하고 인덱싱을 먼저 실행하세요."
        )
    if not report.items:
        raise EssentialsError("모델이 유효한 항목을 생성하지 못했습니다. 다시 시도하세요.")

    _save_report(report, db=db)
    status(f"리포트 v{report.version} 저장 완료 ({len(report.items)}개 항목)")
    return report


def _build_messages(
    category_name: str, chunks: list[vectors.RetrievedChunk]
) -> list[dict[str, str]]:
    blocks = [
        f"[doc:{idx}] ({format_location(chunk)})\n{chunk.text}"
        for idx, chunk in enumerate(chunks, start=1)
    ]
    user = (
        f"컨텍스트:\n{chr(10).join(blocks)}\n\n"
        f"카테고리 「{category_name}」에 해당하는 핵심 항목을 최대 5개 bullet로 "
        "한국어로 요약하세요. 각 bullet 끝에 근거 [doc:N]을 붙이세요. "
        "해당 내용이 컨텍스트에 없으면 아무것도 출력하지 마세요."
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _parse_items(text: str) -> list[tuple[str, list[int]]]:
    """Return (summary, doc numbers) per bullet; fall back to whole text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    bullets = [ln.lstrip("-•* ").strip() for ln in lines if ln[:1] in "-•*"]
    if not bullets and lines:
        bullets = [" ".join(lines)]
    items: list[tuple[str, list[int]]] = []
    for bullet in bullets:
        refs = [int(n) for n in _DOC_REF.findall(bullet)]
        summary = _DOC_REF.sub("", bullet).strip(" ,.·")
        if summary:
            items.append((summary, refs))
    return items


def _next_version(project_id: str, *, db: Path | None = None) -> int:
    with db_session(db) as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM essentials_reports WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    return int(row[0]) + 1


def _save_report(report: EssentialsReport, *, db: Path | None = None) -> None:
    with db_session(db) as conn:
        conn.execute(
            """
            INSERT INTO essentials_reports(
                id, project_id, version, created_at, model, provider, is_starred
            ) VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                report.id,
                report.project_id,
                report.version,
                report.created_at,
                report.model,
                report.provider,
            ),
        )
        for item in report.items:
            conn.execute(
                """
                INSERT INTO essentials_items(id, report_id, category, summary, is_starred)
                VALUES (?, ?, ?, ?, 0)
                """,
                (item.id, item.report_id, item.category, item.summary),
            )
            conn.executemany(
                """
                INSERT OR IGNORE INTO essentials_item_citations(item_id, chunk_id)
                VALUES (?, ?)
                """,
                [(item.id, chunk_id) for chunk_id in item.citation_ids],
            )


def list_reports(project_id: str, *, db: Path | None = None) -> list[EssentialsReport]:
    """Report metadata (no items), newest first."""
    with db_session(db) as conn:
        rows = conn.execute(
            """
            SELECT * FROM essentials_reports
            WHERE project_id = ?
            ORDER BY version DESC
            """,
            (project_id,),
        ).fetchall()
    return [_row_to_report(row) for row in rows]


def get_report(report_id: str, *, db: Path | None = None) -> EssentialsReport:
    with db_session(db) as conn:
        row = conn.execute(
            "SELECT * FROM essentials_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        if row is None:
            raise LookupError("리포트를 찾을 수 없습니다.")
        report = _row_to_report(row)
        item_rows = conn.execute(
            "SELECT * FROM essentials_items WHERE report_id = ? ORDER BY rowid ASC",
            (report_id,),
        ).fetchall()
        for item_row in item_rows:
            cite_rows = conn.execute(
                "SELECT chunk_id FROM essentials_item_citations WHERE item_id = ?",
                (item_row["id"],),
            ).fetchall()
            report.items.append(
                EssentialsItem(
                    id=item_row["id"],
                    report_id=item_row["report_id"],
                    category=item_row["category"],
                    summary=item_row["summary"],
                    is_starred=bool(item_row["is_starred"]),
                    citation_ids=[c["chunk_id"] for c in cite_rows],
                )
            )
    return report


def toggle_report_star(report_id: str, *, db: Path | None = None) -> bool:
    with db_session(db) as conn:
        row = conn.execute(
            "SELECT is_starred FROM essentials_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        if row is None:
            raise LookupError("리포트를 찾을 수 없습니다.")
        new_value = 0 if row["is_starred"] else 1
        conn.execute(
            "UPDATE essentials_reports SET is_starred = ? WHERE id = ?",
            (new_value, report_id),
        )
    return bool(new_value)


def toggle_item_star(item_id: str, *, db: Path | None = None) -> bool:
    with db_session(db) as conn:
        row = conn.execute(
            "SELECT is_starred FROM essentials_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if row is None:
            raise LookupError("항목을 찾을 수 없습니다.")
        new_value = 0 if row["is_starred"] else 1
        conn.execute(
            "UPDATE essentials_items SET is_starred = ? WHERE id = ?",
            (new_value, item_id),
        )
    return bool(new_value)


@dataclass(frozen=True)
class StarredEssentialsItem:
    item: EssentialsItem
    report_version: int


def list_starred_items(
    project_id: str, *, db: Path | None = None
) -> list[StarredEssentialsItem]:
    with db_session(db) as conn:
        rows = conn.execute(
            """
            SELECT i.*, r.version AS report_version
            FROM essentials_items i
            JOIN essentials_reports r ON r.id = i.report_id
            WHERE r.project_id = ? AND i.is_starred = 1
            ORDER BY r.version DESC, i.rowid ASC
            """,
            (project_id,),
        ).fetchall()
        starred: list[StarredEssentialsItem] = []
        for row in rows:
            cite_rows = conn.execute(
                "SELECT chunk_id FROM essentials_item_citations WHERE item_id = ?",
                (row["id"],),
            ).fetchall()
            starred.append(
                StarredEssentialsItem(
                    item=EssentialsItem(
                        id=row["id"],
                        report_id=row["report_id"],
                        category=row["category"],
                        summary=row["summary"],
                        is_starred=True,
                        citation_ids=[c["chunk_id"] for c in cite_rows],
                    ),
                    report_version=row["report_version"],
                )
            )
    return starred


def _row_to_report(row) -> EssentialsReport:
    return EssentialsReport(
        id=row["id"],
        project_id=row["project_id"],
        version=row["version"],
        created_at=row["created_at"],
        model=row["model"],
        provider=row["provider"],
        is_starred=bool(row["is_starred"]),
    )
