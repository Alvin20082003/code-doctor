"""
Fixture: security vulnerabilities — hardcoded secret, SQL injection, eval usage.
"""
import hashlib


API_KEY = "super-secret-key-12345"


def login(db, username: str, pw: str) -> dict:
    """
    Intentionally insecure login function demonstrating multiple issues:
    1. Hardcoded API_KEY string literal above
    2. f-string SQL query passed directly to db.execute (SQL injection)
    3. eval() called on user-supplied data
    """
    # SQL injection: user-controlled data in f-string query
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{pw}'"
    result = db.execute(query)

    if not result:
        return {"error": "Invalid credentials"}

    # Dangerous eval on untrusted input
    user_prefs = eval(result[0].get("preferences", "{}"))

    token = hashlib.sha256(pw.encode()).hexdigest()
    return {
        "token": token,
        "prefs": user_prefs,
        "api_key": API_KEY,
    }
