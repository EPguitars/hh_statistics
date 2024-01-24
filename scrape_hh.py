# define a data structure
# scrape from a list of categories
# first request to check the amount of pages
# then scrape all pages
import asyncio
import logging
from datetime import datetime

from rich.logging import RichHandler
from rich import print
import aiolimiter

from html_scraper import get_html
from parsers import parse_serp_page, parse_pagination, generate_pages
from search_words import search_words
from validator import scrape_additional_data
from db_operations import MongoConnector
from afterscraper import update_rest_items

limiter = aiolimiter.AsyncLimiter(5, 1)
browser_semaphore =  asyncio.Semaphore(10)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s",
                    handlers=[RichHandler()])


async def run_hh_scraper(db_manager: MongoConnector):

    for word in search_words:
        url = f"https://hh.ru/search/vacancy?text={word}&salary=&ored_clusters=true&hhtmFrom=vacancy_search_list&hhtmFromLabel=vacancy_search_line"
        
        # First get a first page to detect pagination
        first_html = await get_html(url, "httpx", limiter)
        
        if not first_html:
            first_html = await get_html(url, "browser", browser_semaphore)

        if not first_html:
            logging.error("No html received")
            continue

        pages_amount = parse_pagination(first_html)
        pages_urls = generate_pages(url, pages_amount, word)
        tasks = []
        
        for page in pages_urls:
            tasks.append(get_html(page, "browser", browser_semaphore))

        pages_htmls = await asyncio.gather(*tasks)
        parsed_items = []

        if pages_htmls:
            for html in pages_htmls:
                if html:
                    parsed_items.append(parse_serp_page(html, word))

        if parsed_items:
            for block in parsed_items:
                tasks = []
                
                if block:
                    for item in block:
                        if item:
                            tasks.append(scrape_additional_data(item, db_manager, limiter))
                            
                prepared_to_db = await asyncio.gather(*tasks)        
                tasks = []

                if prepared_to_db:
                    for item in prepared_to_db:
                        if item:
                            tasks.append(db_manager.send_to_db(item))
                    
                    await asyncio.gather(*tasks)
    
    

async def main():
    start_time = datetime.now()
    db_manager = MongoConnector()
    db_manager.ping()

    await db_manager.refresh_is_actual()
    await run_hh_scraper(db_manager)
    await update_rest_items(db_manager, limiter)
    await db_manager.close_connection()
    
    end_time = datetime.now()
    execution_time = end_time - start_time
    logging.info("Parsing is done. Congratulations!")
    print(f"Execution time: {execution_time} seconds")


if __name__ == "__main__":
    # First get a first page to detect pagination
    asyncio.run(main())