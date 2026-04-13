"""
MR Newsletter -- Web Scraper
각 소스별 크롤러 클래스 (전략 패턴)
"""
import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 프로젝트 루트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "newsletter.db")
SCRAPED_DATA_DIR = os.path.join(PROJECT_ROOT, ".tmp", "scraped_data")

# 공통 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def url_hash(url: str) -> str:
    """URL을 해시하여 고유 ID 생성"""
    return hashlib.md5(url.strip().encode("utf-8")).hexdigest()


def normalize_title(title: str) -> str:
    """공고 제목 정규화 (중복 비교용)"""
    title = re.sub(r"\[.*?\]", "", title)       # [재공지] 등 제거
    title = re.sub(r"\(.*?\)", "", title)       # (소괄호 내용) 제거
    title = re.sub(r"\s+", " ", title).strip()  # 공백 정규화
    return title


# =============================================================================
#  Base Scraper
# =============================================================================
class BaseScraper(ABC):
    """크롤러 기본 클래스"""

    name: str = "base"
    base_url: str = ""
    _shared_driver = None

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.results = []

    @classmethod
    def get_driver(cls):
        """싱글톤 패턴으로 Headless Chrome WebDriver 반환"""
        if cls._shared_driver is None:
            profile_dir = os.path.join(PROJECT_ROOT, ".tmp", "chrome_profile")
            os.makedirs(profile_dir, exist_ok=True)
            
            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
            cls._shared_driver = webdriver.Chrome(options=options)
            cls._shared_driver.implicitly_wait(5)
            
            # Load stored cookies via JSON to bypass profile locking
            cookie_file = os.path.join(PROJECT_ROOT, ".tmp", "naver_cookies.json")
            if os.path.exists(cookie_file):
                try:
                    cls._shared_driver.get("https://www.naver.com")
                    time.sleep(1)
                    with open(cookie_file, "r", encoding="utf-8") as f:
                        cookies = json.load(f)
                    for c in cookies:
                        for key in ["sameSite", "httpOnly", "expiry", "staleAt"]:
                            c.pop(key, None)
                        try:
                            cls._shared_driver.add_cookie(c)
                        except: pass
                except Exception as e:
                    print(f"  [Driver] Cookie load failed: {e}")
        return cls._shared_driver

    @classmethod
    def quit_driver(cls):
        """WebDriver 종료"""
        if cls._shared_driver:
            try:
                cls._shared_driver.quit()
            except: pass
            cls._shared_driver = None

    @abstractmethod
    def scrape(self) -> list[dict]:
        """크롤링 실행. 공고 리스트 반환."""
        pass

    def fetch(self, url: str, **kwargs) -> BeautifulSoup | None:
        """URL에서 HTML을 가져와 BeautifulSoup 객체 반환"""
        try:
            resp = self.session.get(url, timeout=15, **kwargs)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            print(f"  [WARN] {self.name}: Failed to fetch {url} -- {e}")
            return None

    def make_posting(self, **kwargs) -> dict:
        """공고 딕셔너리 생성"""
        source_url = kwargs.get("source_url", "")
        return {
            "id": url_hash(source_url),
            "title": kwargs.get("title", "").strip(),
            "source": self.name,
            "source_url": source_url.strip(),
            "target_age": kwargs.get("target_age", ""),
            "target_gender": kwargs.get("target_gender", ""),
            "target_condition": kwargs.get("target_condition", ""),
            "date": kwargs.get("date", ""),
            "time": kwargs.get("time", ""),
            "duration": kwargs.get("duration", ""),
            "reward": kwargs.get("reward", ""),
            "location": kwargs.get("location", ""),
            "type": kwargs.get("type", ""),
            "raw_content": kwargs.get("raw_content", ""),
            "scraped_at": datetime.now().isoformat(),
            "is_active": True,
            "url_hash": url_hash(source_url),
        }


