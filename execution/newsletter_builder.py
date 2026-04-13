"""
MR Newsletter -- Newsletter Builder
크롤링 데이터 -> 웹사이트 HTML + 이메일 HTML 생성
"""
import json
import os
import sqlite3
import sys
from datetime import datetime

# 프로젝트 루트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "newsletter.db")
WEBSITE_DIR = os.path.join(PROJECT_ROOT, "newsletter-website")
OUTPUT_EMAIL_DIR = os.path.join(PROJECT_ROOT, "output", "email")
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "templates")
SCRAPED_DATA_DIR = os.path.join(PROJECT_ROOT, ".tmp", "scraped_data")

def load_env():
    env = {}
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if not os.path.exists(env_path):
        return env
    try:
        # Try UTF-16 first
        try:
            with open(env_path, 'r', encoding='utf-16') as f:
                lines = f.readlines()
        except:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k.strip()] = v.strip().strip('"\'')
    except:
        pass
    return env

ENV = load_env()


# Type -> badge class mapping for email
TYPE_BADGE = {
    "fgd": ("type-fgd", "FGD"),
    "online": ("type-online", "Online"),
    "taste": ("type-taste", "Taste"),
    "interview": ("type-interview", "Interview"),
    "other": ("type-other", "Other"),
}

TYPE_MAP = {
    "좌담회": "fgd",
    "설문조사": "online",
    "온라인": "online",
    "맛테스트": "taste",
    "인터뷰": "interview",
    "유치조사": "other",
    "패널모집": "other",
    "기타": "other",
}

TYPE_COLOR = {
    "fgd": "#3b82f6",
    "online": "#22c55e",
    "taste": "#f59e0b",
    "interview": "#a855f7",
    "other": "#a0a0a0",
}


