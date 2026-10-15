"""Local account and session storage for CoolRoute.

Passwords use PBKDF2-HMAC-SHA256 and session secrets are only stored as hashes.
This is intended for the self-hosted local app; email verification and recovery
need an email provider and are intentionally not simulated.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parent / "data" / "coolroute.sqlite3"
SESSION_SECONDS = 14 * 24 * 60 * 60
PBKDF2_ROUNDS = 310_000
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    db = connect()
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize() -> None:
    with database() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
            CREATE TABLE IF NOT EXISTS route_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                route_key TEXT NOT NULL,
                saved_at INTEGER NOT NULL,
                origin_json TEXT NOT NULL,
                destination_json TEXT NOT NULL,
                origin_label TEXT NOT NULL,
                destination_label TEXT NOT NULL,
                city TEXT NOT NULL,
                preferences_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                UNIQUE(email, route_key)
            );
            CREATE INDEX IF NOT EXISTS route_history_recent ON route_history(email, saved_at DESC);
        """)


def save_route_history(email: str, record: dict) -> dict:
    """Insert or update a user's route record without expiring older history."""
    now = int(time.time())
    encode = lambda value: json.dumps(value, separators=(",", ":"), allow_nan=False)
    with database() as db:
        db.execute("""
            INSERT INTO route_history
              (email, route_key, saved_at, origin_json, destination_json,
               origin_label, destination_label, city, preferences_json, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email, route_key) DO UPDATE SET
              saved_at=excluded.saved_at, origin_json=excluded.origin_json,
              destination_json=excluded.destination_json,
              origin_label=excluded.origin_label, destination_label=excluded.destination_label,
              city=excluded.city, preferences_json=excluded.preferences_json,
              metrics_json=excluded.metrics_json
        """, (email, record["route_key"], now, encode(record["origin"]),
              encode(record["destination"]), record["origin_label"],
              record["destination_label"], record["city"],
              encode(record["preferences"]), encode(record["metrics"])))
        row = db.execute("SELECT id, saved_at FROM route_history WHERE email=? AND route_key=?",
                         (email, record["route_key"])).fetchone()
    return {"id": int(row["id"]), "saved_at": int(row["saved_at"])}


def get_route_history(email: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Return only this account's newest saved walks (no automatic deletion)."""
    with database() as db:
        rows = db.execute("""
            SELECT id, saved_at, origin_json, destination_json, origin_label,
                   destination_label, city, preferences_json, metrics_json
            FROM route_history WHERE email=? ORDER BY saved_at DESC, id DESC LIMIT ? OFFSET ?
        """, (email, max(1, min(int(limit), 100)), max(0, int(offset)))).fetchall()
    return [{"id": int(row["id"]), "saved_at": int(row["saved_at"]),
             "origin": json.loads(row["origin_json"]),
             "destination": json.loads(row["destination_json"]),
             "origin_label": row["origin_label"],
             "destination_label": row["destination_label"], "city": row["city"],
             "preferences": json.loads(row["preferences_json"]),
             "metrics": json.loads(row["metrics_json"])} for row in rows]


def normalize_email(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Enter a valid email address.")
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise ValueError("Enter a valid email address.")
    return email


def register(email_value: object, password: object) -> str:
    email = normalize_email(email_value)
    if not isinstance(password, str) or len(password) < 10 or len(password) > 256:
        raise ValueError("Use a password between 10 and 256 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    try:
        with database() as db:
            db.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                       (email, salt, digest, int(time.time())))
    except sqlite3.IntegrityError as exc:
        raise LookupError("An account with this email already exists. Sign in instead.") from exc
    return email


def authenticate(email_value: object, password: object) -> str:
    email = normalize_email(email_value)
    if not isinstance(password, str) or len(password) > 256:
        raise PermissionError("Email or password is incorrect.")
    with database() as db:
        row = db.execute("SELECT password_salt, password_hash FROM users WHERE email = ?",
                         (email,)).fetchone()
    if row is None:
        # Do a comparable hash operation to reduce account enumeration timing.
        hashlib.pbkdf2_hmac("sha256", str(password).encode(), b"coolroute-dummy-salt",
                            PBKDF2_ROUNDS)
        raise PermissionError("Email or password is incorrect.")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                    row["password_salt"], PBKDF2_ROUNDS)
    if not hmac.compare_digest(candidate, row["password_hash"]):
        raise PermissionError("Email or password is incorrect.")
    return email


def new_session(email: str) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    expires = int(time.time()) + SESSION_SECONDS
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with database() as db:
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
        db.execute("INSERT INTO sessions VALUES (?, ?, ?)", (token_hash, email, expires))
    return token, expires


def session_email(token: str | None) -> str | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with database() as db:
        row = db.execute("SELECT email, expires_at FROM sessions WHERE token_hash = ?",
                         (token_hash,)).fetchone()
        if row is None:
            return None
        if row["expires_at"] <= int(time.time()):
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            return None
        return str(row["email"])


def delete_session(token: str | None) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with database() as db:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
