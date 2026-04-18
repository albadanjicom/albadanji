import os
import json
import urllib.request
import smtplib
from email.message import EmailMessage
from datetime import datetime
import time

def load_env():
    env = {}
    try:
        # Load from the ROOT directory (where run_daily is usually invoked)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, '.env')
        if not os.path.exists(env_path):
            env_path = '.env'
            
        lines = []
        # Try UTF-16 first (common on Windows PowerShell outputs)
        try:
            with open(env_path, 'r', encoding='utf-16') as f:
                lines = f.readlines()
        except:
            # Fallback to UTF-8
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k.strip()] = v.strip().strip('"\'')
    except Exception as e:
        print(f"  [환경 설정 로드 실패] {e}")
    return env

def get_subscribers(web_app_url, token):
    try:
        print("  [1/4] 구글 시트에서 구독자 명단을 조회합니다...")
        url = f"{web_app_url}?action=get_subscribers&auth={token}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            if res.get('status') == 'success':
                return res.get('data', [])
            else:
                print(f"  [오류] 명단 조회 실패: {res.get('message')}")
    except Exception as e:
        print(f"  [명단 조회 에러] {e}")
    return []

def send_newsletters(dry_run=False):
    print("============================================================")
    print("                 [알바단지 이메일 자동 발송 시작]                  ")
    print("============================================================")
    
    env = load_env()
    WEB_APP_URL = env.get('WEB_APP_URL')
    SMTP_USER = env.get('SMTP_USER')
    SMTP_APP_PASSWORD = env.get('SMTP_APP_PASSWORD')
    
    if not all([WEB_APP_URL, SMTP_USER, SMTP_APP_PASSWORD]):
        print("  [오류] .env 파일에 필요한 계정 정보(SMTP_USER, SMTP_APP_PASSWORD)가 누락되었습니다.")
        return {"success": 0, "fail": 0, "total": 0}
        
    # 2. 이번에 보낼 HTML 파일 확인
    today_str = datetime.now().strftime('%Y-%m-%d')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_html_path = os.path.join(project_root, 'output', 'email', f"{today_str}.html")
    
    if not os.path.exists(output_html_path):
        print(f"  [오류] 오늘의 이메일 파일({output_html_path})이 없습니다. 봇 빌더를 먼저 실행해주세요.")
        return {"success": 0, "fail": 0, "total": 0}
        
    with open(output_html_path, 'r', encoding='utf-8') as f:
        base_html = f.read()
        
    # 3. 구독자 명단 확인
    GAS_API_TOKEN = env.get('GAS_API_TOKEN')
    subscribers = get_subscribers(WEB_APP_URL, GAS_API_TOKEN)
    
    if not subscribers:
        print("  [2/4] 구독중인 회원이 0명이거나 리스트를 가져오지 못했습니다. 발송을 취소합니다.")
        return {"success": 0, "fail": 0, "total": 0}
    
    print(f"  [2/4] 총 {len(subscribers)}명의 활성 구독자를 찾았습니다.")
    
    # 4. 발송 진행 (SMTP)
    print("  [3/4] 구글 SMTP 서버에 로그인합니다...")
    success_count = 0
    fail_count = 0
    
    server = None
    try:
        if not dry_run:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SMTP_USER, SMTP_APP_PASSWORD)
    except Exception as e:
        print(f"  [접속 오류] SMTP 서버 로그인에 실패했습니다. (앱 비밀번호 혹은 계정명 확인 필요)\n  - 에러: {e}")
        return {"success": 0, "fail": 0, "total": len(subscribers)}
        
    print("  [4/4] 개별 이메일 발송을 시작합니다! (스팸 방지를 위해 랜덤 시간차 적용)")
    
    import random
    
    # 5시~7시(2시간 = 7200초) 안에 모두 보내도록 최대 평균 딜레이 계산
    # 구독자가 적을 때는 25~50초 간격 유지, 몹시 많을 때는 그에 맞춰 간격 단축
    max_avg_delay = min(7000 / max(len(subscribers), 1), 35) 
    
    for idx, email in enumerate(subscribers):
        # 개별 사용자용 커스텀 취소 링크 삽입
        unsub_link = f"{WEB_APP_URL}?action=unsubscribe&email={email}"
        personal_html = base_html.replace('{UNSUBSCRIBE_LINK}', unsub_link)
        
        msg = EmailMessage()
        msg['Subject'] = f"[알바단지] {today_str} 좌담회 소식이 도착했습니다!"
        msg['From'] = f"알바단지 <{SMTP_USER}>"
        msg['To'] = email
        msg.set_content("HTML 형식을 지원하는 메일 클라이언트에서 열어주세요.")
        msg.add_alternative(personal_html, subtype='html')
        
        try:
            if not dry_run:
                server.send_message(msg)
            print(f"      - [{idx+1}/{len(subscribers)}] 전송 완료: {email}")
            success_count += 1
            
            # 마지막 메일이 아니면 랜덤 대기
            if idx < len(subscribers) - 1:
                min_delay = max(5, int(max_avg_delay * 0.5))
                max_delay = max(10, int(max_avg_delay * 1.5))
                delay = random.randint(min_delay, max_delay)
                print(f"        (사람처럼 보이기 위해 {delay}초 대기 중...)")
                time.sleep(delay)
                
        except Exception as e:
            print(f"      - [{idx+1}/{len(subscribers)}] 전송 실패: {email} ({e})")
            fail_count += 1
            
    if server:
        server.quit()
        
    print("============================================================")
    print(f"[발송 완료] 성공: {success_count}건, 실패: {fail_count}건")
    print("============================================================")
    
    return {"success": success_count, "fail": fail_count, "total": len(subscribers)}

