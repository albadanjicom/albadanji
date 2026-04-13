"""
MR Newsletter — DB 초기화 스크립트
SQLite 데이터베이스 스키마 생성
"""
import sqlite3
import os
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "newsletter.db")


def init_database():
    """데이터베이스 및 테이블 생성"""
    # data 디렉토리 확인
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 구독자 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'unsubscribed')),
            source TEXT DEFAULT 'manual' CHECK(source IN ('manual', 'website', 'referral', 'excel_import'))
        )
    """)

    # 수집 공고 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS postings (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT UNIQUE NOT NULL,
            target_age TEXT,
            target_gender TEXT,
            target_condition TEXT,
            date TEXT,
            time TEXT,
            duration TEXT,
            reward TEXT,
            location TEXT,
            type TEXT CHECK(type IN (
                '좌담회', '설문조사', '맛테스트', '인터뷰', 
                '온라인', '유치조사', '패널모집', '기타'
            )),
            raw_content TEXT,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            url_hash TEXT UNIQUE
        )
    """)

    # 뉴스레터 발행 로그 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS newsletters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            publish_date TEXT NOT NULL,
            total_postings INTEGER DEFAULT 0,
            web_html_path TEXT,
            email_html_path TEXT,
            sent_manually BOOLEAN DEFAULT 0,
            sent_at DATETIME
        )
    """)

    # 크롤링 실행 로그 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME,
            new_postings INTEGER DEFAULT 0,
            total_scraped INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running' CHECK(status IN ('running', 'success', 'failed')),
            error_message TEXT
        )
    """)

    # 인덱스 생성
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_postings_source ON postings(source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_postings_date ON postings(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_postings_active ON postings(is_active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_postings_scraped ON postings(scraped_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscribers_status ON subscribers(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_newsletters_date ON newsletters(publish_date)")

    conn.commit()
    conn.close()

    print(f"[OK] Database initialized: {DB_PATH}")
    return DB_PATH


def get_db_stats():
    """DB 현재 상태 출력"""
    if not os.path.exists(DB_PATH):
        print("[ERROR] DB does not exist. Run init_database() first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables = ["subscribers", "postings", "newsletters", "scrape_logs"]
    print("\n[DB Status]")
    print("-" * 40)
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count}건")
    print("-" * 40)

    conn.close()


if __name__ == "__main__":
    if "--stats" in sys.argv:
        get_db_stats()
    else:
        init_database()
        get_db_stats()