def get_today_postings(date_str: str = None) -> list[dict]:
    """DB에서 오늘의 공고 가져오기"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 항상 DB에서 가져오기 (JSON은 크롤러 실행별 신규 건수만 저장되므로 무시)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM postings 
        WHERE date(scraped_at) = ? AND is_active = 1
        ORDER BY is_featured DESC, scraped_at DESC
    """, (date_str,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def build_website_data(postings: list[dict], date_str: str = None):
    """웹사이트용 data.json 생성"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    output = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "count": len(postings),
        "postings": postings,
    }

    data_path = os.path.join(WEBSITE_DIR, "data.js")
    with open(data_path, "w", encoding="utf-8") as f:
        js_content = f"window.postingsData = {json.dumps(output, ensure_ascii=False, indent=2)};"
        f.write(js_content)

    print(f"[Website] data.js generated: {len(postings)} postings")
    return data_path


def build_email_posting_html(posting: dict) -> str:
    """이메일용 개별 공고 HTML 생성"""
    p_type = TYPE_MAP.get(posting.get("type", ""), "other")
    color = TYPE_COLOR.get(p_type, "#a0a0a0")
    type_label = posting.get("type", "Other")

    type_icons = {
        "좌담회": "&#128172;", "온라인": "&#128187;", "설문조사": "&#128187;",
        "맛테스트": "&#127860;", "인터뷰": "&#127908;", "유치조사": "&#128230;",
        "패널모집": "&#128101;", "기타": "&#128196;", "상시모집": "&#128260;"
    }
    t_icon = type_icons.get(p_type, "&#128196;")
    
    info_rows = []
    
    if posting.get("date"):
        info_rows.append(f"""
          <tr>
            <td style="padding: 10px 0; border-bottom: 1px solid #E2E8F0; width: 75px; vertical-align: top;">
              <span style="color: #94A3B8; font-size: 13px;">&#128197; 일정</span>
            </td>
            <td style="padding: 10px 0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
              <span style="color: #1E293B; font-size: 13px; line-height: 1.4;">{posting['date']}</span>
            </td>
          </tr>""")
    if posting.get("duration"):
        info_rows.append(f"""
          <tr>
            <td style="padding: 10px 0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
              <span style="color: #94A3B8; font-size: 13px;">&#9202; 소요시간</span>
            </td>
            <td style="padding: 10px 0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
              <span style="color: #1E293B; font-size: 13px; line-height: 1.4;">{posting['duration']}</span>
            </td>
          </tr>""")
    if posting.get("reward"):
        info_rows.append(f"""
          <tr>
            <td style="padding: 10px 0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
              <span style="color: #94A3B8; font-size: 13px;">&#128176; 사례비</span>
            </td>
            <td style="padding: 10px 0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
              <span style="color: #2563EB; font-size: 13px; font-weight: 700; line-height: 1.4;">{posting['reward']}</span>
            </td>
          </tr>""")
          
    target_str = ""
    if posting.get("target_age") and posting.get("target_gender"):
        target_str = f"{posting['target_age']} {posting['target_gender']}"
    elif posting.get("target_age"):
        target_str = posting['target_age']
    elif posting.get("target_gender"):
        target_str = posting['target_gender']
        
    if target_str:
        info_rows.append(f"""
          <tr>
            <td style="padding: 10px 0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
              <span style="color: #94A3B8; font-size: 13px;">&#128100; 대상</span>
            </td>
            <td style="padding: 10px 0; border-bottom: 1px solid #E2E8F0; vertical-align: top;">
              <span style="color: #1E293B; font-size: 13px; line-height: 1.4;">{target_str}</span>
            </td>
          </tr>""")
          
    if posting.get("location"):
        info_rows.append(f"""
          <tr>
            <td style="padding: 10px 0; border-bottom: none; vertical-align: top;">
              <span style="color: #94A3B8; font-size: 13px;">&#128205; 장소</span>
            </td>
            <td style="padding: 10px 0; border-bottom: none; vertical-align: top;">
              <span style="color: #1E293B; font-size: 13px; line-height: 1.4;">{posting['location']}</span>
            </td>
          </tr>""")
          
    if info_rows and not posting.get("location"):
        info_rows[-1] = info_rows[-1].replace('border-bottom: 1px solid #E2E8F0;', 'border-bottom: none;')

    meta_html = ""
    if info_rows:
        rows_str = "".join(info_rows)
        meta_html = f'''
          <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #F8FAFC; border-radius: 8px; margin-top: 16px; margin-bottom: 4px;">
            <tr>
              <td style="padding: 4px 16px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                  {rows_str}
                </table>
              </td>
            </tr>
          </table>
        '''
        
    if posting.get("survey_content"):
        site_url = ENV.get("SITE_URL", "https://www.albadanji.com")
        detail_url = f"{site_url}/detail.html?id={posting.get('id', '')}"
        meta_html += f'''
          <div style="margin-top: 12px; text-align: center;">
            <a href="{detail_url}" target="_blank" style="display: inline-block; padding: 10px 20px; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; color: #2563EB; text-decoration: none; font-size: 14px; font-weight: 600;">&#128269; 상세 내용 보기</a>
          </div>
        '''

    return f"""
          <tr>
            <td style="padding-bottom: 16px;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); overflow: hidden; border-collapse: separate;">
                <tr>
                  <td style="padding: 0;">
                    <a href="{posting.get('source_url', '#')}" style="display: block; padding: 24px; text-decoration: none; color: inherit;" target="_blank">
                      <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                        <tr>
                          <td style="vertical-align: top;">
                            <h3 style="font-size: 17px; font-weight: 700; color: #1E293B; margin: 0; line-height: 1.4; word-break: keep-all; text-decoration: none;">
                              {posting.get('title', '')}
                            </h3>
                          </td>
                          <td style="vertical-align: top; text-align: right; width: 85px; padding-left: 12px;">
                            <span class="type-badge" style="display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 700; background: rgba({_hex_to_rgb(color)}, 0.12); color: {color}; white-space: nowrap; border: 1px solid rgba({_hex_to_rgb(color)}, 0.2); text-decoration: none;">
                              {t_icon} {type_label}
                            </span>
                          </td>
                        </tr>
                      </table>
                      
                      {meta_html}
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>"""


def _hex_to_rgb(hex_color: str) -> str:
    """#3b82f6 -> 59,130,246"""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def build_email_html(postings: list[dict], date_str: str = None) -> str:
    """이메일 HTML 전체 생성"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 날짜 표시 형식
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    days_ko = ["월", "화", "수", "목", "금", "토", "일"]
    date_display = f"{dt.year}.{dt.month:02d}.{dt.day:02d} ({days_ko[dt.weekday()]})"

    # 공고별 HTML 생성
    postings_html = "\n".join([build_email_posting_html(p) for p in postings])

    # 템플릿 로드
    template_path = os.path.join(TEMPLATE_DIR, "email_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # 변수 치환
    html = template.replace("{{ title }}", f"알바단지 - {date_display}")
    html = html.replace("{{ date_display }}", date_display)
    html = html.replace("{{ posting_count }}", str(len(postings)))
    html = html.replace("{{ postings_html }}", postings_html)
    site_url = ENV.get("SITE_URL", "https://albadanji.com")
    html = html.replace("{{ site_url }}", site_url)
    html = html.replace("{{ unsubscribe_url }}", "{UNSUBSCRIBE_LINK}")

    return html


def save_email_html(html: str, date_str: str = None) -> str:
    """이메일 HTML 파일 저장"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    os.makedirs(OUTPUT_EMAIL_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_EMAIL_DIR, f"{date_str}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Email] HTML saved: {filepath}")
    return filepath


