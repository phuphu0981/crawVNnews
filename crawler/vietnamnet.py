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


class VietNamNetCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.logger = log.get_logger(name=__name__)
        self.base_url = "https://vietnamnet.vn"
        self.article_type_dict = {
            0: "thoi-su",
            1: "kinh-doanh",
            2: "the-thao",
            3: "van-hoa",
            4: "giai-tri",
            5: "the-gioi",
            6: "doi-song",
            7: "giao-duc",
            8: "suc-khoe",
            9: "thong-tin-truyen-thong",
            10: "phap-luat",
            11: "oto-xe-may",
            12: "bat-dong-san",
            13: "du-lich",
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

        title_tag = soup.find("h1", class_="content-detail-title") 
        desc_tag = soup.find("h2", class_=["content-detail-sapo", "sm-sapo-mb-0"])
        p_tag = soup.find("div", class_=["maincontent", "main-content"])

        if [var for var in (title_tag, desc_tag, p_tag) if var is None]:
            return None, None, None
        
        title = title_tag.text
        description = (get_text_from_tag(p) for p in desc_tag.contents)
        paragraphs = (get_text_from_tag(p) for p in p_tag.find_all("p"))

        return title, description, paragraphs

    def extract_date(self, soup):
        """Extract date from VietNamNet JSON-LD or dataLayer script."""
        import json as _json, re
        # Try JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = _json.loads(script.string or '')
                if isinstance(data, dict) and 'datePublished' in data:
                    return data['datePublished']
            except (ValueError, TypeError):
                pass
        # Fallback: dataLayer ArticlePublishDate
        for script in soup.find_all('script'):
            txt = script.string or ''
            m = re.search(r"ArticlePublishDate['\"]?\s*:\s*['\"]([^'\"]+)", txt)
            if m:
                return m.group(1)
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

        title_tag = soup.find("h1", class_="content-detail-title")
        desc_tag = soup.find("h2", class_=["content-detail-sapo", "sm-sapo-mb-0"])
        p_tag = soup.find("div", class_=["maincontent", "main-content"])

        if [var for var in (title_tag, desc_tag, p_tag) if var is None]:
            return False

        title = title_tag.text
        description = (get_text_from_tag(p) for p in desc_tag.contents)
        paragraphs = (get_text_from_tag(p) for p in p_tag.find_all("p"))

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
        page_url = f"https://vietnamnet.vn/{article_type}-page{page_number}"
        content = requests.get(page_url).content
        soup = BeautifulSoup(content, "html.parser")
        titles = soup.find_all(class_=["horizontalPost__main-title", "vnn-title", "title-bold"])

        if (len(titles) == 0):
            self.logger.info(f"Couldn't find any news in {page_url} \nMaybe you sent too many requests, try using less workers")
            
        articles_urls = list()

        for title in titles:
            full_url = title.find_all("a")[0].get("href")
            if self.base_url not in full_url:
                full_url = self.base_url + full_url
            articles_urls.append(full_url)
    
        return articles_urls
