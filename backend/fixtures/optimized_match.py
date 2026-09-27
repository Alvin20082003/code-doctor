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
    """Return a mapping of user ID to their orders, using a pre-grouped lookup."""
    orders_by_user: dict = {}
    for order in orders:
        orders_by_user.setdefault(order.user_id, []).append(order)

    result = {}
    for user in users:
        result[user.id] = orders_by_user.get(user.id, [])
    return result
