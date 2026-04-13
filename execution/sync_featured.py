import os
import json
import sqlite3
import urllib.request
from datetime import datetime

def load_env():
    env = {}
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, '.env')
        if not os.path.exists(env_path):
            env_path = '.env'
            
        lines = []
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
    except Exception as e:
        print(f"  [Env Load Error] {e}")
    return env

def sync_featured_postings():
    print("============================================================")
    print("  [자사 공고 동기화] Google Sheets에서 고정 공고를 가져옵니다...")
    
    env = load_env()
    WEB_APP_URL = env.get('WEB_APP_URL')
    
    if not WEB_APP_URL:
        print("  [오류] .env에 WEB_APP_URL이 설정되어 있지 않습니다.")
        return

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "data", "newsletter.db")

    try:
        GAS_API_TOKEN = env.get('GAS_API_TOKEN')
        url = f"{WEB_APP_URL}?action=get_featured&auth={GAS_API_TOKEN}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            
            if res.get('status') == 'success':
                featured_data = res.get('data', [])
                print(f"  [결과] 총 {len(featured_data)}건의 고정 공고를 발견했습니다. DB를 동기화합니다.")
                
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                scraped_at = datetime.now().isoformat()
                
                # 먼저 기존 고정 공고를 모두 삭제 (완벽 동기화를 위해)
                c.execute("DELETE FROM postings WHERE is_featured = 1 AND source = '알바단지 자체'")
                
                # 가져온 고정 공고 새로 삽입
                for p in featured_data:
                    c.execute("""
                        INSERT INTO postings (
                            id, title, source, source_url, target_age, duration,
                            reward, location, type, scraped_at, is_active,
                            is_featured, survey_content
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get('id', ''),
                        p.get('title', ''), 
                        '알바단지 자체', 
                        p.get('url', ''), 
                        p.get('target', ''), 
                        p.get('duration', ''),
                        p.get('reward', ''), 
                        p.get('location', ''), 
                        p.get('type', '기타'), 
                        scraped_at, 
                        1, 
                        1, 
                        p.get('survey_content', '')
                    ))
                
                conn.commit()
                conn.close()
                print("  [완료] 고정 공고 DB 동기화가 완료되었습니다.")
            else:
                print(f"  [오류] 구글 시트에서 응답이 실패했습니다: {res}")
                
    except Exception as e:
        print(f"  [동기화 에러] {e}")
    print("============================================================")

if __name__ == '__main__':
    sync_featured_postings()
