import asyncio
import logging

from bson import ObjectId
from rich import print
from rich.logging import RichHandler
from aiolimiter import AsyncLimiter

from html_scraper import get_html
from selectolax.parser import Selector, HTMLParser
from models import VacancyRAW
from db_operations import MongoConnector

def parse_description(html: Selector) -> str:
    """Parse vacancy description from html"""
    description_selector = html.css_first("div[data-qa='vacancy-description']")

    if description_selector:
        description = description_selector.text()
        return description
    
    else:
        logging.info("No description found")
        return None


def parse_key_skills(html: Selector) -> list:
    skills_selector = html.css("span[data-qa='bloko-tag__text']")
    key_skills = list()

    if skills_selector:
        for skill in skills_selector:
            key_skills.append(skill.text())

    return key_skills


def parse_company_address(html: Selector) -> str:
    address_selector_one = html.css_first("span[data-qa='vacancy-view-raw-address']")
    address_selector_two = html.css_first("p[data-qa='vacancy-view-location']")

    if address_selector_one:
        address = address_selector_one.text()
        return address
    
    if address_selector_two:
        address = address_selector_two.text()
        return address
    
    else:
        logging.info("No address found")
        return None


def parse_company_rating(html: Selector) -> float:
    rating_selector = html.css_first("span[data-qa='employer-rating']")

    if rating_selector:
        rating = rating_selector.text()
        return float(rating)
    
    else:
        logging.info("No rating found")
        return None


def parse_company_reviews(html: Selector) -> int:
    reviews_selector = html.css_first("a[data-qa='vacancy-company-reviews-count']")

    if reviews_selector:
        reviews = reviews_selector.text()
        return int(reviews)
    
    else:
        logging.info("No reviews found")
        return None
    

def parse_company_recommendations(html: Selector) -> int:
    recommendations_selector = html.css_first("a[data-qa='vacancy-company-reviews-recommendations']")

    if recommendations_selector:
        recommendations = recommendations_selector.text()
        return int(recommendations)
    
    else:
        logging.info("No recommendations found")
        return None


def parse_employment_type(html: Selector) -> str:
    employment_type_selector = html.css_first("p[data-qa='vacancy-view-employment-mode']")

    if employment_type_selector:
        employment_type = employment_type_selector.text()
        return employment_type
    
    else:
        logging.info("No employment type found")
        return None

async def scrape_additional_data(item: VacancyRAW, db_connector: MongoConnector, 
                                 limiter: AsyncLimiter):
    # first check in db
    # if It's not in db, then use scraping
    # if it is, just copy data from db
    db_item = await db_connector.find_item_by_id(item.source_id)

    if db_item:
        logging.info("Item is already in db")
        query = {"_id": ObjectId(db_item["_id"])}

        if isinstance(db_item["search_strings"], list):
            if item.search_strings[0] not in db_item["search_strings"]:
                new_word_list = db_item["search_strings"] + item.search_strings
                await db_connector.collection.update_one(query, {"$set": {"search_strings": new_word_list}})

        elif isinstance(db_item["search_strings"], str):
            if item.search_strings[0] != db_item["search_strings"]:
                new_word_list = [db_item["search_strings"]] + item.search_strings
                await db_connector.collection.update_one(query, {"$set": {"search_strings": new_word_list}})

        await db_connector.set_is_actual_true(item.source_id)
        return None
    
    else:
        html = await get_html(item.url, "httpx", limiter)
        
        if html:
            selectolax = HTMLParser(html)
        
        else:
            return None

        item.description = parse_description(selectolax)
        item.key_skills = parse_key_skills(selectolax)
        item.company_address = parse_company_address(selectolax)
        
        item.employment_type = parse_employment_type(selectolax)

        return item
        

if __name__ == "__main__":
    
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s",
                        handlers=[RichHandler()])

    test_item = VacancyRAW(
        title='Senior Data analyst',
        salary_type='no numbers',
        salary=None,
        url='https://hh.ru/vacancy/91586327',
        city='Москва',
        experience=[3, 6],
        fresh=False,
        is_actual=True,
        company_name='ООО Ок Софт',
        company_page='https://hh.ru/employer/5692713?hhtmFrom=vacancy_search_list',
        search_string='python',
        when_scraped='15-01-2024 04:01:44',
        company_address=None,
        description=None,
        employment_type=None,
        source_id='91535831',
        key_skills=None
    )

    limiter = AsyncLimiter(10, 1)

    asyncio.run(scrape_additional_data(test_item, limiter))