def send_admin_report(stats, postings_list):
    env = load_env()
    SMTP_USER = env.get('SMTP_USER')
    SMTP_APP_PASSWORD = env.get('SMTP_APP_PASSWORD')
    ADMIN_EMAIL = env.get('ADMIN_EMAIL')
    
    if not all([SMTP_USER, SMTP_APP_PASSWORD, ADMIN_EMAIL]):
        print("  [보고서 오류] 계정 정보(SMTP_USER) 또는 관리자 이메일 정보가 없어 보고서를 보낼 수 없습니다.")
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    msg = EmailMessage()
    msg['Subject'] = f"[보고] {today_str} 알바단지 뉴스레터 발행 결과"
    msg['From'] = f"알바단지 시스템 <{SMTP_USER}>"
    msg['To'] = ADMIN_EMAIL
    
    posting_count = 0
    source_summary = ""
    if isinstance(postings_list, int):
        posting_count = postings_list
    else:
        posting_count = len(postings_list)
        from collections import Counter
        counts = Counter(p.get('source', '기타') for p in postings_list)
        source_summary = "\n   [출처별 상세]\n"
        for src, cnt in counts.most_common():
            source_summary += f"   - {src}: {cnt}건\n"

    content = f"""
안녕하세요, 관리자님.
{today_str} 알바단지 뉴스레터 발행 결과를 보고드립니다.

1. 신규 공고 수집 요약
   - 총 수집 건수: {posting_count}건{source_summary}
2. 뉴스레터 이메일 발송 현황
   - 총 대상자: {stats.get('total', 0)}명
   - 발송 성공: {stats.get('success', 0)}건
   - 발송 실패: {stats.get('fail', 0)}건

오늘의 업무가 성공적으로 완료되었습니다.
감사합니다.
"""
    msg.set_content(content)
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_APP_PASSWORD)
            server.send_message(msg)
        print(f"  [보고 완료] 관리자({ADMIN_EMAIL})에게 일일 보고서를 발송했습니다.")
    except Exception as e:
        print(f"  [보고 실패] 관리자 메일 발송 중 에러 발생: {e}")

if __name__ == '__main__':
    send_newsletters(dry_run=False)