# =============================================================================
#  1. AlbabankScraper  (albabank.pe.kr)
# =============================================================================
class AlbabankScraper(BaseScraper):
    name = "albabank"
    base_url = "https://albabank.pe.kr/category/fgd/"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        # 메인 페이지 + 재공지 페이지
        urls = [
            self.base_url,
            "https://albabank.pe.kr/category/refgd/",
        ]

        for page_url in urls:
            soup = self.fetch(page_url)
            if not soup:
                continue

            articles = soup.select("article") or soup.select(".post")
            if not articles:
                # fallback: h4 태그로 찾기
                for h4 in soup.select("h4"):
                    link = h4.find("a")
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    if not href or not title:
                        continue

                    # 상세 페이지에서 내용 가져오기
                    detail = self._parse_detail(href)
                    posting = self.make_posting(
                        title=title,
                        source_url=href,
                        raw_content=detail.get("raw_content", ""),
                        type=self._guess_type(title),
                        **{k: v for k, v in detail.items() if k != "raw_content"},
                    )
                    results.append(posting)
            else:
                for article in articles:
                    # 제목 링크를 h2/h3/h4에서 찾기 (첫 a는 카테고리 링크일 수 있음)
                    title_el = article.find(["h2", "h3", "h4"])
                    if not title_el:
                        continue
                    link = title_el.find("a")
                    if not link:
                        link = article.find("a")
                    if not link:
                        continue
                    title = title_el.get_text(strip=True)
                    href = link.get("href", "")
                    if not href or not title:
                        continue
                    # 카테고리 링크 필터링
                    if "/category/" in href:
                        continue

                    detail = self._parse_detail(href)
                    posting = self.make_posting(
                        title=title,
                        source_url=href,
                        raw_content=detail.get("raw_content", ""),
                        type=self._guess_type(title),
                        **{k: v for k, v in detail.items() if k != "raw_content"},
                    )
                    results.append(posting)

            time.sleep(1)  # 폴라이트 크롤링

        print(f"  [{self.name}] Found {len(results)} postings")
        return results

    def _parse_detail(self, url: str) -> dict:
        """상세 페이지에서 추가 정보 파싱"""
        soup = self.fetch(url)
        if not soup:
            return {}

        content_el = (
            soup.select_one("article.single") or
            soup.select_one(".entry-content") or 
            soup.select_one("article")
        )
        if not content_el:
            return {}

        raw = content_el.get_text(separator="\n", strip=True)
        info = {"raw_content": raw[:2000]}

        # *를 줄바꿈으로 치환하여 각 필드를 분리 (albabank 패턴)
        normalized = raw.replace("*", "\n")

        # 사례비 추출 (정확한 필드명 매칭 우선)
        reward_match = re.search(r"(사례비|참석비|참여비|보상)\s*[:：]\s*(.+)", normalized)
        if reward_match:
            info["reward"] = reward_match.group(2).strip()

        # 소요시간 추출
        duration_match = re.search(r"소요\s*시간\s*[:：]\s*(.+)", normalized)
        if duration_match:
            info["duration"] = duration_match.group(1).strip()

        # 장소 추출
        loc_match = re.search(r"(장소|위치)\s*[:：]\s*(.+)", normalized)
        if loc_match:
            info["location"] = loc_match.group(2).strip()

        # 대상 추출
        target_match = re.search(r"(대상\s*조건|대상|조건)\s*[:：\-]\s*(.+)", normalized)
        if target_match:
            target_text = target_match.group(2).strip()
            info["target_condition"] = target_text
            # 성별
            if "여성" in target_text and "남" not in target_text:
                info["target_gender"] = "여성"
            elif "남성" in target_text and "여" not in target_text:
                info["target_gender"] = "남성"
            elif "남녀" in target_text or "남여" in target_text:
                info["target_gender"] = "남녀"
            # 연령
            age_match = re.search(r"(만?\s*\d+[~\-]\s*\d+세)", target_text)
            if age_match:
                info["target_age"] = age_match.group(1)
            else:
                age_match2 = re.search(r"(\d+세)", target_text)
                if age_match2:
                    info["target_age"] = age_match2.group(1)

        # 일정 추출
        date_match = re.search(r"(일정|날짜|일시|조사\s*기간|조사\s*일자)\s*[:：]\s*(.+)", normalized)
        if date_match:
            info["date"] = date_match.group(2).strip()

        # 시간 추출
        time_match = re.search(r"(시간|진행\s*시간)\s*[:：]\s*(.+)", normalized)
        if time_match and "소요" not in time_match.group(0):
            info["time"] = time_match.group(2).strip()

        time.sleep(0.5)
        return info

    def _guess_type(self, title: str) -> str:
        """제목에서 공고 유형 추측"""
        title_lower = title.lower()
        if "좌담회" in title_lower or "fgd" in title_lower:
            return "좌담회"
        if "맛테스트" in title_lower or "맛 테스트" in title_lower or "갱조사" in title_lower:
            return "맛테스트"
        if "인터뷰" in title_lower:
            return "인터뷰"
        if "설문" in title_lower or "온라인" in title_lower or "다이어리" in title_lower:
            return "온라인"
        if "유치" in title_lower:
            return "유치조사"
        if "패널" in title_lower:
            return "패널모집"
        return "기타"


