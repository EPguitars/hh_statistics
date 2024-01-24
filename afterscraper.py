""" 
This module scrapes all the data with is not scraped by the main scraper. 
And it sets is_archived to True for all the vacancies which are not actual anymore.
"""
import logging
from datetime import datetime
import asyncio

from aiolimiter import AsyncLimiter
from selectolax.parser import HTMLParser
from rich import print

from db_operations import MongoConnector
from html_scraper import get_html
from models import VacancyRAW

async def get_not_scraped_items(db_manager: MongoConnector):
    """
    This function gets all the items which are not scraped yet.
    """
    # get all the items which are not scraped and not archived
    items = db_manager.collection.find({"is_actual": False, "is_archived": False})
    
    return [VacancyRAW(**item) async for item in items]

async def process_batch(batch):
    """ function to process batch of items """
    start = datetime.now()
    await asyncio.gather(*batch)
    end = datetime.now()
    print(f"BATCH DONE, time spended - {end - start}")


def detect_is_archived(html):
    """ function to detect if the vacancy is archived """
    selectolax = HTMLParser(html)
    archived_selector = selectolax.css_first("div.vacancy-section > h2")

    if archived_selector:
        
        if "архив" in archived_selector.text().lower():
            return True
        else:
            return False

    else:
        return False


async def update_statuses(item: VacancyRAW, 
                          db_manager: MongoConnector, 
                          limiter: AsyncLimiter):
    """ function to update statuses of items """
    html = await get_html(item.url, "httpx", limiter)
    
    if not html:
        html = await get_html(item.url, "browser", limiter)

    if not html:
        return None

    is_archived = detect_is_archived(html)

    if is_archived:
        await db_manager.set_is_archived_true(item.source_id)
    
    else:
        await db_manager.set_is_actual_true(item.source_id)


async def update_rest_items(db_manager: MongoConnector, limiter: AsyncLimiter):
    """
    This function updates all the items which are not actual anymore.
    """
    # get all the items which are not actual and not archived
    items = await get_not_scraped_items(db_manager)

    tasks = []

    for item in items:
        tasks.append(update_statuses(item, db_manager, limiter))

    total_tasks = len(tasks)
    batch_size = 100
    tasks_left = total_tasks
    print(f"TOTAL TASKS: {total_tasks}")

    for i in range(0, total_tasks, batch_size):
        batch = tasks[i:i+batch_size]
        await process_batch(batch)
        tasks_left -= batch_size
        logging.info(f"TASKS LEFT: {0 if tasks_left <= 0 else tasks_left}")

 # ===========================================================================   

async def fast_test():
    """ function to test the module """
    url = "https://hh.ru/vacancy/86631893"
    limiter = AsyncLimiter(10, 1)
    html = await get_html(url, "httpx", limiter)
    is_archived = detect_is_archived(html)
    print(is_archived)

if __name__ == "__main__":
    db_manager = MongoConnector()
    limiter = AsyncLimiter(10, 1)
    asyncio.run(update_rest_items(db_manager, limiter))