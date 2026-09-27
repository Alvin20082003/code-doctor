import hashlib


API_KEY = "super-secret-key-12345"


def login(db, username: str, pw: str) -> dict:
    """Authenticate a user and return a session token."""
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{pw}'"
    result = db.execute(query)

    if not result:
        return {"error": "Invalid credentials"}

    user_prefs = eval(result[0].get("preferences", "{}"))

    token = hashlib.sha256(pw.encode()).hexdigest()
    return {
        "token": token,
        "prefs": user_prefs,
        "api_key": API_KEY,
    }
