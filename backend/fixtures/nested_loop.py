"""
Fixture: nested loop — O(n*m) complexity example.
Matches each user against orders by comparing IDs.
"""
from dataclasses import dataclass
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


def match_orders(users: List[User], orders: List[Order]) -> dict:
    """
    For every user, scan all orders to find ones belonging to that user.
    Time complexity: O(n*m) — n users, m orders.
    """
    result = {}
    for user in users:
        user_orders = []
        for order in orders:
            if user.id == order.user_id:
                user_orders.append(order)
        result[user.id] = user_orders
    return result
