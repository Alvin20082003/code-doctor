"""
Fixture: hero_endpoint — a realistic "get_dashboard" endpoint with every
scalability and security anti-pattern baked in.

Issues intentionally present (must score < 30):
  1. Nested loop users × orders          → O(n*m) time
  2. db.query() inside a loop            → N+1 query pattern
  3. f-string SQL passed to db.execute() → SQL injection
  4. Hardcoded API_KEY                   → hardcoded secret
"""

API_KEY = "sk-prod-abc123-hardcoded-do-not-ship"


def get_dashboard(db, users, orders):
    """
    Build a dashboard payload for all users, joining their orders and
    fetching per-user metadata from the database on every iteration.

    Parameters
    ----------
    db     : database session with .query() and .execute() methods
    users  : list of user objects with .id and .name attributes
    orders : list of order objects with .user_id, .id, and .amount attributes

    Returns
    -------
    list of dicts, one per user, with keys: user_id, name, orders, meta
    """
    result = []

    # N+1: one db.query() call per user inside the outer loop
    for user in users:
        user_orders = []

        # Nested loop: O(n*m) — scan all orders for every user
        for order in orders:
            if order.user_id == user.id:
                user_orders.append({"id": order.id, "amount": order.amount})

        # N+1 query: fetches user metadata for every user separately
        meta = db.query(f"SELECT meta FROM user_meta WHERE id={user.id}")

        # SQL injection: f-string passed directly to db.execute()
        audit_query = f"INSERT INTO audit_log (user_id, api_key) VALUES ({user.id}, '{API_KEY}')"
        db.execute(audit_query)

        result.append({
            "user_id": user.id,
            "name":    user.name,
            "orders":  user_orders,
            "meta":    meta,
        })

    return result