def log_newsletter(date_str: str, total: int, web_path: str, email_path: str):
    """뉴스레터 발행 로그 기록"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO newsletters 
            (publish_date, total_postings, web_html_path, email_html_path)
            VALUES (?, ?, ?, ?)
        """, (date_str, total, web_path, email_path))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB WARN] Newsletter log failed: {e}")


def build_all_data_js(start_date: str = "2026-04-05"):
    """list.html용: DB에서 start_date 이후 전체 공고를 all_data.js로 생성"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT id, title, source, source_url,
               target_age, target_gender, target_condition,
               date, time, duration, reward, location,
               type, scraped_at, is_active, url_hash,
               is_featured, survey_content
        FROM postings
        WHERE date(scraped_at) >= ?
          AND is_active = 1
        ORDER BY is_featured DESC, scraped_at DESC
    """, (start_date,))
    rows = c.fetchall()
    conn.close()

    import json as _json
    postings = [dict(r) for r in rows]
    output = {
        "generated_at": datetime.now().isoformat(),
        "start_date": start_date,
        "count": len(postings),
        "postings": postings,
    }
    out_path = os.path.join(WEBSITE_DIR, "all_data.js")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"window.allPostingsData = {_json.dumps(output, ensure_ascii=False, indent=2)};\n")
    print(f"[all_data.js] {len(postings)}건 누적 저장 완료")



def build_website_archive():
    """웹사이트 아카이브용 데이터 JS 생성 및 파일 복사"""
    import shutil
    archives_dir = os.path.join(WEBSITE_DIR, "archives")
    os.makedirs(archives_dir, exist_ok=True)
    
    email_files = []
    if os.path.exists(OUTPUT_EMAIL_DIR):
        email_files = [f for f in os.listdir(OUTPUT_EMAIL_DIR) if f.endswith('.html')]
        
    dates = []
    for f in email_files:
        src = os.path.join(OUTPUT_EMAIL_DIR, f)
        dst = os.path.join(archives_dir, f)
        shutil.copy2(src, dst)
        dates.append(f.replace(".html", ""))
        
    dates.sort(reverse=True)
    
    js_path = os.path.join(WEBSITE_DIR, "js", "archives-data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        import json
        f.write(f"const archiveDates = {json.dumps(dates)};\n")
    print(f"[Archive] data.js generated: {len(dates)} past newsletters")


def build_all(date_str: str = None):
    """전체 빌드 실행"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print("=" * 60)
    print(f"[Newsletter Builder] Building for {date_str}")
    print("=" * 60)

    # 1. 데이터 로드
    postings = get_today_postings(date_str)
    if not postings:
        print("[INFO] No new postings today, but proceeding with build as requested.")
        postings = [] # Ensure it's an empty list

    print(f"[Data] {len(postings)} postings loaded")

    # 2. 웹사이트 data.js 생성
    web_path = build_website_data(postings, date_str)

    # 3. 이메일 HTML 생성
    email_html = build_email_html(postings, date_str)
    email_path = save_email_html(email_html, date_str)

    # 4. 아카이브 업데이트
    build_website_archive()

    # 5. 전체 누적 데이터 업데이트 (list.html용)
    build_all_data_js()

    # 6. 로그
    log_newsletter(date_str, len(postings), web_path, email_path)

    print(f"\n[DONE] Newsletter built successfully!")
    print(f"  Website data: {web_path}")
    print(f"  Email HTML:   {email_path}")
    print(f"  (Open the email HTML in browser to preview)")
    print("=" * 60)


if __name__ == "__main__":
    date_arg = None
    if len(sys.argv) > 1 and sys.argv[1] != "--test":
        date_arg = sys.argv[1]
    build_all(date_str=date_arg)
