import sqlite3
import json

c = sqlite3.connect('data/newsletter.db').cursor()
rows = c.execute("SELECT title, source_url FROM postings WHERE title LIKE '%주류%' OR title LIKE '%슈팅%'").fetchall()
for r in rows:
    print(r[0])
    print(r[1])
    print("---")
