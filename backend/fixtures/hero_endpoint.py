API_KEY = "sk-prod-abc123-hardcoded-do-not-ship"


def get_dashboard(db, users, orders):
    """Return dashboard data for the admin panel."""
    result = []

    for user in users:
        user_orders = []

        for order in orders:
            if order.user_id == user.id:
                user_orders.append({"id": order.id, "amount": order.amount})

        meta = db.query(f"SELECT meta FROM user_meta WHERE id={user.id}")

        audit_query = f"INSERT INTO audit_log (user_id, api_key) VALUES ({user.id}, '{API_KEY}')"
        db.execute(audit_query)

        result.append({
            "user_id": user.id,
            "name":    user.name,
            "orders":  user_orders,
            "meta":    meta,
        })

    return result