# =============================================================================
#  2. PanelPowerScraper  (panel.co.kr) -- 엠브레인, API 기반 수집
# =============================================================================
class PanelPowerScraper(BaseScraper):
    name = "panelpower"
    base_url = "https://www.panel.co.kr"
    api_url = "https://www.panel.co.kr/user/survey/offline/getSurveyOfflineList"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url} via API")
        results = []
        surveys = None

        # 방법 1: 직접 API 호출 (Content-Type: application/json 필수)
        try:
            api_headers = {**HEADERS, "Content-Type": "application/json"}
            resp = requests.post(self.api_url, headers=api_headers, json={}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                surveys = data if isinstance(data, list) else data.get("list", data.get("data", data.get("result", [])))
        except: pass

        # 방법 2: Selenium으로 페이지 로드 후 JavaScript로 API 호출
        if not surveys or not isinstance(surveys, list):
            try:
                driver = self.get_driver()
                driver.get(f"{self.base_url}/user/survey/offline/list")
                time.sleep(5)
                json_str = driver.execute_script("""
                    var xhr = new XMLHttpRequest();
                    xhr.open('POST', '/user/survey/offline/getSurveyOfflineList', false);
                    xhr.setRequestHeader('Content-Type', 'application/json');
                    xhr.send('{}');
                    return xhr.responseText;
                """)
                if json_str:
                    import json
                    data = json.loads(json_str)
                    surveys = data if isinstance(data, list) else data.get("list", data.get("data", data.get("result", [])))
            except: pass

        if surveys and isinstance(surveys, list):
            for s in surveys:
                srv_no = str(s.get("srvNo", s.get("surveyNo", s.get("id", ""))))
                title = s.get("srvNm", s.get("surveyName", s.get("title", "")))
                if not title: continue
                
                detail_url = f"{self.base_url}/user/survey/offline/detail/{srv_no}" if srv_no else f"{self.base_url}/user/survey/offline/list"
                
                date_str = ""
                sta = s.get("srvStaDt", s.get("startDate", ""))
                end = s.get("srvEndDt", s.get("endDate", ""))
                if sta and end:
                    date_str = f"{sta} ~ {end}"
                elif sta:
                    date_str = sta
                
                reward = s.get("minResPayVal", s.get("reward", ""))
                if reward:
                    reward = f"{int(reward):,}원" if str(reward).isdigit() else str(reward)
                
                location = s.get("location", s.get("place", ""))
                duration = s.get("reqreTime", s.get("duration", ""))
                target = s.get("tgtDesc", s.get("target", ""))
                target_gender = ""
                target_age = ""
                if target:
                    if "여성" in target and "남" not in target: target_gender = "여성"
                    elif "남성" in target and "여" not in target: target_gender = "남성"
                    elif "남녀" in target: target_gender = "남녀"
                    age_m = re.search(r'(만?\s*\d+\s*세?\s*이상|만?\s*\d+[~\-]\s*\d+\s*세|\d+대)', target)
                    if age_m: target_age = age_m.group(1)
                
                posting = self.make_posting(
                    title=title,
                    source_url=detail_url,
                    type="좌담회",
                    date=date_str,
                    reward=str(reward),
                    location=str(location),
                    duration=str(duration),
                    target_condition=str(target),
                    target_age=target_age,
                    target_gender=target_gender,
                )
                results.append(posting)
            print(f"  [{self.name}] API returned {len(results)} surveys")
        else:
            print(f"  [{self.name}] API unavailable, using Selenium fallback")
            results = self._selenium_fallback()

        print(f"  [{self.name}] Found {len(results)} postings")
        return results

    def _selenium_fallback(self) -> list[dict]:
        results = []
        driver = self.get_driver()
        try:
            driver.get(f"{self.base_url}/user/survey/offline/list")
            time.sleep(5)
            
            # 제목 목록 수집
            body_text = driver.find_element(By.TAG_NAME, "body").text
            titles = []
            lines = [l.strip() for l in body_text.split("\n") if len(l.strip()) > 10]
            for line in lines:
                if any(kw in line for kw in ["좌담회", "인터뷰", "조사", "설문", "FGD", "테스트"]):
                    titles.append(line[:80])
            
            print(f"  [{self.name}] Found {len(titles)} titles, clicking through for details...")
            
            for title in titles:
                try:
                    # 목록 페이지로 돌아가기
                    driver.get(f"{self.base_url}/user/survey/offline/list")
                    time.sleep(3)
                    
                    # 제목 텍스트로 클릭 가능한 요소 찾기
                    try:
                        elem = driver.find_element(By.XPATH, f"//a[contains(text(), '{title[:20]}')]")
                    except:
                        try:
                            elem = driver.find_element(By.XPATH, f"//*[contains(text(), '{title[:20]}')]")
                        except:
                            results.append(self.make_posting(
                                title=title,
                                source_url=f"{self.base_url}/user/survey/offline/list",
                                type="좌담회",
                            ))
                            continue
                    
                    elem.click()
                    time.sleep(3)
                    
                    detail_url = driver.current_url
                    detail_text = driver.find_element(By.TAG_NAME, "body").text
                    
                    # 정보 추출 (panel.co.kr은 콜론 없이 스페이스, 또는 줄바꿈 후 값)
                    lines = detail_text.split("\n")
                    def find_val(label):
                        for i, line in enumerate(lines):
                            l = line.strip()
                            if l.startswith(label):
                                # 같은 줄: "진행일 2026.04.07 ~ 2026.04.08"
                                rest = l[len(label):].strip().lstrip(":：").strip()
                                if rest:
                                    return rest
                                # 다음 줄: "장소\n방배동 엠브레인 본사"
                                if i + 1 < len(lines) and lines[i+1].strip():
                                    return lines[i+1].strip()
                        return ""
                    
                    date_str = find_val("진행일") or find_val("일정")
                    reward = find_val("사례비")
                    location = find_val("장소")
                    duration = find_val("소요시간")
                    target = find_val("내용") or find_val("대상")
                    
                    posting = self.make_posting(
                        title=title,
                        source_url=detail_url,
                        type="좌담회",
                        date=date_str,
                        reward=reward,
                        location=location,
                        duration=duration,
                        target_condition=target,
                    )
                    results.append(posting)
                    print(f"    -> {title[:30]} | {date_str} | {reward} | {location}")
                    
                except Exception as e:
                    results.append(self.make_posting(
                        title=title,
                        source_url=f"{self.base_url}/user/survey/offline/list",
                        type="좌담회",
                    ))
        except Exception as e:
            print(f"  [{self.name}] Selenium fallback failed: {e}")
        return results


# =============================================================================
#  3. SurveylinkScraper  (surveylink.co.kr)
# =============================================================================
class SurveylinkScraper(BaseScraper):
    name = "surveylink"
    base_url = "https://www.surveylink.co.kr"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        # 설문 목록 페이지
        survey_urls = [
            f"{self.base_url}/survey/list",
            f"{self.base_url}/survey/",
        ]

        for survey_url in survey_urls:
            soup = self.fetch(survey_url)
            if not soup:
                continue

            # 설문 목록 파싱
            items = soup.select(".survey-item, .list-item, .board-item, tr")
            for item in items:
                link = item.find("a")
                if not link:
                    continue
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if not href or not title or len(title) < 5:
                    continue

                if not href.startswith("http"):
                    href = self.base_url + href

                posting = self.make_posting(
                    title=title,
                    source_url=href,
                    type="온라인",
                )
                results.append(posting)
            if results:
                break

        print(f"  [{self.name}] Found {len(results)} postings")
        return results


# =============================================================================
#  4. PanelNowScraper  (panelnow.co.kr)
# =============================================================================
class PanelNowScraper(BaseScraper):
    name = "panelnow"
    base_url = "https://www.panelnow.co.kr"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        soup = self.fetch(self.base_url)
        if not soup:
            return results

        # 진행 중인 설문 목록 파싱
        items = soup.select(".survey-list a, .survey-item a, .list-group-item a")
        for item in items:
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if not href or not title or len(title) < 5:
                continue
            if not href.startswith("http"):
                href = self.base_url + href

            posting = self.make_posting(
                title=title,
                source_url=href,
                type="온라인",
            )
            results.append(posting)

        print(f"  [{self.name}] Found {len(results)} postings")
        return results


# =============================================================================
#  5. ResearchiScraper  (researchi.co.kr)
# =============================================================================
class ResearchiScraper(BaseScraper):
    name = "researchi"
    base_url = "https://researchi.co.kr"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        # HTTP로 시도 (TLS 문제 우회)
        for scheme in ["https", "http"]:
            try:
                url = f"{scheme}://researchi.co.kr"
                soup = self.fetch(url, verify=False)
                if not soup:
                    continue

                items = soup.select("article, .post, .board-item, tr")
                for item in items:
                    link = item.find("a")
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    if not href or not title or len(title) < 5:
                        continue
                    if not href.startswith("http"):
                        href = url + href

                    detail = self._parse_detail(href)
                    # 유형 추측 시 제목과 본문을 함께 참고
                    combined_text = f"{title} {detail.get('raw_content', '')}"
                    
                    posting = self.make_posting(
                        title=title,
                        source_url=href,
                        type=self._guess_type(combined_text),
                        raw_content=detail.get("raw_content", ""),
                        **{k: v for k, v in detail.items() if k != "raw_content"},
                    )
                    results.append(posting)
                if results:
                    break
            except Exception as e:
                print(f"  [{self.name}] {scheme} failed: {e}")
                continue

        print(f"  [{self.name}] Found {len(results)} postings")
        return results

    def _parse_detail(self, url: str) -> dict:
        try:
            soup = self.fetch(url, verify=False)
            if not soup:
                return {}

            content_el = (
                soup.select_one(".board-view-content") or
                soup.select_one(".content") or
                soup.select_one("article") or
                soup.select_one("td")
            )
            if not content_el:
                return {}

            raw = content_el.get_text(separator="\n", strip=True)
            info = {"raw_content": raw[:2000]}
            # *는 줄바꿈으로 보되, -는 날짜 형식을 위해 유지. 특수 공백 처리.
            normalized = raw.replace("*", "\n").replace("\u200b", "").replace("\xa0", " ")

            # 정규표현식 보강: 콜론 주변 다양한 공백 처리 및 키워드 확장
            sep = r"[\s:：\-]*"
            
            reward_match = re.search(fr"(사례비|참석비|참여비|보상|사례금){sep}(.+)", normalized)
            if reward_match: info["reward"] = reward_match.group(2).strip().split('\n')[0]

            duration_match = re.search(fr"(소요\s*시간|진행\s*시간|소요){sep}(.+)", normalized)
            if duration_match: info["duration"] = duration_match.group(2).strip().split('\n')[0]

            loc_match = re.search(fr"(장소|위치|진행장소){sep}(.+)", normalized)
            if loc_match: info["location"] = loc_match.group(2).strip().split('\n')[0]

            target_match = re.search(fr"(대상\s*조건|대상|조건|참여\s*대상){sep}(.+)", normalized)
            if target_match:
                target_text = target_match.group(2).strip().split('\n')[0]
                info["target_condition"] = target_text
                if "여성" in target_text and "남" not in target_text: info["target_gender"] = "여성"
                elif "남성" in target_text and "여" not in target_text: info["target_gender"] = "남성"
                elif "남녀" in target_text or "남여" in target_text: info["target_gender"] = "남녀"
                age_match = re.search(r"(만?\s*\d+[~\-]\s*\d+세|\d+세|\d+대)", target_text)
                if age_match: info["target_age"] = age_match.group(1)

            date_match = re.search(fr"(일정|날짜|일시|조사\s*기간|조사\s*일자|진행\s*일){sep}(.+)", normalized)
            if date_match: info["date"] = date_match.group(2).strip().split('\n')[0]

            time_match = re.search(fr"(시간|진행\s*시간){sep}(.+)", normalized)
            if time_match and "소요" not in time_match.group(0): info["time"] = time_match.group(2).strip().split('\n')[0]

            time.sleep(0.5)
            return info
        except Exception:
            return {}


    def _guess_type(self, text: str) -> str:
        text_lower = text.lower()
        if "좌담회" in text_lower or "fgd" in text_lower:
            return "좌담회"
        if "맛테스트" in text_lower or "갱조사" in text_lower or "hut" in text_lower or "테스트" in text_lower:
            return "맛테스트"
        if "인터뷰" in text_lower:
            return "인터뷰"
        if "설문" in text_lower or "온라인" in text_lower:
            return "온라인"
        return "기타"


# =============================================================================
#  6. NaverCafeScraper  (togetheralba - 상세 페이지 파싱 포함)
# =============================================================================
class NaverCafeScraper(BaseScraper):
    name = "naver_cafe"
    base_url = "https://m.cafe.naver.com/togetheralba"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping Naver Cafe using Headless Chrome")
        results = []
        driver = self.get_driver()

        try:
            driver.get(self.base_url)
            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, "lxml")

            # 게시글 링크 수집
            links = []
            items = soup.select("a.mainLink")
            for item in items:
                tit_el = item.select_one("[class*='tit'], strong, .tit")
                title = tit_el.get_text(strip=True) if tit_el else item.get_text(strip=True)
                href = item.get("href", "")
                if len(title) < 3: continue
                if href.startswith("/"): href = "https://m.cafe.naver.com" + href
                elif not href.startswith("http"): href = "https://m.cafe.naver.com/" + href
                links.append((title, href))

            if not links:
                for a in soup.select("a[href*='ArticleRead'], a[href*='articleid']"):
                    title = a.get_text(strip=True)
                    href = a.get("href", "")
                    if len(title) < 3: continue
                    if href.startswith("/"): href = "https://m.cafe.naver.com" + href
                    links.append((title, href))

            print(f"  [{self.name}] {len(links)} article links found, parsing details...")

            # 각 상세 페이지 파싱
            for title, href in links:
                detail = self._parse_cafe_detail(driver, href)
                # 외부 링크(이메일, 타 웹사이트)에서 접속 시 네이버 카페 PC버전(iframe)은 종종 로그인 화면으로 튕기거나 막는 현상이 있습니다.
                # m.cafe.naver.com (모바일 웹버전)으로 연결하면 공개 카페의 경우 로그인 없이 정상적으로 내용이 보입니다.
                article_m = re.search(r'articleid=(\d+)', href)
                path_m = re.search(r'/togetheralba/(\d+)', href)
                if article_m:
                    desktop_url = f"https://m.cafe.naver.com/togetheralba/{article_m.group(1)}"
                elif path_m:
                    desktop_url = f"https://m.cafe.naver.com/togetheralba/{path_m.group(1)}"
                else:
                    desktop_url = href
                
                posting = self.make_posting(
                    title=title,
                    source_url=desktop_url,
                    type=detail.get("type", self._guess_type(title)),
                    date=detail.get("date", ""),
                    reward=detail.get("reward", ""),
                    location=detail.get("location", ""),
                    duration=detail.get("duration", ""),
                    target_condition=detail.get("target_condition", ""),
                    target_gender=detail.get("target_gender", ""),
                    target_age=detail.get("target_age", ""),
                    raw_content=detail.get("raw_content", ""),
                )
                results.append(posting)

        except Exception as e:
            print(f"  [{self.name}] Naver Cafe Scraping Failed: {e}")

        unique = {p["title"]: p for p in results}.values()
        print(f"  [{self.name}] Found {len(unique)} postings")
        return list(unique)

    def _parse_cafe_detail(self, driver, url: str) -> dict:
        """상세 페이지에서 일정/사례비/위치/대상 등 추출"""
        info = {}
        try:
            driver.get(url)
            time.sleep(2)
            body_text = driver.find_element(By.TAG_NAME, "body").text
            info["raw_content"] = body_text[:2000]
            normalized = body_text.replace("*", "\n").replace("◈", "\n").replace("◆", "\n").replace("▶", "\n")

            # 사례비
            m = re.search(r"(사\s*례\s*비|참석비|참여비|보상|사례금)\s*[:：)]\s*(.+)", normalized)
            if m: info["reward"] = m.group(2).strip().split("\n")[0]

            # 소요시간
            m = re.search(r"(소요\s*시간|진행\s*시간|소요)\s*[:：)]\s*(.+)", normalized)
            if m: info["duration"] = m.group(2).strip().split("\n")[0]

            # 위치/장소
            m = re.search(r"(위\s*치|장\s*소|진행\s*장소)\s*[:：)]\s*(.+)", normalized)
            if m: info["location"] = m.group(2).strip().split("\n")[0]

            # 일정/날짜
            m = re.search(r"(일\s*정|날\s*짜|일\s*시|조사\s*기간|조사\s*일자|진행\s*일)\s*[:：)]\s*(.+)", normalized)
            if m: info["date"] = m.group(2).strip().split("\n")[0]

            # 대상/조건
            m = re.search(r"(대\s*상\s*조\s*건|대\s*상|조\s*건|참여\s*대상)\s*[:：)]\s*(.+)", normalized)
            if m:
                target = m.group(2).strip().split("\n")[0]
                info["target_condition"] = target
                if "여성" in target and "남" not in target: info["target_gender"] = "여성"
                elif "남성" in target and "여" not in target: info["target_gender"] = "남성"
                elif "남녀" in target or "남여" in target: info["target_gender"] = "남녀"
                age_m = re.search(r"(만?\s*\d+[~\-]\s*\d+세|\d+대)", target)
                if age_m: info["target_age"] = age_m.group(1)

            # 유형 추측 (본문 기반)
            full = body_text + " "
            if "온라인" in full and "좌담회" in full: info["type"] = "좌담회"
            elif "좌담회" in full or "FGD" in full.upper(): info["type"] = "좌담회"
            elif "맛테스트" in full or "갱조사" in full or "HUT" in full.upper(): info["type"] = "맛테스트"
            elif "인터뷰" in full: info["type"] = "인터뷰"
            elif "설문" in full or "서베이" in full: info["type"] = "온라인"

        except Exception as e:
            pass
        return info

    def _guess_type(self, title: str) -> str:
        if "좌담회" in title or "FGD" in title.upper(): return "좌담회"
        if "맛테스트" in title or "갱조사" in title: return "맛테스트"
        if "인터뷰" in title: return "인터뷰"
        if "설문" in title or "서베이" in title: return "온라인"
        return "기타"

