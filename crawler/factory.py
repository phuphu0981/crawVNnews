from .vnexpress import VNExpressCrawler
from .dantri import DanTriCrawler
from .vietnamnet import VietNamNetCrawler
from .sueddeutsche import SueddeutscheCrawler

WEBNAMES = {"vnexpress": VNExpressCrawler,
            "dantri": DanTriCrawler,
            "vietnamnet": VietNamNetCrawler,
            "sueddeutsche": SueddeutscheCrawler}

def get_crawler(webname, **kwargs):
    crawler = WEBNAMES[webname](**kwargs)
    return crawler