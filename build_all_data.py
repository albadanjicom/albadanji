"""
build_all_data.py
DB에서 2026-04-05 이후 전체 공고를 뽑아 newsletter-website/all_data.js 생성
매일 run_daily.bat 실행 시 newsletter_builder.py와 함께 호출되도록 newsletter_builder.py에도 추가 예정
"""
import sqlite3
import json
import os
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(PROJECT_ROOT, "data", "newsletter.db")
WEBSITE_DIR  = os.path.join(PROJECT_ROOT, "newsletter-website")
OUTPUT_PATH  = os.path.join(WEBSITE_DIR, "all_data.js")
START_DATE   = "2026-04-05"   # 수집 시작일

def build_all_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT id, title, source, source_url,
               target_age, target_gender, target_condition,
               date, time, duration, reward, location,
               type, scraped_at, is_active, url_hash
        FROM postings
        WHERE date(scraped_at) >= ?
          AND is_active = 1
        ORDER BY scraped_at DESC
    """, (START_DATE,))
    rows = c.fetchall()
    conn.close()

    postings = [dict(r) for r in rows]

    output = {
        "generated_at": datetime.now().isoformat(),
        "start_date": START_DATE,
        "count": len(postings),
        "postings": postings,
    }

    js_content = f"window.allPostingsData = {json.dumps(output, ensure_ascii=False, indent=2)};\n"
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"[all_data.js] {len(postings)}건 저장 완료 → {OUTPUT_PATH}")
    return len(postings)

if __name__ == "__main__":
    build_all_data()
