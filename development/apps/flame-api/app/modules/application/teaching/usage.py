"""Application usage quotas use only the server-verified principal."""


def daily_usage_limit(principal: dict, member_limit: int) -> int | None:
    return None if principal.get("role") == "admin" else member_limit
