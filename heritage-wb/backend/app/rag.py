"""Retrieval-augmented chat over the site database.

Retrieval is Postgres full-text search (no embedding model needed for ~dozens of
sites). Swap `retrieve` for pgvector similarity once the archive grows.
"""
import os
import re
from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session
from .models import Site, fts_doc

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
SYSTEM = (
    "You are a guide to the heritage sites of West Bengal. Answer only from the SITE NOTES "
    "provided. If the notes do not contain the answer, say so plainly instead of guessing. "
    "Be concise. Mention site names so visitors can look them up."
)


def retrieve(db: Session, question: str, k: int = 4) -> list[Site]:
    words = [w for w in re.findall(r"\w+", question.lower()) if len(w) > 2]
    if not words:
        return []
    doc = fts_doc()
    q = func.to_tsquery(literal_column("'english'"), " | ".join(words))  # OR match; ranking sorts the best first
    stmt = select(Site).where(doc.op("@@")(q)).order_by(func.ts_rank(doc, q).desc()).limit(k)
    return list(db.scalars(stmt))


def answer(db: Session, question: str, lang: str = "en") -> tuple[str | None, list[str]]:
    sites = retrieve(db, question)
    sources = [s.slug for s in sites]
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None, sources  # retrieval-only mode
    import anthropic

    notes = "\n".join(
        f"- {s.name_en} ({s.region}, {s.year_founded}): {s.description_en}" for s in sites
    ) or "(no matching sites)"
    reply_in = "Bengali" if lang == "bn" else "English"
    msg = anthropic.Anthropic(api_key=key).messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"SITE NOTES:\n{notes}\n\nQuestion: {question}\nReply in {reply_in}."}],
    )
    return "".join(b.text for b in msg.content if b.type == "text"), sources
