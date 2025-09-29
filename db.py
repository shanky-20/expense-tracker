# db.py
import sqlite3
import os
from typing import List, Tuple, Optional

BASE_DIR = os.path.dirname(__file__)
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "expenses.db")

CREATE_BOOKS_TABLE = """
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT,
    subtitle TEXT,
    authors TEXT,
    publisher TEXT,
    published_date TEXT,
    category TEXT,
    distribution_expense REAL
);
"""

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(CREATE_BOOKS_TABLE)
    conn.commit()
    conn.close()

def upsert_book(book: Tuple):
    """
    book: (id, title, subtitle, authors, publisher, published_date, category, distribution_expense)
    Uses INSERT OR REPLACE to update existing by id.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO books
        (id, title, subtitle, authors, publisher, published_date, category, distribution_expense)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, book)
    conn.commit()
    conn.close()

def fetch_all_books() -> List[Tuple]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, subtitle, authors, publisher, published_date, category, distribution_expense FROM books ORDER BY published_date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def fetch_filtered_books(keyword: Optional[str]=None, category: Optional[str]=None, publisher: Optional[str]=None) -> List[Tuple]:
    conn = get_conn()
    cur = conn.cursor()
    query = "SELECT id, title, subtitle, authors, publisher, published_date, category, distribution_expense FROM books WHERE 1=1"
    params = []
    if keyword:
        query += " AND (title LIKE ? OR subtitle LIKE ? OR authors LIKE ?)"
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)
    if publisher:
        query += " AND publisher LIKE ?"
        params.append(f"%{publisher}%")
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_book(book_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()

def delete_all_books():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM books")
    conn.commit()
    conn.close()

def get_unique_categories() -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM books WHERE category IS NOT NULL ORDER BY category")
    rows = [r[0] for r in cur.fetchall() if r[0]]
    conn.close()
    return rows
