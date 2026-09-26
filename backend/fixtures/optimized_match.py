"""
Fixture: optimized match using a dict-grouping approach.
Groups orders by user_id in one pass, then iterates users to look up.
Total work: O(n+m) — one pass to build the dict, one pass per collection.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class User:
    id: int
    name: str


@dataclass
class Order:
    id: int
    user_id: int
    amount: float


def match_orders_optimized(users: List[User], orders: List[Order]) -> dict:
    """
    Build a lookup dict from orders grouped by user_id, then iterate users
    once and fetch each user's orders via O(1) dict access.

    Time: O(n+m) — O(m) to build the dict + O(n) to iterate users.
    Space: O(n+m) — the grouped dict holds all orders.
    """
    # First pass: group orders by user_id — O(m)
    orders_by_user: dict = {}
    for order in orders:
        orders_by_user.setdefault(order.user_id, []).append(order)

    # Second pass: for each user, fetch their orders in O(1) — O(n) total
    result = {}
    for user in users:
        result[user.id] = orders_by_user.get(user.id, [])
    return result
