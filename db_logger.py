import sqlite3
import os
import time

DB_PATH = "/data/license_manager.db"


class DBLogger:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client TEXT,
                    timestamp INTEGER,
                    service TEXT,
                    "order" TEXT,
                    user TEXT,
                    filename TEXT,
                    words INTEGER,
                    tariff REAL,
                    amount REAL,
                    balance REAL
                )
            """)
            conn.commit()

    def log(self, client, service, order="", user="", filename="", words=0, tariff=0, amount=0, balance=0):
        timestamp = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO transactions (client, timestamp, service, "order", user, filename, words, tariff, amount, balance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (client, timestamp, service, order, user, filename, words, tariff, amount, balance))
            conn.commit()

    def reset(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM transactions")
            conn.commit()

    def history(self, client):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM transactions WHERE client = ? ORDER BY timestamp DESC", (client,))
            cols = [desc[0] for desc in c.description]
            return [dict(zip(cols, row)) for row in c.fetchall()]

    def all_logs(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM transactions ORDER BY timestamp DESC")
            cols = [desc[0] for desc in c.description]
            return [dict(zip(cols, row)) for row in c.fetchall()]