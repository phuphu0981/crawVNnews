import requests
import sys
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


class DanTriCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.logger = log.get_logger(name=__name__)
        self.base_url = "https://dantri.com.vn"
        self.article_type_dict = {
            0: "xa-hoi",
            1: "the-gioi",
            2: "kinh-doanh",
            3: "bat-dong-san",
            4: "the-thao",
            5: "lao-dong-viec-lam",
            6: "tam-long-nhan-ai",
            7: "suc-khoe",
            8: "van-hoa",
            9: "giai-tri",
            10: "suc-manh-so",
            11: "giao-duc",
            12: "an-sinh",
            13: "phap-luat"
        }   
        
    def extract_content(self, url: str) -> tuple:
        """
        Extract title, description and paragraphs from url
        @param url (str): url to crawl
        @return title (str)
        @return description (generator)
        @return paragraphs (generator)
        """
        content = requests.get(url).content
        soup = BeautifulSoup(content, "html.parser")

        title = soup.find("h1", class_="title-page detail") 
        if title == None:
            return None, None, None
        title = title.text

        description = (get_text_from_tag(p) for p in soup.find("h2", class_="singular-sapo").contents)
        content = soup.find("div", class_="singular-content")
        paragraphs = (get_text_from_tag(p) for p in content.find_all("p"))

        return title, description, paragraphs

    def extract_date(self, soup):
        """Extract date from DanTri. Try JSON-LD first, then URL pattern."""
        import json as _json
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = _json.loads(script.string or '')
                if isinstance(data, dict) and 'datePublished' in data:
                    return data['datePublished']
            except (ValueError, TypeError):
                pass
        # Fallback: extract from author-time class
        import re
        time_el = soup.find(class_=re.compile(r'author-time|date'))
        if time_el:
            return time_el.text.strip()
        return None

    def write_content(self, url: str, output_fpath: str) -> bool:
        """
        From url, extract title, description and paragraphs then write in output_fpath
        @param url (str): url to crawl
        @param output_fpath (str): file path to save crawled result
        @return (bool): True if crawl successfully and otherwise
        """
        content = requests.get(url).content
        soup = BeautifulSoup(content, "html.parser")

        # Date filtering
        date_str = self.extract_date(soup)
        article_date = parse_article_date(date_str)
        if not is_date_in_range(article_date, self._date_from, self._date_to):
            return True  # Skip silently, not an error

        title = soup.find("h1", class_="title-page detail")
        if title is None:
            return False
        title = title.text

        description = (get_text_from_tag(p) for p in soup.find("h2", class_="singular-sapo").contents)
        content_div = soup.find("div", class_="singular-content")
        paragraphs = (get_text_from_tag(p) for p in content_div.find_all("p"))

        with open(output_fpath, "w", encoding="utf-8") as file:
            file.write(title + "\n")
            for p in description:
                file.write(p + "\n")
            for p in paragraphs:                     
                file.write(p + "\n")

        # Download images
        images = extract_image_urls(soup)
        if images:
            img_dir = output_fpath.replace('.txt', '_images')
            downloaded = download_images(images, img_dir)
            if downloaded:
                meta_path = output_fpath.replace('.txt', '_images.json')
                import json
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(downloaded, f, ensure_ascii=False, indent=2)

        return True
    
    def get_urls_of_type_thread(self, article_type, page_number):
        """" Get urls of articles in a specific type in a page"""
        page_url = f"https://dantri.com.vn/{article_type}/trang-{page_number}.htm"
        content = requests.get(page_url).content
        soup = BeautifulSoup(content, "html.parser")
        titles = soup.find_all(class_="article-title")

        if (len(titles) == 0):
            self.logger.info(f"Couldn't find any news in {page_url} \nMaybe you sent too many requests, try using less workers")
            

        articles_urls = list()

        for title in titles:
            link = title.find_all("a")[0]
            articles_urls.append(self.base_url + link.get("href"))
    
        return articles_urls
