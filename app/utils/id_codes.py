from __future__ import annotations

from typing import Any, Callable, Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session


def _parse_suffix_int(code: str, prefix: str) -> int | None:
    code = (code or "").strip()
    if not code:
        return None
    if not code.upper().startswith(prefix.upper() + "-"):
        return None
    suffix = code.split("-", 1)[1].strip()
    try:
        return int(suffix)
    except Exception:
        return None


def generate_next_code(
    db: Session,
    model: Any,
    code_attr: str,
    prefix: str,
    width: int = 6,
) -> str:
    """Generate the next code like MAT-000001 or ACT-000001.

    Note: this scans existing codes in Python for SQLite portability.
    """

    prefix = str(prefix or "").strip().upper()
    if not prefix:
        raise ValueError("prefix is required")

    col = getattr(model, code_attr)

    rows: Iterable[tuple[str | None]] = (
        db.query(col)
        .filter(
            col.isnot(None),
            col != "",
        )
        .all()
    )

    max_n = 0
    for (c,) in rows:
        n = _parse_suffix_int(str(c or ""), prefix)
        if n is not None and n > max_n:
            max_n = n

    return f"{prefix}-{(max_n + 1):0{int(width)}d}"


def ensure_codes(
    db: Session,
    model: Any,
    code_attr: str,
    prefix: str,
    width: int = 6,
    order_by_attr: str = "id",
) -> int:
    """Backfill codes for rows where code is null/empty. Returns count updated."""

    prefix = str(prefix or "").strip().upper()
    col = getattr(model, code_attr)
    order_col = getattr(model, order_by_attr)

    missing = (
        db.query(model)
        .filter(or_(col.is_(None), col == ""))
        .order_by(order_col.asc())
        .all()
    )

    if not missing:
        return 0

    # Start after current max
    next_code = generate_next_code(db, model, code_attr=code_attr, prefix=prefix, width=width)
    next_n = _parse_suffix_int(next_code, prefix) or 1

    updated = 0
    for row in missing:
        setattr(row, code_attr, f"{prefix}-{next_n:0{int(width)}d}")
        next_n += 1
        db.add(row)
        updated += 1

    return updated


def _activity_project_prefix(project_id: int, project_width: int = 6) -> str:
    return f"ACT-P{int(project_id):0{int(project_width)}d}"


def _parse_activity_project_suffix_int(code: str, project_prefix: str) -> int | None:
    code = (code or "").strip()
    if not code:
        return None
    if not code.upper().startswith(project_prefix.upper() + "-"):
        return None
    suffix = code.rsplit("-", 1)[-1].strip()
    try:
        return int(suffix)
    except Exception:
        return None


def activity_code_allocator(
    db: Session,
    activity_model: Any,
    project_id: int,
    code_attr: str = "code",
    width: int = 6,
    project_width: int = 6,
) -> Callable[[], str]:
    """Return a callable that yields unique project-scoped Activity codes.

    Format: ACT-P000123-000001
    """

    project_prefix = _activity_project_prefix(project_id, project_width=project_width)
    col = getattr(activity_model, code_attr)
    pid_col = getattr(activity_model, "project_id")

    rows: Iterable[tuple[str | None]] = (
        db.query(col)
        .filter(
            pid_col == int(project_id),
            col.isnot(None),
            col != "",
        )
        .all()
    )

    max_n = 0
    for (c,) in rows:
        n = _parse_activity_project_suffix_int(str(c or ""), project_prefix)
        if n is not None and n > max_n:
            max_n = n

    next_n = max_n + 1

    def _next() -> str:
        nonlocal next_n
        code = f"{project_prefix}-{next_n:0{int(width)}d}"
        next_n += 1
        return code

    return _next


def generate_next_activity_code(
    db: Session,
    activity_model: Any,
    project_id: int,
    code_attr: str = "code",
    width: int = 6,
    project_width: int = 6,
) -> str:
    return activity_code_allocator(
        db,
        activity_model,
        project_id=project_id,
        code_attr=code_attr,
        width=width,
        project_width=project_width,
    )()


def ensure_activity_codes_per_project(
    db: Session,
    activity_model: Any,
    code_attr: str = "code",
    width: int = 6,
    project_width: int = 6,
) -> int:
    """Backfill/normalize activity codes to project-scoped format.

    Updates rows where code is missing OR not in ACT-Pxxxxxx-xxxxxx format for that project.
    """

    col = getattr(activity_model, code_attr)
    pid_col = getattr(activity_model, "project_id")
    id_col = getattr(activity_model, "id")

    project_ids = [int(pid) for (pid,) in db.query(pid_col).distinct().all() if pid is not None]
    updated = 0

    for pid in project_ids:
        project_prefix = _activity_project_prefix(pid, project_width=project_width)
        next_code = activity_code_allocator(
            db,
            activity_model,
            project_id=pid,
            code_attr=code_attr,
            width=width,
            project_width=project_width,
        )

        rows = (
            db.query(activity_model)
            .filter(pid_col == pid)
            .order_by(id_col.asc())
            .all()
        )
        for r in rows:
            existing = str(getattr(r, code_attr, "") or "").strip()
            ok = _parse_activity_project_suffix_int(existing, project_prefix) is not None
            if ok:
                continue
            setattr(r, code_attr, next_code())
            db.add(r)
            updated += 1

    return updated
