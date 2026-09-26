"""
Fixture: N+1 query problem example.
Fetches each user's orders with a separate DB query per user.
"""
from typing import List


def get_user_orders(db, user_ids: List[int]) -> dict:
    """
    Naive implementation that fires one DB query per user_id.
    Classic N+1 query pattern — should batch with an IN clause instead.
    """
    result = {}
    for user_id in user_ids:
        # Each iteration triggers a separate database round-trip
        orders = db.query(
            "SELECT * FROM orders WHERE user_id = ?",
            (user_id,)
        )
        result[user_id] = orders
    return result


def get_user_profiles(db, user_ids: List[int]) -> list:
    """
    Another N+1 pattern using .filter() ORM-style call inside a loop.
    """
    profiles = []
    for uid in user_ids:
        user = db.filter(id=uid).first()
        profiles.append(user)
    return profiles
