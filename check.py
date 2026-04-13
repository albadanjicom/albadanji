import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
driver.get('https://m.cafe.naver.com/togetheralba')
time.sleep(3)
soup = BeautifulSoup(driver.page_source, 'lxml')

print("Using a.mainLink:")
items = soup.select("a.mainLink")
for item in items:
    tit_el = item.select_one("[class*='tit'], strong, .tit")
    title = tit_el.get_text(strip=True) if tit_el else item.get_text(strip=True)
    href = item.get("href", "")
    print(f"Title: {title[:30]} | Href: {href}")

print("\nUsing ul.list_area li a.txt_area:")
items = soup.select("ul.list_area li a.txt_area")
for item in items:
    tit_el = item.select_one("strong.tit")
    title = tit_el.get_text(strip=True) if tit_el else item.get_text(strip=True)
    href = item.get("href", "")
    print(f"Title: {title[:30]} | Href: {href}")

driver.quit()
