from abc import ABC, abstractmethod
import concurrent.futures
from datetime import datetime

from tqdm import tqdm

from utils.utils import init_output_dirs, create_dir, read_file
from utils.date_utils import parse_article_date, is_date_in_range

class BaseCrawler(ABC):

    @abstractmethod
    def extract_content(self, url):
        """
        Extract title, description and paragraphs from url
        @param url (str): url to crawl
        @return title (str)
        @return description (generator)
        @return paragraphs (generator)
        """

        title = str()
        description = list()
        paragraphs = list()

        return title, description, paragraphs

    @abstractmethod
    def extract_date(self, soup):
        """
        Extract publication date string from a BeautifulSoup object.
        @param soup: BeautifulSoup object of the article page
        @return date_str (str or None): date string in any parseable format
        """
        return None

    @abstractmethod
    def write_content(self, url, output_fpath):
        """
        From url, extract title, description and paragraphs then write in output_fpath
        @param url (str): url to crawl
        @param output_fpath (str): file path to save crawled result
        @return (bool): True if crawl successfully and otherwise
        """

        return True
    
    @abstractmethod
    def get_urls_of_type_thread(self, article_type, page_number):
        """" Get urls of articles in a specific type in a page"""

        articles_urls = list()

        return articles_urls

    def _parse_date_config(self):
        """Parse date_from/date_to from config strings to date objects."""
        df = getattr(self, 'date_from', None)
        dt = getattr(self, 'date_to', None)
        self._date_from = None
        self._date_to = None
        if df:
            try:
                self._date_from = datetime.strptime(df, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
        if dt:
            try:
                self._date_to = datetime.strptime(dt, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

    def start_crawling(self):
        self._parse_date_config()
        error_urls = list()
        if self.task=="url":
            error_urls = self.crawl_urls(self.urls_fpath, self.output_dpath)
        elif self.task=="type":
            error_urls = self.crawl_types()

        self.logger.info(f"The number of failed URL: {len(error_urls)}")

    def crawl_urls(self, urls_fpath, output_dpath):
        """
        Crawling contents from a list of urls
        Returns:
            list of failed urls
        """
        self.logger.info(f"Start crawling urls from {urls_fpath} file...")
        create_dir(output_dpath)
        urls = list(read_file(urls_fpath))
        num_urls = len(urls)
        # number of digits in an integer
        self.index_len = len(str(num_urls))

        args = ([output_dpath]*num_urls, urls, range(num_urls))
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            results = list(tqdm(executor.map(self.crawl_url_thread, *args), total=num_urls, desc="URLs"))
    
        self.logger.info(f"Saving crawling result into {output_dpath} directory...")
        return [result for result in results if result is not None]

    def crawl_url_thread(self, output_dpath, url, index):
        """ Crawling content of the specific url """
        file_index = str(index + 1).zfill(self.index_len)
        output_fpath = "".join([output_dpath, "/url_", file_index, ".txt"])
        is_success = self.write_content(url, output_fpath)
        if (not is_success):
            self.logger.debug(f"Crawling unsuccessfully: {url}")
            return url
        else:
            return None

    def crawl_types(self):
        """ Crawling contents of a specific type or all types """
        urls_dpath, results_dpath = init_output_dirs(self.output_dpath)

        if self.article_type == "all":
            error_urls = self.crawl_all_types(urls_dpath, results_dpath)
        else:
            error_urls = self.crawl_type(self.article_type, urls_dpath, results_dpath)
        return error_urls

    def crawl_type(self, article_type, urls_dpath, results_dpath):
        """" Crawl total_pages of articles in specific type """
        self.logger.info(f"Crawl articles type {article_type}")
        error_urls = list()
        
        # getting urls
        self.logger.info(f"Getting urls of {article_type}...")
        articles_urls = self.get_urls_of_type(article_type)
        articles_urls_fpath = "/".join([urls_dpath, f"{article_type}.txt"])
        with open(articles_urls_fpath, "w") as urls_file:
            urls_file.write("\n".join(articles_urls)) 

        # crawling urls
        self.logger.info(f"Crawling from urls of {article_type}...")
        results_type_dpath = "/".join([results_dpath, article_type])
        error_urls = self.crawl_urls(articles_urls_fpath, results_type_dpath)
        
        return error_urls

    def crawl_all_types(self, urls_dpath, results_dpath):
        """" Crawl articles from all categories with total_pages per category """
        total_error_urls = list()
        
        num_types = len(self.article_type_dict) 
        for i in range(num_types):
            article_type = self.article_type_dict[i]
            error_urls = self.crawl_type(article_type, urls_dpath, results_dpath)
            self.logger.info(f"The number of failed {article_type} URL: {len(error_urls)}")
            self.logger.info("-" * 79)
            total_error_urls.extend(error_urls)
        
        return total_error_urls

    def get_urls_of_type(self, article_type):
        """" Get urls of articles in a specific type """
        articles_urls = list()
        args = ([article_type]*self.total_pages, range(1, self.total_pages+1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            results = list(tqdm(executor.map(self.get_urls_of_type_thread, *args), total=self.total_pages, desc="Pages"))

        articles_urls = sum(results, [])
        articles_urls = list(set(articles_urls))
    
        return articles_urls
