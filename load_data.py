# load_data.py
import pandas as pd
from db import init_db, upsert_book
import os

# Path to CSV - put your uploaded file here
CSV_PATH = os.path.join("data", "Books Distribution Expenses - Books.csv")

def load_csv_to_db(csv_path=CSV_PATH, limit=None):
    print("Initializing DB...")
    init_db()
    print(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    print("Rows read:", len(df))
    if limit:
        df = df.head(limit)
        print("Limiting to first", limit, "rows.")
    # Ensure expected columns exist
    expected = ["id","title","subtitle","authors","publisher","published_date","category","distribution_expense"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise RuntimeError("CSV missing columns: " + ", ".join(missing))
    inserted = 0
    for _, r in df.iterrows():
        book = (
            str(r["id"]),
            str(r["title"]),
            str(r["subtitle"]) if pd.notna(r["subtitle"]) else "",
            str(r["authors"]) if pd.notna(r["authors"]) else "",
            str(r["publisher"]) if pd.notna(r["publisher"]) else "",
            str(r["published_date"]) if pd.notna(r["published_date"]) else "",
            str(r["category"]) if pd.notna(r["category"]) else "",
            float(r["distribution_expense"]) if pd.notna(r["distribution_expense"]) else 0.0
        )
        upsert_book(book)
        inserted += 1
    print(f"Inserted/Updated {inserted} rows into database.")

if __name__ == "__main__":
    load_csv_to_db()
