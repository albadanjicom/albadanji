import sqlite3, json, os

DB_PATH = r'C:\Users\Z640\Desktop\MRnewsletter\data\newsletter.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('Tables:', [t[0] for t in tables])

c.execute("SELECT date(scraped_at) as day, COUNT(*) as cnt FROM postings WHERE date(scraped_at) >= '2026-04-05' AND is_active=1 GROUP BY day ORDER BY day DESC")
rows = c.fetchall()
total = 0
for r in rows:
    print(f'  {r[0]}: {r[1]}건')
    total += r[1]
print(f'  합계: {total}건')
conn.close()
