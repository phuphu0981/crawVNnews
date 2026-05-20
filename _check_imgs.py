import requests
from bs4 import BeautifulSoup

# VNExpress
url = 'https://vnexpress.net/quang-hai-ban-thang-rat-quan-trong-voi-toi-4520944.html'
soup = BeautifulSoup(requests.get(url).content, 'html.parser')

print("=== VNExpress images ===")
for fig in soup.find_all('figure'):
    img = fig.find('img')
    if img:
        src = img.get('data-src') or img.get('src') or ''
        alt = img.get('alt', '')[:60]
        print(f'  src={src[:120]}')
        print(f'  alt={alt}')
    cap = fig.find('figcaption') or fig.find('p', class_='Image')
    if cap:
        print(f'  caption={cap.text.strip()[:80]}')
    print()

# Also check picture/source tags
for pic in soup.find_all('picture'):
    source = pic.find('source')
    if source:
        srcset = source.get('data-srcset') or source.get('srcset') or ''
        print(f'  picture source: {srcset[:120]}')

print("\n=== DanTri images ===")
url2 = 'https://dantri.com.vn/giao-duc/nhieu-truong-dai-hoc-tang-chi-tieu-nam-2025-20250519064752289.htm'
soup2 = BeautifulSoup(requests.get(url2).content, 'html.parser')
content = soup2.find('div', class_='singular-content')
if content:
    for fig in content.find_all('figure'):
        img = fig.find('img')
        if img:
            src = img.get('data-src') or img.get('src') or ''
            print(f'  src={src[:120]}')
        cap = fig.find('figcaption')
        if cap:
            print(f'  caption={cap.text.strip()[:80]}')
        print()

print("\n=== VietNamNet images ===")
url3 = 'https://vietnamnet.vn/apple-co-the-tang-gia-iphone-vi-thue-quan-cua-trump-2403795.html'
soup3 = BeautifulSoup(requests.get(url3).content, 'html.parser')
main = soup3.find('div', class_=['maincontent', 'main-content'])
if main:
    for fig in main.find_all('figure'):
        img = fig.find('img')
        if img:
            src = img.get('data-src') or img.get('src') or ''
            print(f'  src={src[:120]}')
        cap = fig.find('figcaption')
        if cap:
            print(f'  caption={cap.text.strip()[:80]}')
        print()
    # Also check standalone imgs
    for img in main.find_all('img'):
        if not img.find_parent('figure'):
            src = img.get('data-src') or img.get('src') or ''
            if src and 'icon' not in src.lower():
                print(f'  standalone img: {src[:120]}')
