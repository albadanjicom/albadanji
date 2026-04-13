"""
MR Newsletter -- Daily Runner
매일 자동 실행 메인 스크립트

Usage:
    py -3 execution/run_daily.py          # 전체 실행
    py -3 execution/run_daily.py --scrape  # 크롤링만
    py -3 execution/run_daily.py --build   # 빌드만
"""
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "execution"))

from scraper import run_all_scrapers
from newsletter_builder import build_all


def run_daily():
    """매일 실행 전체 파이프라인"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print(f"  MR Newsletter Daily Run")
    print(f"  Date: {date_str}")
    print(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    # Step 0: 구글 시트 웹 앱 고정 공고 동기화
    try:
        from sync_featured import sync_featured_postings
        sync_featured_postings()
    except Exception as e:
        print(f"  [Error] 고정 공고 동기화 실패: {e}")

    # Step 1: 크롤링
    print("\n[Step 1/3] Scraping...")
    postings = run_all_scrapers()
    
    # Step 2: 뉴스레터 빌드
    print("\n[Step 2/3] Building newsletter...")
    build_all(date_str)
    
    # Step 3: 이메일 발송
    print("\n[Step 3/3] Sending emails...")
    stats = {"success": 0, "fail": 0, "total": 0}
    try:
        from email_sender import send_newsletters, send_admin_report
        stats = send_newsletters(dry_run=False)
        
        # Step 4: 보고서 발송
        print("\n[Step 4/4] Sending report to admin...")
        send_admin_report(stats, len(postings))
    except Exception as e:
        print(f"  [Error] 이메일 발송 또는 보고 모듈 실패: {e}")
        
    # Step 5: 웹사이트 업데이트 (GitHub Deploy) - 사용자에 의해 비활성화됨
    print("\n[Step 5/5] Deploying website via GitHub... (Skipped)")
    # 자동 배포를 하지 않도록 요청되어 기존 git push 로직을 주석 처리/삭제했습니다.
        
    print("\n" + "=" * 60)
    print("  DAILY RUN COMPLETE!")
    print("=" * 60)
    print(f"\n  Postings collected: {len(postings)}")
    print("=" * 60)


if __name__ == "__main__":
    args = sys.argv[1:]
    
    if "--scrape" in args:
        run_all_scrapers()
    elif "--build" in args:
        build_all()
    else:
        run_daily()
