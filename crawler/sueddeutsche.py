import requests
import sys
import re
import json
from pathlib import Path

from bs4 import BeautifulSoup

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]  # root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH

from logger import log
from crawler.base_crawler import BaseCrawler
from utils.bs4_utils import get_text_from_tag
from utils.date_utils import parse_article_date, is_date_in_range
from utils.image_utils import extract_image_urls, download_images


class SueddeutscheCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.logger = log.get_logger(name=__name__)
        self.base_url = "https://www.sueddeutsche.de"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.article_type_dict = {
            0: "politik",
            1: "wirtschaft",
            2: "panorama",
            3: "sport",
            4: "kultur",
            5: "wissen",
            6: "digital",
            7: "karriere",
            8: "reise",
            9: "auto",
        }

    def extract_content(self, url: str) -> tuple:
        """
        Extract title, description and paragraphs from url
        @param url (str): url to crawl
        @return title (str)
        @return description (generator)
        @return paragraphs (generator)
        """
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                return None, None, None
            content = resp.content
        except Exception as e:
            self.logger.error(f"Failed to fetch content from {url}: {e}")
            return None, None, None

        soup = BeautifulSoup(content, "html.parser")

        title_tag = soup.find("h1") or soup.find(attrs={"itemprop": "headline"})
        if title_tag is None:
            return None, None, None
        title = title_tag.text.strip()

        # Description / Sapo
        desc_tag = (
            soup.find("p", attrs={"itemprop": "description"}) or
            soup.find(attrs={"data-testid": "teaser-text"}) or
            soup.find("p", class_="sz-article-intro") or
            soup.find("div", class_="sz-article-intro")
        )
        if desc_tag:
            description = (get_text_from_tag(p) for p in desc_tag.contents if p)
        else:
            description = iter([])

        # Body paragraphs
        body_container = (
            soup.find(attrs={"itemprop": "articleBody"}) or
            soup.find(attrs={"data-testid": "article-body"}) or
            soup.find("article") or
            soup.find("section", class_="body")
        )
        if body_container:
            paragraphs = (get_text_from_tag(p) for p in body_container.find_all("p"))
        else:
            # Fallback
            paragraphs = (get_text_from_tag(p) for p in soup.find_all("p") if len(p.text) > 40)

        return title, description, paragraphs

    def extract_date(self, soup):
        """Extract date from Sueddeutsche Zeitung JSON-LD or meta tags."""
        # 1. Try JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                if isinstance(data, dict):
                    if 'datePublished' in data:
                        return data['datePublished']
                    elif '@graph' in data:
                        for item in data['@graph']:
                            if isinstance(item, dict) and 'datePublished' in item:
                                return item['datePublished']
            except (ValueError, TypeError):
                pass

        # 2. Try meta tags
        meta = (
            soup.find('meta', attrs={'property': 'article:published_time'}) or
            soup.find('meta', attrs={'name': 'date'}) or
            soup.find('meta', attrs={'itemprop': 'datePublished'})
        )
        if meta:
            return meta.get('content')

        # 3. Try time element
        time_el = soup.find('time')
        if time_el and time_el.get('datetime'):
            return time_el.get('datetime')

        return None

    def write_content(self, url: str, output_fpath: str) -> bool:
        """
        From url, extract title, description and paragraphs then write in output_fpath
        @param url (str): url to crawl
        @param output_fpath (str): file path to save crawled result
        @return (bool): True if crawl successfully and otherwise
        """
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                return False
            content = resp.content
        except Exception as e:
            self.logger.error(f"Failed to fetch content in write_content for {url}: {e}")
            return False

        soup = BeautifulSoup(content, "html.parser")

        # Date filtering
        date_str = self.extract_date(soup)
        article_date = parse_article_date(date_str)
        if not is_date_in_range(article_date, self._date_from, self._date_to):
            return True  # Skip silently, not an error

        title_tag = soup.find("h1") or soup.find(attrs={"itemprop": "headline"})
        if title_tag is None:
            return False
        title = title_tag.text.strip()

        desc_tag = (
            soup.find("p", attrs={"itemprop": "description"}) or
            soup.find(attrs={"data-testid": "teaser-text"}) or
            soup.find("p", class_="sz-article-intro") or
            soup.find("div", class_="sz-article-intro")
        )
        if desc_tag:
            description = [get_text_from_tag(p) for p in desc_tag.contents if p]
        else:
            description = []

        body_container = (
            soup.find(attrs={"itemprop": "articleBody"}) or
            soup.find(attrs={"data-testid": "article-body"}) or
            soup.find("article") or
            soup.find("section", class_="body")
        )
        if body_container:
            paragraphs = [get_text_from_tag(p) for p in body_container.find_all("p")]
        else:
            paragraphs = [get_text_from_tag(p) for p in soup.find_all("p") if len(p.text) > 40]

        with open(output_fpath, "w", encoding="utf-8") as file:
            file.write(title + "\n")
            for p in description:
                if p:
                    file.write(p.strip() + "\n")
            for p in paragraphs:
                if p:
                    file.write(p.strip() + "\n")

        # Download images
        images = extract_image_urls(soup)
        if images:
            img_dir = output_fpath.replace('.txt', '_images')
            downloaded = download_images(images, img_dir)
            if downloaded:
                meta_path = output_fpath.replace('.txt', '_images.json')
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(downloaded, f, ensure_ascii=False, indent=2)

        return True

    def get_urls_of_type_thread(self, article_type, page_number):
        """" Get urls of articles in a specific type in a page"""
        if page_number == 1:
            page_url = f"https://www.sueddeutsche.de/{article_type}"
        else:
            page_url = f"https://www.sueddeutsche.de/{article_type}?page={page_number}"

        try:
            resp = requests.get(page_url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                self.logger.error(f"Failed to fetch category page: {page_url} Status: {resp.status_code}")
                return []
            content = resp.content
        except Exception as e:
            self.logger.error(f"Exception fetching category page {page_url}: {e}")
            return []

        soup = BeautifulSoup(content, "html.parser")
        
        # Look for article links
        # Sueddeutsche articles usually have links containing "/politik/", "/wirtschaft/", etc.
        # Let's find all 'a' tags with href containing the article type.
        articles_urls = list()
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a.get("href")
            # Filter standard article link patterns
            # Standard SZ article links look like: https://www.sueddeutsche.de/politik/us-wahl-trump-1.12345 or starting with /politik/
            # Ignore index, pagination, or overview pages
            if not href:
                continue

            # Standardize relative paths
            full_url = href
            if href.startswith("/"):
                full_url = self.base_url + href

            # Verify it's an article under the specific category
            # Ensure it contains article-like identifier (usually ending in a number or containing a hyphen and unique id)
            # Avoid the category page itself or main category page, query params, etc.
            if f"/{article_type}/" in full_url or f"/{article_type}-" in full_url:
                if any(x in full_url for x in ["?page=", "/index.html", "/archiv", "javascript:", "#"]):
                    continue
                # Simple check for unique article links
                # Most articles are longer URLs with descriptive slugs
                slug = full_url.replace(f"https://www.sueddeutsche.de/{article_type}/", "")
                if len(slug) > 10 and full_url not in seen:
                    seen.add(full_url)
                    articles_urls.append(full_url)

        if len(articles_urls) == 0:
            self.logger.info(f"Couldn't find any news in {page_url} \nMaybe you sent too many requests, try using less workers")

        return articles_urls
