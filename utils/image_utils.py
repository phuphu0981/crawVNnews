"""Utility functions for downloading and extracting images from articles."""
import os
import re
import logging
import requests


logger = logging.getLogger(__name__)


def extract_image_urls(soup):
    """
    Extract all article image URLs from a BeautifulSoup object.
    Works across VNExpress, DanTri, VietNamNet.
    Returns list of dicts: [{"url": str, "caption": str}, ...]
    """
    images = []
    seen_urls = set()

    for fig in soup.find_all('figure'):
        img = fig.find('img')
        if not img:
            continue

        src = img.get('data-src') or img.get('src') or ''
        # Skip tiny placeholders (base64 or very short)
        if not src or src.startswith('data:') or len(src) < 20:
            continue
        # Skip icons/logos
        if any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'emoji']):
            continue

        if src in seen_urls:
            continue
        seen_urls.add(src)

        caption = ''
        figcap = fig.find('figcaption')
        if figcap:
            caption = figcap.get_text(strip=True)
        if not caption:
            caption = img.get('alt', '')

        images.append({"url": src, "caption": caption})

    # Fallback: check standalone imgs in article body if no figures found
    if not images:
        article_body = (
            soup.find('article') or
            soup.find('div', class_='singular-content') or
            soup.find('div', class_=re.compile(r'maincontent|main-content'))
        )
        if article_body:
            for img in article_body.find_all('img'):
                src = img.get('data-src') or img.get('src') or ''
                if not src or src.startswith('data:') or len(src) < 20:
                    continue
                if any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'emoji']):
                    continue
                if src in seen_urls:
                    continue
                seen_urls.add(src)
                images.append({"url": src, "caption": img.get('alt', '')})

    return images


def download_images(image_list, output_dir):
    """
    Download images to output_dir.
    Returns list of dicts: [{"filename": str, "caption": str, "url": str}, ...]
    """
    if not image_list:
        return []

    os.makedirs(output_dir, exist_ok=True)
    downloaded = []

    for i, img_info in enumerate(image_list):
        url = img_info["url"]
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue

            # Determine extension from content-type or URL
            content_type = resp.headers.get('Content-Type', '')
            if 'webp' in content_type:
                ext = '.webp'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            else:
                ext = '.jpg'

            filename = f"img_{i + 1}{ext}"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, 'wb') as f:
                f.write(resp.content)

            downloaded.append({
                "filename": filename,
                "caption": img_info.get("caption", ""),
                "url": url,
            })
        except Exception as e:
            logger.debug(f"Failed to download image {url}: {e}")

    return downloaded