# =============================================================================
#  6.1. SK77Lee CafeScraper  (네이버 카페 sk77lee - 상세 페이지 파싱 포함)
# =============================================================================
class DaumCafeScraper(BaseScraper):
    name = "sk77lee_cafe"
    base_url = "https://m.cafe.naver.com/sk77lee"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping Naver Cafe sk77lee using Headless Chrome")
        results = []
        driver = self.get_driver()

        try:
            driver.get(self.base_url)
            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, "lxml")

            # 게시글 링크 수집
            links = []
            items = soup.select("a.mainLink")
            for item in items:
                tit_el = item.select_one("[class*='tit'], strong, .tit")
                title = tit_el.get_text(strip=True) if tit_el else item.get_text(strip=True)
                href = item.get("href", "")
                if len(title) < 3: continue
                if href.startswith("/"): href = "https://m.cafe.naver.com" + href
                elif not href.startswith("http"): href = "https://m.cafe.naver.com/" + href
                links.append((title, href))

            if not links:
                for a in soup.select("a[href*='ArticleRead'], a[href*='articleid']"):
                    title = a.get_text(strip=True)
                    href = a.get("href", "")
                    if len(title) < 3: continue
                    if href.startswith("/"): href = "https://m.cafe.naver.com" + href
                    links.append((title, href))

            print(f"  [{self.name}] {len(links)} article links found, parsing details...")

            # 각 상세 페이지 파싱
            for title, href in links:
                detail = self._parse_cafe_detail(driver, href)
                article_m = re.search(r'articleid=(\d+)', href)
                path_m = re.search(r'/sk77lee/(\d+)', href)
                if article_m:
                    desktop_url = f"https://cafe.naver.com/sk77lee/{article_m.group(1)}"
                elif path_m:
                    desktop_url = f"https://cafe.naver.com/sk77lee/{path_m.group(1)}"
                else:
                    desktop_url = href.replace("m.cafe.naver.com", "cafe.naver.com")
                
                posting = self.make_posting(
                    title=title,
                    source_url=desktop_url,
                    type=detail.get("type", self._guess_type(title)),
                    date=detail.get("date", ""),
                    reward=detail.get("reward", ""),
                    location=detail.get("location", ""),
                    duration=detail.get("duration", ""),
                    target_condition=detail.get("target_condition", ""),
                    target_gender=detail.get("target_gender", ""),
                    target_age=detail.get("target_age", ""),
                    raw_content=detail.get("raw_content", ""),
                )
                results.append(posting)

        except Exception as e:
            print(f"  [{self.name}] sk77lee Cafe Scraping Failed: {e}")

        unique = {p["title"]: p for p in results}.values()
        print(f"  [{self.name}] Found {len(unique)} postings")
        return list(unique)

    def _parse_cafe_detail(self, driver, url: str) -> dict:
        """상세 페이지에서 일정/사례비/위치/대상 등 추출"""
        info = {}
        try:
            driver.get(url)
            time.sleep(2)
            body_text = driver.find_element(By.TAG_NAME, "body").text
            info["raw_content"] = body_text[:2000]
            normalized = body_text.replace("*", "\n").replace("◈", "\n").replace("◆", "\n").replace("▶", "\n")

            m = re.search(r"(사\s*례\s*비|참석비|참여비|보상|사례금)\s*[:：)]\s*(.+)", normalized)
            if m: info["reward"] = m.group(2).strip().split("\n")[0]

            m = re.search(r"(소요\s*시간|진행\s*시간|소요)\s*[:：)]\s*(.+)", normalized)
            if m: info["duration"] = m.group(2).strip().split("\n")[0]

            m = re.search(r"(위\s*치|장\s*소|진행\s*장소)\s*[:：)]\s*(.+)", normalized)
            if m: info["location"] = m.group(2).strip().split("\n")[0]

            m = re.search(r"(일\s*정|날\s*짜|일\s*시|조사\s*기간|조사\s*일자|진행\s*일)\s*[:：)]\s*(.+)", normalized)
            if m: info["date"] = m.group(2).strip().split("\n")[0]

            m = re.search(r"(대\s*상\s*조\s*건|대\s*상|조\s*건|참여\s*대상)\s*[:：)]\s*(.+)", normalized)
            if m:
                target = m.group(2).strip().split("\n")[0]
                info["target_condition"] = target
                if "여성" in target and "남" not in target: info["target_gender"] = "여성"
                elif "남성" in target and "여" not in target: info["target_gender"] = "남성"
                elif "남녀" in target or "남여" in target: info["target_gender"] = "남녀"
                age_m = re.search(r"(만?\s*\d+[~\-]\s*\d+세|\d+대)", target)
                if age_m: info["target_age"] = age_m.group(1)

            full = body_text + " "
            if "온라인" in full and "좌담회" in full: info["type"] = "좌담회"
            elif "좌담회" in full or "FGD" in full.upper(): info["type"] = "좌담회"
            elif "맛테스트" in full or "갱조사" in full or "HUT" in full.upper(): info["type"] = "맛테스트"
            elif "인터뷰" in full: info["type"] = "인터뷰"
            elif "설문" in full or "서베이" in full: info["type"] = "온라인"

        except Exception:
            pass
        return info

    def _guess_type(self, title: str) -> str:
        if "좌담회" in title or "FGD" in title.upper(): return "좌담회"
        if "맛테스트" in title or "갱조사" in title: return "맛테스트"
        if "인터뷰" in title: return "인터뷰"
        if "설문" in title or "서베이" in title: return "온라인"
        return "기타"

