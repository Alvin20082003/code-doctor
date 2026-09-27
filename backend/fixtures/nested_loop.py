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
    """Return a mapping of user ID to the list of their orders."""
    result = {}
    for user in users:
        user_orders = []
        for order in orders:
            if user.id == order.user_id:
                user_orders.append(order)
        result[user.id] = user_orders
    return result
