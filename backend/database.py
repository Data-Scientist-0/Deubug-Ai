import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            is_verified INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS otp_codes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    NOT NULL,
            code        TEXT    NOT NULL,
            expires_at  INTEGER NOT NULL,
            used        INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            title       TEXT    NOT NULL,
            stack       TEXT    DEFAULT '',
            code        TEXT    DEFAULT '',
            result      TEXT    DEFAULT '',
            bug_count   INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.close()


# ── User CRUD ─────────────────────────────────────────────────────────────────

def create_user(username: str, email: str, hashed_password: str) -> dict | None:
    try:
        conn = get_db()
        cursor = conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username.strip(), email.strip().lower(), hashed_password),
        )
        user_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return dict(row)
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username.strip(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_user_email(email: str) -> bool:
    conn = get_db()
    conn.execute(
        "UPDATE users SET is_verified = 1 WHERE email = ?",
        (email.strip().lower(),),
    )
    conn.close()
    return True


def update_username(user_id: int, new_username: str) -> bool:
    try:
        conn = get_db()
        conn.execute(
            "UPDATE users SET username = ? WHERE id = ?",
            (new_username.strip(), user_id),
        )
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def update_password(user_id: int, new_hashed_password: str) -> bool:
    conn = get_db()
    conn.execute(
        "UPDATE users SET password = ? WHERE id = ?",
        (new_hashed_password, user_id),
    )
    conn.close()
    return True


def delete_user(user_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.close()
    return True


# ── OTP CRUD ──────────────────────────────────────────────────────────────────

def save_otp(email: str, code: str, expires_at: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM otp_codes WHERE email = ?", (email.strip().lower(),))
    conn.execute(
        "INSERT INTO otp_codes (email, code, expires_at) VALUES (?, ?, ?)",
        (email.strip().lower(), code, expires_at),
    )
    conn.close()
    return True


def get_latest_otp(email: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        """SELECT * FROM otp_codes
           WHERE email = ? AND used = 0
           ORDER BY created_at DESC LIMIT 1""",
        (email.strip().lower(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_otp_used(email: str) -> bool:
    conn = get_db()
    conn.execute(
        "UPDATE otp_codes SET used = 1 WHERE email = ?",
        (email.strip().lower(),),
    )
    conn.close()
    return True


# ── Session CRUD ──────────────────────────────────────────────────────────────

def create_session(user_id: int, title: str, stack: str, code: str, result: str, bug_count: int) -> dict:
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO sessions (user_id, title, stack, code, result, bug_count)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, title, stack, code, result, bug_count),
    )
    sid = cursor.lastrowid
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return dict(row)


def get_sessions(user_id: int) -> list:
    conn = get_db()
    rows = conn.execute(
        """SELECT id, title, stack, bug_count, created_at, updated_at
           FROM sessions WHERE user_id = ?
           ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_by_id(session_id: int, user_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_session(session_id: int, user_id: int, title: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        """UPDATE sessions SET title = ?, updated_at = datetime('now')
           WHERE id = ? AND user_id = ?""",
        (title.strip(), session_id, user_id),
    )
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def delete_session(session_id: int, user_id: int) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def delete_all_sessions(user_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.close()
    return True


def get_session_stats(user_id: int) -> dict:
    conn = get_db()
    row = conn.execute(
        """SELECT COUNT(*) as total,
                  COALESCE(SUM(bug_count), 0) as total_bugs,
                  MAX(created_at) as last_session
           FROM sessions WHERE user_id = ?""",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {"total": 0, "total_bugs": 0, "last_session": None}