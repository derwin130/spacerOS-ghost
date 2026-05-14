import sqlite3
from datetime import datetime

DB_NAME = "ghost.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        op_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        op_type TEXT NOT NULL,
        location TEXT NOT NULL,
        risk TEXT NOT NULL,
        status TEXT NOT NULL,
        departure_time TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id INTEGER NOT NULL,
        discord_id TEXT NOT NULL,
        discord_name TEXT NOT NULL,
        role TEXT NOT NULL,
        ready INTEGER DEFAULT 0,
        joined_at TEXT NOT NULL,
        UNIQUE(operation_id, discord_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dispatch_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        author TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def create_operation(op_code, name, op_type, location, risk, departure_time, created_by):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO operations
    (op_code, name, op_type, location, risk, status, departure_time, created_by, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        op_code,
        name,
        op_type,
        location,
        risk,
        "BOARDING",
        departure_time,
        created_by,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def get_operation_by_code(op_code):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM operations
    WHERE op_code = ?
    """, (op_code.upper(),))

    operation = cursor.fetchone()

    conn.close()
    return operation


def get_active_operations():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM operations
    WHERE status != 'CLOSED'
    ORDER BY created_at DESC
    """)

    operations = cursor.fetchall()

    conn.close()
    return operations


def join_operation(operation_id, discord_id, discord_name, role):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO participants
    (operation_id, discord_id, discord_name, role, ready, joined_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        operation_id,
        discord_id,
        discord_name,
        role,
        0,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def mark_ready(operation_id, discord_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE participants
    SET ready = 1
    WHERE operation_id = ? AND discord_id = ?
    """, (operation_id, discord_id))

    updated = cursor.rowcount

    conn.commit()
    conn.close()

    return updated > 0


def get_participants(operation_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT discord_name, role, ready
    FROM participants
    WHERE operation_id = ?
    ORDER BY joined_at ASC
    """, (operation_id,))

    participants = cursor.fetchall()

    conn.close()
    return participants


def add_dispatch(operation_id, message, author):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO dispatch_logs
    (operation_id, message, author, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        operation_id,
        message,
        author,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def close_operation(operation_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE operations
    SET status = 'CLOSED'
    WHERE id = ?
    """, (operation_id,))

    conn.commit()
    conn.close()
