from abc import ABC, abstractmethod
from typing import List, Tuple
import sqlite3
import os


class DataStore(ABC):
    @abstractmethod
    def _init_db(self):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def save_review(self, request_id: str, url: str, location: str, reviewer: str, content: str):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def get_reviews(self, request_id: str) -> List[Tuple]:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def count_by_url(self, request_id: str) -> int:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def count_by_request_id(self, request_id: str) -> int:
        raise NotImplementedError("Subclasses must implement this method.")


class SQLite(DataStore):
    def __init__(self, db_path: str = 'reviews.db'):
        self.db_path = db_path
        self.conn = None
        self.get_db_connection()
        self._init_db()

    def get_db_connection(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self.conn

    def _init_db(self):
        if os.path.exists(self.db_path):
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE Review (
                id INTEGER PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                request_id TEXT NOT NULL,
                url TEXT NOT NULL,
                location TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                content TEXT NOT NULL
            )
        ''')
        conn.commit()

    async def save_review(self, request_id: str, url: str, location: str, reviewer: str, content: str):
        conn = self.get_db_connection()
        c = conn.cursor()
        query = "INSERT INTO Review(request_id, url, location, reviewer, content) VALUES (?, ?, ?, ?, ?)"
        c.execute(query, (request_id, url, location, reviewer, content))
        conn.commit()

    async def get_reviews(self, request_id: str) -> List[Tuple]:
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM Review WHERE request_id=?", (request_id,))
        reviews = [row for row in c.fetchall()]
        conn.close()
        return reviews

    async def count_by_request_id(self, request_id: str) -> int:
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM Review WHERE request_id=?", (request_id,))
        count = c.fetchone()[0]
        return count

    async def count_by_url(self, url: str) -> List[Tuple]:
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM Review WHERE url=?", (url,))
        count = c.fetchone()[0]
        return count
