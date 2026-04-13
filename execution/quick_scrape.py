"""최근 일주일치 데이터만 수집하는 스크립트 (3개 신규 소스 전용)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import (
    NaverCafeScraper, DaumCafeScraper, HankookRandomScraper,
    PanelPowerScraper, BaseScraper, save_to_db, save_to_json,
    deduplicate_postings
)
from datetime import datetime

print("=" * 60)
print(f"[Quick Scrape] 신규 소스 수집 시작: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 60)

all_postings = []

# 1) 엠브레인 패널파워
try:
    print("\n[1/4] 엠브레인 패널파워...")
    pp = PanelPowerScraper()
    r = pp.scrape()
    all_postings.extend(r)
except Exception as e:
    print(f"  ERROR: {e}")

# 2) 네이버 카페
try:
    print("\n[2/4] 네이버 카페 (togetheralba)...")
    nc = NaverCafeScraper()
    r = nc.scrape()
    all_postings.extend(r)
except Exception as e:
    print(f"  ERROR: {e}")

# 3) 다음 카페
try:
    print("\n[3/4] 다음 카페 (sk77lee)...")
    dc = DaumCafeScraper()
    r = dc.scrape()
    all_postings.extend(r)
except Exception as e:
    print(f"  ERROR: {e}")

# 4) 한국리서치 초대설문 (ID 630~660)
try:
    print("\n[4/4] 한국리서치 초대설문 (ID 630~660 탐색)...")
    hr = HankookRandomScraper()
    r = hr.scrape()
    all_postings.extend(r)
except Exception as e:
    print(f"  ERROR: {e}")

# Selenium 정리
BaseScraper.quit_driver()

# 중복 제거 및 저장
all_postings = deduplicate_postings(all_postings)

print(f"\n{'=' * 60}")
print(f"수집 완료: 총 {len(all_postings)}개")

if all_postings:
    new_count, total = save_to_db(all_postings)
    save_to_json(all_postings)
    print(f"  → DB 신규 저장: {new_count}개 / 전체: {total}개")
    
    for p in all_postings:
        print(f"  [{p['source']}] {p['title'][:50]}")
else:
    print("  → 수집된 공고가 없습니다.")

print("=" * 60)
