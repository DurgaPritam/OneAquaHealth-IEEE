"""Generic CRUD router factory so each resource stays a few lines.

No ``from __future__ import annotations`` here: FastAPI must see the real
schema classes passed in at runtime, not string annotations.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, SQLModel, select

from api.db import get_session


def crud_router(
    table: type[SQLModel],
    create_schema: type[SQLModel] | None,
    update_schema: type[SQLModel],
    prefix: str,
    tag: str,
    filters: tuple[str, ...] = (),
) -> APIRouter:
    """Build list, get, create, patch and delete endpoints for ``table``.

    ``filters`` lists column names accepted as exact-match query parameters on
    the list endpoint, e.g. ``GET /api/checkins?site_id=C1``.
    """
    router = APIRouter(prefix=prefix, tags=[tag])
    filter_doc = f"Optional exact-match filters: {', '.join(filters)}." if filters else "No filters."

    @router.get("", response_model=list[table], description=filter_doc)  # type: ignore[valid-type]
    def list_items(
        request: Request,
        session: Session = Depends(get_session),
        limit: int = Query(500, le=5000),
        offset: int = 0,
    ) -> list[SQLModel]:
        stmt = select(table)
        for name in filters:
            value = request.query_params.get(name)
            if value is not None:
                stmt = stmt.where(getattr(table, name) == _coerce(table, name, value))
        return list(session.exec(stmt.offset(offset).limit(limit)).all())

    @router.get("/{item_id}", response_model=table)
    def get_item(item_id: str, session: Session = Depends(get_session)) -> SQLModel:
        return get_or_404(session, table, item_id)

    if create_schema is not None:

        @router.post("", response_model=table, status_code=201)
        def create_item(payload: create_schema, session: Session = Depends(get_session)) -> SQLModel:  # type: ignore[valid-type]
            item = table.model_validate(payload)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    @router.patch("/{item_id}", response_model=table)
    def update_item(item_id: str, payload: update_schema, session: Session = Depends(get_session)) -> SQLModel:  # type: ignore[valid-type]
        item = get_or_404(session, table, item_id)
        item.sqlmodel_update(payload.model_dump(exclude_unset=True))
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    @router.delete("/{item_id}", status_code=204)
    def delete_item(item_id: str, session: Session = Depends(get_session)) -> None:
        item = get_or_404(session, table, item_id)
        session.delete(item)
        session.commit()

    return router


def _pk_type(table: type[SQLModel]) -> type:
    column = next(iter(table.__table__.primary_key.columns))  # type: ignore[attr-defined]
    try:
        return column.type.python_type
    except NotImplementedError:
        return str


def _coerce(table: type[SQLModel], name: str, value: str) -> Any:
    column = table.__table__.columns[name]  # type: ignore[attr-defined]
    try:
        py_type = column.type.python_type
    except NotImplementedError:
        return value
    if py_type is bool:
        return value.lower() in ("1", "true", "yes")
    if py_type is int:
        return int(value)
    return value


def get_or_404(session: Session, table: type[SQLModel], item_id: str | int) -> Any:
    key: Any = item_id
    if _pk_type(table) is int:
        try:
            key = int(item_id)
        except ValueError:
            raise HTTPException(404, f"{table.__name__} {item_id} not found") from None
    item = session.get(table, key)
    if item is None:
        raise HTTPException(404, f"{table.__name__} {item_id} not found")
    return item