# =============================================================================
#  7. HankookRandomScraper  (한국리서치 초대설문 무차별 대입 - 목표 아이디 648 주변)
# =============================================================================
class HankookRandomScraper(BaseScraper):
    name = "hankook_hrc_ms"
    base_url = "https://www.hrc-ms.com"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Brute-forcing HRC-MS hidden surveys (IDs 630-660) via Chrome")
        results = []
        driver = self.get_driver()

        for sid in range(630, 660):
            try:
                url = f"https://www.hrc-ms.com/participate/improSurvey/{sid}?intro=2"
                driver.get(url)
                time.sleep(2)

                page_text = driver.find_element(By.TAG_NAME, "body").text.strip()

                # 페이지가 비어있거나 에러 페이지이면 스킵
                if len(page_text) < 20:
                    continue
                if "요청하신 페이지를 찾을 수 없습니다" in page_text or "Not Found" in page_text:
                    continue
                if "로그인" in page_text and len(page_text) < 100:
                    continue

                # 페이지 텍스트에서 조사명 추출 시도
                survey_title = f"[HRC 초대설문 #{sid}]"
                lines = [l.strip() for l in page_text.split("\n") if len(l.strip()) > 5]
                for line in lines:
                    if any(kw in line for kw in ["조사", "설문", "인터뷰", "좌담", "참여"]):
                        survey_title = f"[HRC #{sid}] {line[:60]}"
                        break

                posting = self.make_posting(
                    title=survey_title,
                    source_url=url,
                    type="기타",
                    raw_content=page_text[:1000]
                )
                results.append(posting)
                print(f"  [{self.name}] Hidden Survey Found! ID {sid}: {survey_title[:40]}")
            except Exception as e:
                pass

        print(f"  [{self.name}] Found {len(results)} hidden postings")
        return results

