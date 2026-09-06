"""Owned, confirmed garment identifier adapter for the integration boundary."""

from __future__ import annotations

from functools import lru_cache

from app.infrastructure.persistence.postgresql_repository import connection
from app.shared_contracts.confirmed_garment_query import ConfirmedGarmentQuery


class SqliteConfirmedGarmentQuery(ConfirmedGarmentQuery):
    """Expose only identifiers for the caller's currently available garments."""

    def list_available_garment_ids(self, user_id: str) -> list[str]:
        with connection() as conn:
            rows = conn.execute(
                "SELECT id FROM garments WHERE user_id=? AND status='available' "
                "ORDER BY is_favourite DESC, updated_at DESC, id ASC",
                (user_id,),
            ).fetchall()
        return [str(row["id"]) for row in rows]


@lru_cache(maxsize=1)
def get_confirmed_garment_query() -> ConfirmedGarmentQuery:
    return SqliteConfirmedGarmentQuery()
