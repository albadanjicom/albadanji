"""
각 날짜별 JSON 캐시를 DB에서 최신 데이터로 재생성 후 빌드
"""
import sys
import os
import sqlite3
import json

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "execution"))

DB_PATH = os.path.join(PROJECT_ROOT, "data", "newsletter.db")
SCRAPED_DATA_DIR = os.path.join(PROJECT_ROOT, ".tmp", "scraped_data")

def rebuild_json_from_db(date_str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT * FROM postings
        WHERE date(scraped_at) = ? AND is_active = 1
        ORDER BY scraped_at DESC
    """, (date_str,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    
    json_path = os.path.join(SCRAPED_DATA_DIR, f"{date_str}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"[{date_str}] JSON rebuilt: {len(rows)}건 → {json_path}")
    return len(rows)

from newsletter_builder import build_all

for date_str in ["2026-04-05", "2026-04-06", "2026-04-07", "2026-04-08", "2026-04-09"]:
    count = rebuild_json_from_db(date_str)
    print(f"\n--- Building {date_str} ({count}건) ---")
    build_all(date_str)
    print()
