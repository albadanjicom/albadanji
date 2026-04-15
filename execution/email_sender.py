import os
import boto3
from botocore.exceptions import ClientError
import json
import urllib.request
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
    AWS_ACCESS_KEY_ID = env.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = env.get('AWS_REGION', 'ap-northeast-2')
    AWS_SES_SENDER_EMAIL = env.get('AWS_SES_SENDER_EMAIL')
    
    if not all([WEB_APP_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SES_SENDER_EMAIL]):
        print("  [오류] .env 파일에 필요한 계정 정보(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SES_SENDER_EMAIL)가 누락되었습니다.")
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
    
    # 4. 발송 진행 (AWS SES)
    print("  [3/4] AWS SES 클라이언트를 초기화합니다...")
    success_count = 0
    fail_count = 0
    
    try:
        if not dry_run:
            ses_client = boto3.client(
                'ses',
                region_name=AWS_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
    except Exception as e:
        print(f"  [접속 오류] AWS SES 클라이언트 초기화에 실패했습니다.\n  - 에러: {e}")
        return {"success": 0, "fail": 0, "total": len(subscribers)}
        
    print("  [4/4] 개별 이메일 발송을 시작합니다!")
    for idx, email in enumerate(subscribers):
        # 개별 사용자용 커스텀 취소 링크 삽입
        unsub_link = f"{WEB_APP_URL}?action=unsubscribe&email={email}"
        personal_html = base_html.replace('{UNSUBSCRIBE_LINK}', unsub_link)
        
        msg = EmailMessage()
        msg['Subject'] = f"[알바단지] {today_str} 최신 지원 공고가 도착했습니다!"
        msg['From'] = f"알바단지 <{AWS_SES_SENDER_EMAIL}>"
        msg['To'] = email
        msg.set_content("HTML 형식을 지원하는 메일 클라이언트에서 열어주세요.")
        msg.add_alternative(personal_html, subtype='html')
        
        try:
            if not dry_run:
                response = ses_client.send_raw_email(
                    Source=msg['From'],
                    Destinations=[msg['To']],
                    RawMessage={'Data': msg.as_string()}
                )
            print(f"      - [{idx+1}/{len(subscribers)}] 전송 완료: {email}")
            success_count += 1
            time.sleep(0.1) # AWS Limit 제한 넘지 않도록 약간의 딜레이
        except ClientError as e:
            print(f"      - [{idx+1}/{len(subscribers)}] 전송 실패 (AWS SES 에러): {email} ({e.response['Error']['Message']})")
            fail_count += 1
        except Exception as e:
            print(f"      - [{idx+1}/{len(subscribers)}] 전송 실패: {email} ({e})")
            fail_count += 1
        
    print("============================================================")
    print(f"[발송 완료] 성공: {success_count}건, 실패: {fail_count}건")
    print("============================================================")
    
    return {"success": success_count, "fail": fail_count, "total": len(subscribers)}

def send_admin_report(stats, postings_list):
    """관리자에게 일일 업무 보고서를 발송합니다."""
    env = load_env()
    AWS_ACCESS_KEY_ID = env.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = env.get('AWS_REGION', 'ap-northeast-2')
    AWS_SES_SENDER_EMAIL = env.get('AWS_SES_SENDER_EMAIL')
    ADMIN_EMAIL = env.get('ADMIN_EMAIL')
    
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SES_SENDER_EMAIL, ADMIN_EMAIL]):
        print("  [보고서 오류] AWS 계정 또는 관리자 이메일 정보가 없어 보고서를 보낼 수 없습니다.")
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    msg = EmailMessage()
    msg['Subject'] = f"[보고] {today_str} 알바단지 뉴스레터 발행 결과"
    msg['From'] = f"알바단지 시스템 <{AWS_SES_SENDER_EMAIL}>"
    msg['To'] = ADMIN_EMAIL
    
    posting_count = 0
    source_summary = ""
    if isinstance(postings_list, int):
        posting_count = postings_list
    else:
        posting_count = len(postings_list)
        from collections import Counter
        counts = Counter(p.get('source', '기타') for p in postings_list)
        source_summary = "\n   [출처별 수집 상세]\n"
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
        ses_client = boto3.client(
            'ses',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        ses_client.send_raw_email(
            Source=msg['From'],
            Destinations=[msg['To']],
            RawMessage={'Data': msg.as_string()}
        )
        print(f"  [보고 완료] 관리자({ADMIN_EMAIL})에게 일일 보고서를 발송했습니다.")
    except ClientError as e:
        print(f"  [보고 실패] 관리자 메일 발송 중 에러 발생 (AWS): {e.response['Error']['Message']}")
    except Exception as e:
        print(f"  [보고 실패] 관리자 메일 발송 중 에러 발생: {e}")

if __name__ == '__main__':
    send_newsletters(dry_run=False)
