from abc import ABC, abstractmethod
from datetime import timedelta, datetime
from typing import List, Tuple, AnyStr
import sqlite3
import os


class DataStore(ABC):
    @abstractmethod
    def connect(self):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def finds(self, table_name, **criteria):
        raise (NotImplementedError("Subclasses must implement this method."))

    @abstractmethod
    async def save_review(self, request_id: str, url: str, location: str, reviewer: str, content: str):
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def delete_reviews(self):
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
        self.connection = None
        self.__new = True
        if os.path.exists(self.db_path):
            self.__new = False

    async def connect(self):
        with self.__get_connection() as connection:
            connection.row_factory = sqlite3.Row

        if self.__new:
            await self.__create_database()

    def __get_connection(self):
        conn = sqlite3.connect(self.db_path)
        return conn

    def __commit(self):
        with self.__get_connection() as connection:
            connection.commit()

    async def execute_query(self, query):
        with self.__get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query)
            return cursor

    async def close(self):
        self.connection.close()

    async def __create_database(self):
        await self.execute_query('''
            CREATE TABLE Review (
                id INTEGER PRIMARY KEY,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                request_id TEXT NOT NULL,
                url TEXT NOT NULL,
                location TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                content TEXT NOT NULL
            )
        ''')

        self.__commit()

    async def finds(self, table_name: str, **criteria):
        query = f'SELECT * FROM "{table_name}" '

        if len(criteria) > 0:
            query += 'WHERE '

        for key, value in criteria.items():
            query += f'"{key}" = {'\'' + value + '\'' if isinstance(value, str) else value} AND '
        # Remove the trailing "AND" from the query
        query = query.rstrip("AND ")
        # query += f' ORDER BY "updated_at" DESC'
        cursor = await self.execute_query(query)
        records = cursor.fetchall()

        return records

    async def save_review(self, request_id: str, url: str, location: str, reviewer: str, content: str):
        query = (
            f'INSERT INTO Review(request_id, url, location, reviewer, content) '
            f'VALUES ("{request_id}", "{url}", "{location}", "{reviewer}", "{content}")'
        )

        cursor = await self.execute_query(query)
        self.__commit()
        return cursor.lastrowid

    async def get_reviews(self, request_id: str) -> List[Tuple]:
        reviews = await self.finds('Review', request_id=request_id)
        columns_to_remove = [0, 1, 2]
        return [tuple(value for index, value in enumerate(row) if index not in columns_to_remove) for row in
                reviews]

    async def count_by_request_id(self, request_id: str) -> int:
        query = f'SELECT COUNT(*) FROM Review WHERE request_id={request_id}'
        cursor = await self.execute_query(query)

        count = cursor.fetchone()[0]
        return count

    async def count_by_url(self, url: str) -> List[Tuple]:
        query = f'SELECT COUNT(*) FROM Review WHERE url={url}'
        cursor = await self.execute_query(query)

        count = cursor.fetchone()[0]
        return count

    async def delete_reviews(self, ):
        specific_date = datetime.now() - timedelta(days=3)
        specific_date_str = specific_date.strftime('%Y-%m-%d')
        query = f"DELETE FROM Review WHERE DATE(updated_at) < DATE('{specific_date_str}')"
        cursor = await self.execute_query(query)
        records = cursor.fetchall()

        return records