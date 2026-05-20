import requests, re
from bs4 import BeautifulSoup

# DanTri
url = 'https://dantri.com.vn/giao-duc/nhieu-truong-dai-hoc-tang-chi-tieu-nam-2025-20250519064752289.htm'
soup = BeautifulSoup(requests.get(url).content, 'html.parser')

for el in soup.find_all(class_=re.compile(r'author|date')):
    txt = el.text.strip()
    if len(txt) < 200:
        print(f'DanTri {el.name}.{el.get("class")}: {txt[:100]}')

# Also try data-date attribute
for el in soup.find_all(attrs={"data-date": True}):
    print(f'DanTri data-date: {el.get("data-date")}')