# =============================================================================
#  7.1. HankookResearchScraper  (공개 게시판)
# =============================================================================
class HankookResearchScraper(BaseScraper):
    name = "hankook_research"
    base_url = "https://www.hrc.co.kr"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        # 공지사항/모집 페이지
        urls_to_try = [
            f"{self.base_url}/Notice/List",
            f"{self.base_url}/notice",
            f"{self.base_url}/board",
        ]

        for page_url in urls_to_try:
            soup = self.fetch(page_url)
            if not soup:
                continue

            items = soup.select("tr, .board-item, .list-item, article")
            for item in items:
                link = item.find("a")
                if not link:
                    continue
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if not title or len(title) < 5:
                    continue
                if not href.startswith("http"):
                    href = self.base_url + href

                posting = self.make_posting(
                    title=title,
                    source_url=href,
                    type="기타",
                )
                results.append(posting)
            if results:
                break

        print(f"  [{self.name}] Found {len(results)} postings")
        return results


# =============================================================================
#  DB 저장 · 중복 제거 · 실행
# =============================================================================
def save_to_db(postings: list[dict]) -> tuple[int, int, list[dict]]:
    """크롤링 결과를 DB에 저장. (새로 추가된 건수, 전체 건수, 새로운 공고 리스트) 반환."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0
    new_postings = []

    for p in postings:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO postings 
                (id, title, source, source_url, target_age, target_gender,
                 target_condition, date, time, duration, reward, location,
                 type, raw_content, scraped_at, is_active, url_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], p["title"], p["source"], p["source_url"],
                p.get("target_age", ""), p.get("target_gender", ""),
                p.get("target_condition", ""), p.get("date", ""),
                p.get("time", ""), p.get("duration", ""),
                p.get("reward", ""), p.get("location", ""),
                p.get("type", ""), p.get("raw_content", ""),
                p["scraped_at"], 1, p["url_hash"],
            ))
            if cursor.rowcount > 0:
                new_count += 1
                new_postings.append(p)
        except Exception as e:
            print(f"  [DB ERROR] {p.get('title', '?')}: {e}")

    conn.commit()
    conn.close()
    return new_count, len(postings), new_postings


def save_to_json(postings: list[dict], date_str: str = None):
    """크롤링 결과를 JSON 파일로 저장"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(SCRAPED_DATA_DIR, exist_ok=True)
    filepath = os.path.join(SCRAPED_DATA_DIR, f"{date_str}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(postings, f, ensure_ascii=False, indent=2)
    print(f"[JSON] Saved {len(postings)} postings to {filepath}")
    return filepath


def deduplicate_postings(postings: list[dict]) -> list[dict]:
    """제목 유사도 기반 중복 제거 (albabank ↔ fgdalba 등)"""
    seen_titles = {}
    unique = []
    for p in postings:
        norm_title = normalize_title(p["title"])
        if norm_title in seen_titles:
            # 중복 발견: 더 정보가 많은 쪽 유지
            existing = seen_titles[norm_title]
            if len(p.get("raw_content", "")) > len(existing.get("raw_content", "")):
                unique.remove(existing)
                unique.append(p)
                seen_titles[norm_title] = p
        else:
            seen_titles[norm_title] = p
            unique.append(p)
    return unique


def log_scrape(source: str, status: str, new_count: int, total: int, error: str = ""):
    """크롤링 로그 DB에 기록"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scrape_logs (source, finished_at, new_postings, total_scraped, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source, datetime.now().isoformat(), new_count, total, status, error))
        conn.commit()
        conn.close()
    except Exception:
        pass


# =============================================================================
#  메인 실행
# =============================================================================
ALL_SCRAPERS = [
    AlbabankScraper,
    PanelPowerScraper,
    SurveylinkScraper,
    PanelNowScraper,
    ResearchiScraper,
    HankookResearchScraper,
    HankookRandomScraper,
    NaverCafeScraper,
    DaumCafeScraper,
]

def run_all_scrapers(test_mode: bool = False) -> list[dict]:
    """모든 크롤러 실행"""
    print("=" * 60)
    print(f"[MR Newsletter Scraper] Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_postings = []
    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        try:
            postings = scraper.scrape()
            all_postings.extend(postings)
            log_scrape(scraper.name, "success", len(postings), len(postings))
        except Exception as e:
            print(f"  [ERROR] {scraper.name}: {e}")
            traceback.print_exc()
            log_scrape(scraper.name, "failed", 0, 0, str(e))

        if test_mode:
            break  # 테스트 모드에서는 첫 번째 크롤러만

    BaseScraper.quit_driver()

    # 중복 제거
    before = len(all_postings)
    all_postings = deduplicate_postings(all_postings)
    after = len(all_postings)
    if before != after:
        print(f"\n[Dedup] {before} -> {after} postings (removed {before - after} duplicates)")

    # 저장
    if all_postings:
        new_count, total, new_postings_list = save_to_db(all_postings)
        save_to_json(new_postings_list)
        print(f"\n[Result] {new_count} new / {total} total postings saved to DB")
        all_postings = new_postings_list # 오직 새로운(새로 발굴된) 포스팅만 반환하여 이메일로 전송!
    else:
        print("\n[Result] No postings found")

    print("=" * 60)
    return all_postings


if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    run_all_scrapers(test_mode=test_mode)
