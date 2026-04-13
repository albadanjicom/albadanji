import re
data = open('newsletter-website/archives/2026-04-10.html', encoding='utf-8').read()
urls = re.findall(r'href="([^"]*1241[^"]*)"', data)
for u in set(urls): print(u)
