"""
네이버 로그인 스크립트
- 스크래퍼 전용 프로필(.tmp/chrome_profile)을 띄우고 사용자가 직접 로그인합니다.
- 코드가 백그라운드에서 주기적으로 쿠키를 검사하여 로그인(NID_AUT)을 감지하면 자동으로 저장하고 종료합니다.
"""
import json
import os
import subprocess
import time
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(PROJECT_ROOT, ".tmp", "chrome_profile")
COOKIE_FILE = os.path.join(PROJECT_ROOT, ".tmp", "naver_cookies.json")
os.makedirs(PROFILE_DIR, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEBUG_PORT = 9222

def check_cookies_via_cdp():
    """CDP를 통해 현재 브라우저의 쿠키를 가져옵니다."""
    try:
        tabs = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=2).json()
        ws_url = None
        for tab in tabs:
            if tab.get("type") == "page":
                ws_url = tab.get("webSocketDebuggerUrl")
                break
        if not ws_url:
            return []

        import websocket
        ws = websocket.create_connection(ws_url, timeout=2)
        # Network.getAllCookies를 가져옵니다 (Network.enable 필요없음)
        ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
        all_cookies = []
        for _ in range(30):
            msg = json.loads(ws.recv())
            if msg.get("id") == 1:
                all_cookies = msg.get("result", {}).get("cookies", [])
                break
        ws.close()
        
        # 네이버 쿠키만 필터링
        naver_cookies = [c for c in all_cookies if "naver" in c.get("domain", "")]
        return naver_cookies
    except Exception as e:
        return []

def main():
    print("=" * 60)
    print("  네이버 스크래퍼 쿠키 셋업")
    print("=" * 60)
    print("\n  1. 곧 열리는 크롬 창에서 네이버에 로그인하세요.")
    print("  2. 로그인이 감지되면 자동으로 창이 닫히고 저장됩니다.\n")

    # 기존 크롬 프로세스 정리본 (충돌 방지)
    subprocess.run("taskkill /f /im chrome.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    proc = subprocess.Popen([
        CHROME_PATH,
        f"--user-data-dir={PROFILE_DIR}",
        f"--remote-debugging-port={DEBUG_PORT}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "https://nid.naver.com/nidlogin.login"
    ])

    print("  대기 중... (로그인을 완료해 주세요)")
    
    # 2초마다 쿠키 확인
    success = False
    for _ in range(60):  # 최대 2분 대기
        time.sleep(2)
        if proc.poll() is not None:
            print("  [WARN] 창이 닫혔습니다.")
            break
            
        cookies = check_cookies_via_cdp()
        login_nids = [c["name"] for c in cookies if c["name"] in ("NID_AUT", "NID_SES")]
        
        if "NID_AUT" in login_nids and "NID_SES" in login_nids:
            print("\n  [SUCCESS] 네이버 로그인이 감지되었습니다!")
            
            # 쿠키 저장
            unique = []
            seen = set()
            for c in cookies:
                k = (c["name"], c["domain"])
                if k not in seen:
                    seen.add(k)
                    unique.append({
                        "domain": c["domain"],
                        "name": c["name"],
                        "value": c["value"],
                        "path": c.get("path", "/"),
                        "secure": c.get("secure", False),
                    })
            
            with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                json.dump(unique, f, ensure_ascii=False, indent=2)
                
            print(f"  -> {len(unique)}개의 쿠키가 파일로 저장되었습니다.")
            success = True
            break
            
    # 크롬 종료
    print("  크롬을 종료합니다...")
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        
    if success:
        print("\n  [완료] 이제 스크래퍼가 정상적으로 작동합니다.")
        print("  실행: py execution/run_daily.py")
    else:
        print("\n  [실패] 시간 내에 로그인 쿠키를 감지하지 못했습니다. 다시 시도해 주세요.")


if __name__ == "__main__":
    main()
