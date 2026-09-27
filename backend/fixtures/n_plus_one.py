from typing import List


def get_user_orders(db, user_ids: List[int]) -> dict:
    """Fetch orders grouped by user ID."""
    result = {}
    for user_id in user_ids:
        orders = db.query(
            "SELECT * FROM orders WHERE user_id = ?",
            (user_id,)
        )
        result[user_id] = orders
    return result


def get_user_profiles(db, user_ids: List[int]) -> list:
    """Return profile records for a list of user IDs."""
    profiles = []
    for uid in user_ids:
        user = db.filter(id=uid).first()
        profiles.append(user)
    return profiles
