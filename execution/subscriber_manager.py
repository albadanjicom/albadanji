"""
MR Newsletter -- Subscriber Manager
구독자 관리 (Excel import, 추가, 삭제, 조회)
"""
import os
import sqlite3
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "newsletter.db")


def import_from_excel(filepath: str) -> int:
    """Excel 파일에서 구독자 이메일 가져오기"""
    try:
        import openpyxl
    except ImportError:
        print("[ERROR] openpyxl not installed. Run: pip install openpyxl")
        return 0

    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return 0

    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    imported = 0

    for row in ws.iter_rows(min_row=1, values_only=True):
        for cell in row:
            if cell and isinstance(cell, str) and "@" in cell:
                email = cell.strip().lower()
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO subscribers (email, source, status)
                        VALUES (?, 'excel_import', 'active')
                    """, (email,))
                    if cursor.rowcount > 0:
                        imported += 1
                except Exception as e:
                    print(f"  [WARN] Skipped {email}: {e}")

    conn.commit()
    conn.close()
    wb.close()

    print(f"[Import] {imported} new subscribers imported from {filepath}")
    return imported


def import_from_csv(filepath: str) -> int:
    """CSV 파일에서 구독자 이메일 가져오기"""
    import csv

    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    imported = 0

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            for cell in row:
                if cell and "@" in cell:
                    email = cell.strip().lower()
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO subscribers (email, source, status)
                            VALUES (?, 'excel_import', 'active')
                        """, (email,))
                        if cursor.rowcount > 0:
                            imported += 1
                    except Exception:
                        pass

    conn.commit()
    conn.close()

    print(f"[Import] {imported} new subscribers imported from {filepath}")
    return imported


def add_subscriber(email: str, source: str = "manual") -> bool:
    """구독자 추가"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO subscribers (email, source, status)
            VALUES (?, ?, 'active')
        """, (email.strip().lower(), source))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        if success:
            print(f"[+] Subscriber added: {email}")
        else:
            print(f"[=] Already exists: {email}")
        return success
    except Exception as e:
        print(f"[ERROR] {e}")
        conn.close()
        return False


def unsubscribe(email: str) -> bool:
    """구독 취소"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE subscribers SET status = 'unsubscribed' 
        WHERE email = ? AND status = 'active'
    """, (email.strip().lower(),))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    if success:
        print(f"[-] Unsubscribed: {email}")
    else:
        print(f"[?] Not found or already unsubscribed: {email}")
    return success


def list_subscribers(status: str = "active") -> list[dict]:
    """구독자 목록 조회"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM subscribers WHERE status = ? ORDER BY subscribed_at DESC
    """, (status,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_active_emails() -> list[str]:
    """활성 구독자 이메일만 반환 (발송용)"""
    subs = list_subscribers("active")
    return [s["email"] for s in subs]


def get_stats() -> dict:
    """구독자 통계"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM subscribers WHERE status = 'active'")
    active = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM subscribers WHERE status = 'unsubscribed'")
    unsub = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM subscribers")
    total = cursor.fetchone()[0]
    
    conn.close()
    return {"active": active, "unsubscribed": unsub, "total": total}


def export_emails(filepath: str = None) -> str:
    """활성 구독자 이메일을 파일로 내보내기 (Gmail BCC용)"""
    emails = get_active_emails()
    
    if not filepath:
        filepath = os.path.join(PROJECT_ROOT, "output", "subscribers_emails.txt")
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Gmail BCC에 바로 붙여넣을 수 있는 형식
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(", ".join(emails))
    
    print(f"[Export] {len(emails)} emails exported to {filepath}")
    print(f"  (Copy the content and paste into Gmail BCC field)")
    return filepath


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  py -3 subscriber_manager.py import <excel_or_csv_file>")
        print("  py -3 subscriber_manager.py add <email>")
        print("  py -3 subscriber_manager.py unsub <email>")
        print("  py -3 subscriber_manager.py list")
        print("  py -3 subscriber_manager.py stats")
        print("  py -3 subscriber_manager.py export")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "import" and len(sys.argv) > 2:
        filepath = sys.argv[2]
        if filepath.endswith((".xlsx", ".xls")):
            import_from_excel(filepath)
        elif filepath.endswith(".csv"):
            import_from_csv(filepath)
        else:
            print("[ERROR] Supported formats: .xlsx, .xls, .csv")
    elif cmd == "add" and len(sys.argv) > 2:
        add_subscriber(sys.argv[2])
    elif cmd == "unsub" and len(sys.argv) > 2:
        unsubscribe(sys.argv[2])
    elif cmd == "list":
        subs = list_subscribers()
        for s in subs:
            print(f"  {s['email']} | {s['source']} | {s['subscribed_at']}")
        print(f"\n  Total active: {len(subs)}")
    elif cmd == "stats":
        stats = get_stats()
        print(f"\n[Subscriber Stats]")
        print(f"  Active:       {stats['active']}")
        print(f"  Unsubscribed: {stats['unsubscribed']}")
        print(f"  Total:        {stats['total']}")
    elif cmd == "export":
        export_emails()
    else:
        print("[ERROR] Unknown command")
