import mysql.connector
from config import db_config


def get_connection():
    return mysql.connector.connect(**db_config)


def query(sql, params=(), one=False):
    """SELECT: ibinabalik ang listahan ng dict (o isang dict kapag one=True)."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        conn.close()


def execute(sql, params=()):
    """INSERT/UPDATE/DELETE: ibinabalik ang id ng bagong row."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()