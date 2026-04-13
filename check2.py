from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import sys

# Get article 124102
options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

driver.get("https://cafe.naver.com/togetheralba/124102")
time.sleep(3)

# Since it redirects to an iframe on desktop, we should switch to iframe
try:
    driver.switch_to.frame("cafe_main")
    html = driver.page_source
    soup = BeautifulSoup(html, 'lxml')
    print("TITLE:", soup.select_one("h3.title_text").get_text(strip=True))
    print("BODY:", soup.select_one("div.se-main-container").get_text(strip=True))
except Exception as e:
    print("Failed desktop:", e)
    driver.get("https://m.cafe.naver.com/togetheralba/124102")
    time.sleep(3)
    html = driver.page_source
    soup = BeautifulSoup(html, 'lxml')
    tit = soup.select_one("h2.tit")
    body = soup.select_one("div#postContent")
    print("MOBILE TITLE:", tit.get_text(strip=True) if tit else "N/A")
    print("MOBILE BODY:", body.get_text(strip=True)[:1000] if body else "N/A")

driver.quit()
