import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
import sys

# 이메일 센더의 환경변수 로더 가져오기
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from execution.email_sender import load_env

env = load_env()
SMTP_USER = env.get('SMTP_USER')
SMTP_APP_PASSWORD = env.get('SMTP_APP_PASSWORD')
WEB_APP_URL = env.get('WEB_APP_URL')

today_str = datetime.now().strftime('%Y-%m-%d')
project_root = os.path.dirname(os.path.abspath(__file__))
output_html_path = os.path.join(project_root, 'output', 'email', f"{today_str}.html")

if not os.path.exists(output_html_path):
    print(f"오류: {output_html_path} 파일이 존재하지 않습니다.")
    sys.exit(1)

with open(output_html_path, 'r', encoding='utf-8') as f:
    base_html = f.read()

emails = ['ggamyun@naver.com', 'yeeun012@naver.com']

try:
    print("구글 SMTP 접속 시도 중...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SMTP_USER, SMTP_APP_PASSWORD)
    print("로그인 성공! 메일 발송 중...")
    
    for email in emails:
        unsub_link = f"{WEB_APP_URL}?action=unsubscribe&email={email}"
        personal_html = base_html.replace('{UNSUBSCRIBE_LINK}', unsub_link)
        
        msg = EmailMessage()
        msg['Subject'] = f"[알바단지] {today_str} 최신 지원 공고가 도착했습니다! (방금 구축한 시스템 테스트)"
        msg['From'] = f"알바단지 <{SMTP_USER}>"
        msg['To'] = email
        msg.set_content("HTML 형식을 지원하는 메일 클라이언트에서 열어주세요.")
        msg.add_alternative(personal_html, subtype='html')
        
        server.send_message(msg)
        print(f"[{email}] 님에게 테스트 메일이 성공적으로 전송되었습니다!")
        
    server.quit()
except Exception as e:
    print(f"발송 실패: {e}")
