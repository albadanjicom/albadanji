import sqlite3
import os

db_path = os.path.join("data", "newsletter.db")
conn = sqlite3.connect(db_path)
conn.execute("UPDATE postings SET source_url = replace(source_url, 'https://cafe.naver.com/', 'https://m.cafe.naver.com/')")
conn.commit()
conn.close()
print("Database updated!")
