import os
import glob

old_url = 'AKfycbznThqYqKC9Ld6lN7R1uFtjTuuwe-CDfddqKJjKihVLFMrskUFF-5StdeYeHN5X2OVJ4A'
new_url = 'AKfycbxsoNoQ5saodpsC9AlkW1qGPUeCzKUGomU6iAG58y7zD541ahWTuoSJH1gVmD8ekJzlwQ'

files = glob.glob('output/email/*.html') + glob.glob('newsletter-website/archives/*.html')
count = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    if old_url in content:
        content = content.replace(old_url, new_url)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        count += 1
        print(f'Updated {f}')
print(f'Total {count} files updated.')
