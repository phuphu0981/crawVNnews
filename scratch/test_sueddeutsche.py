import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawler.sueddeutsche import SueddeutscheCrawler

def main():
    print("Initializing SueddeutscheCrawler...")
    crawler = SueddeutscheCrawler(
        task="url",
        urls_fpath="urls.txt",
        output_dpath="result/test_sz",
        num_workers=1,
        date_from=None,
        date_to=None
    )
    crawler._parse_date_config()

    print("Fetching article URLs from /politik page...")
    urls = crawler.get_urls_of_type_thread("politik", 1)
    if not urls:
        print("Error: No URLs found on /politik page!")
        return

    test_url = urls[0]
    print(f"Testing write_content on URL: {test_url}")
    output_fpath = "result/test_sz/test_article.txt"
    os.makedirs(os.path.dirname(output_fpath), exist_ok=True)
    
    success = crawler.write_content(test_url, output_fpath)
    if success:
        print(f"Crawl succeeded! Saved to {output_fpath}")
        if os.path.exists(output_fpath):
            with open(output_fpath, "r", encoding="utf-8") as f:
                content = f.read()
            print("Content Preview:")
            print("-" * 50)
            # Print first 500 characters
            print(content[:500])
            print("-" * 50)
        else:
            print("Error: output file was not created!")
    else:
        print("Crawl failed!")

if __name__ == "__main__":
    main()
