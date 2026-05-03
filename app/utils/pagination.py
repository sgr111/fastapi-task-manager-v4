"""Pagination utility."""


def calculate_pagination(total: int, skip: int, limit: int) -> dict:
    """Calculate pagination metadata including has_more."""
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total,
    }
