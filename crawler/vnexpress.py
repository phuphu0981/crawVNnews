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


class VNExpressCrawler(BaseCrawler):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.logger = log.get_logger(name=__name__)
        self.article_type_dict = {
            0: "thoi-su",
            1: "du-lich",
            2: "the-gioi",
            3: "kinh-doanh",
            4: "khoa-hoc",
            5: "giai-tri",
            6: "the-thao",
            7: "phap-luat",
            8: "giao-duc",
            9: "suc-khoe",
            10: "doi-song"
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

        title = soup.find("h1", class_="title-detail") 
        if title == None:
            return None, None, None
        title = title.text

        # some sport news have location-stamp child tag inside description tag
        description = (get_text_from_tag(p) for p in soup.find("p", class_="description").contents)
        paragraphs = (get_text_from_tag(p) for p in soup.find_all("p", class_="Normal"))

        return title, description, paragraphs

    def extract_date(self, soup):
        """Extract date from VNExpress meta pubdate tag."""
        meta = soup.find('meta', attrs={'name': 'pubdate'})
        if meta:
            return meta.get('content')
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

        title = soup.find("h1", class_="title-detail")
        if title is None:
            return False
        title = title.text

        description = (get_text_from_tag(p) for p in soup.find("p", class_="description").contents)
        paragraphs = (get_text_from_tag(p) for p in soup.find_all("p", class_="Normal"))

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
        page_url = f"https://vnexpress.net/{article_type}-p{page_number}"
        content = requests.get(page_url).content
        soup = BeautifulSoup(content, "html.parser")
        titles = soup.find_all(class_="title-news")

        if (len(titles) == 0):
            self.logger.info(f"Couldn't find any news in {page_url} \nMaybe you sent too many requests, try using less workers")

        articles_urls = list()

        for title in titles:
            link = title.find_all("a")[0]
            articles_urls.append(link.get("href"))
    
        return articles_urls
