"""Composition-injected wardrobe acquisition boundary for Recommendation."""
from app.shared_contracts.confirmed_garment_query import ConfirmedGarmentQuery

_query: ConfirmedGarmentQuery | None = None
_transaction_query_factory = None


def configure_transaction_garment_query(factory) -> None:
    global _transaction_query_factory
    _transaction_query_factory = factory


def transaction_garment_query(connection) -> ConfirmedGarmentQuery:
    if _transaction_query_factory is None:
        raise RuntimeError("Transaction-bound garment query was not configured at startup.")
    return _transaction_query_factory(connection)


def configure_recommendation_query(query: ConfirmedGarmentQuery) -> None:
    global _query
    _query = query


def confirmed_garment_query() -> ConfirmedGarmentQuery:
    if _query is None:
        raise RuntimeError("Recommendation garment query was not configured at startup.")
    return _query
