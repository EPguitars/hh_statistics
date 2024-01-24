import re
import asyncio
import logging
import hashlib
import unicodedata
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime

from rich import print
from selectolax.parser import HTMLParser, Selector

from models import VacancyRAW
from transformator import detect_currency, split_salary, convert_currency, get_currency_rates

VACANCY_BASE_URL = "https://hh.ru/vacancy/"
rates = asyncio.run(get_currency_rates())

def generate_pages(url: str, pages_amount: int, searched_string: str):
    pages = []
    for i in range(pages_amount):
        page_url = f"https://hh.ru/search/vacancy?text={searched_string}&area=1&page=" + str(i)
        pages.append(page_url)
    
    return pages


def parse_title(selector: Selector):
    title_selector = selector.css_first("span.serp-item__title")
    
    if title_selector:
        raw_title = title_selector.text()
        title = unicodedata.normalize('NFKD', raw_title)\
        .encode().decode('utf-8')
        
        return title
    
    else:
        logging.warning("No title found")
        return None


def parse_salary(selector: Selector):
    salary_selector = selector.css_first("span[data-qa='vacancy-serp__vacancy-compensation']")
    
    if salary_selector:
        
        raw_salary = salary_selector.text()
        salary = unicodedata.normalize('NFKD', raw_salary)\
        .encode().decode('utf-8')
        
        return salary
    
    else:
        logging.warning("No salary found")
        return None


def detect_salary_type(salary: str):
    if salary is None:
        return "no numbers"
    
    elif salary.lower() == "по договорённости":
        return "no numbers"
    
    elif "–" in salary:
        return "fork"
    
    elif not salary:
        return "no numbers"

    elif "от" in salary.lower():
        return "min"
    
    elif "до" in salary.lower():
        return "max"

    else:
        return "fixed"


def parse_url(selector: Selector):
    """ Get the url of a vacancy from a selector"""
    url_selector = selector.css_first("a.bloko-link")
    
    if url_selector:
        url = url_selector.attributes["href"]
        return url
    
    else:
        logging.warning("No url found")
        return None


def parse_id(selector: Selector):
    """ Get the id of a vacancy from a selector"""
    id_selector = selector.css_first("a[data-qa='vacancy-serp__vacancy_response']")
    
    if id_selector:
        url = id_selector.attributes["href"]
        id = parse_qs(urlparse(url).query).get("vacancyId")[0]
        
        return id
        
    
    else:
        logging.warning("No id found")
        return None


def parse_city(selector: Selector):
    city_selector = selector.css_first("div[data-qa='vacancy-serp__vacancy-address']")
    
    if city_selector:
        raw_city = city_selector.text()
        city = unicodedata.normalize('NFKD', raw_city)\
        .encode().decode('utf-8')
        
        return city
    
    else:
        logging.warning("No city found")
        return None


def parse_experience(selector: Selector) -> list:
    """ Get the experience of a vacancy from a selector"""
    experience_selector = selector.css_first("div[data-qa='vacancy-serp__vacancy-work-experience']")
    
    if experience_selector:
        experience_string = experience_selector.text()
        
        if "без опыта" in experience_string.lower():
            return [0]
        
        experience_list = [int(match) for match in re.findall(r'\d+', experience_string)]

        if len(experience_list) == 1:
            return experience_list
        
        elif len(experience_list) == 2:
            return experience_list
        
        else:
            logging.warning("Invalid experience string")
            return None

    else:
        logging.warning("No experience found")
        return None


def is_fresh(selector: Selector):
    fresh_selector = selector.css_first("span[data-qa='vacancy-label-be-first']")
    
    if fresh_selector:
        raw_fresh = fresh_selector.text()
        fresh = unicodedata.normalize('NFKD', raw_fresh)\
        .encode().decode('utf-8')
        
        if "откликнитесь среди первых" in fresh.lower():
            return True
        
        else:
            return False
    
    else:
        return False


def parse_company_name(selector: Selector):
    company_name_selector = selector.css_first("a[data-qa='vacancy-serp__vacancy-employer']")
    
    if company_name_selector:
        raw_company_name = company_name_selector.text()
        company_name = unicodedata.normalize('NFKD', raw_company_name)\
        .encode().decode('utf-8')
        
        return company_name
    
    else:
        logging.warning("No company name found")
        return None


def parse_company_page_url(selector: Selector):
    company_page_selector = selector.css_first("a[data-qa='vacancy-serp__vacancy-employer']")
    
    if company_page_selector:
        url = company_page_selector.attributes["href"]
        company_page = urljoin(VACANCY_BASE_URL, url)
        
        return company_page
    
    else:
        logging.warning("No company page url found")
        return None


def parse_serp_item(selector: Selector, search_string) -> VacancyRAW:
    salary = parse_salary(selector)
    salary_type = detect_salary_type(salary)
    salary_currency = detect_currency(salary) if salary else "RUB"
    salary_min, salary_max = split_salary(salary_type, salary, salary_currency)
    salary_min, salary_max = convert_currency(salary_currency, salary_min, salary_max, rates)
    id = parse_id(selector)

    if not id:
        return None
    
    parsed_item = VacancyRAW(
        title=parse_title(selector),
        salary_type=salary_type,
        salary=salary,
        url= VACANCY_BASE_URL + id,
        city=parse_city(selector),
        experience=parse_experience(selector),
        fresh=is_fresh(selector),
        is_actual=True,
        company_name=parse_company_name(selector),
        company_page=parse_company_page_url(selector),
        source_id=id,
        search_strings=[search_string.lower()],
        when_scraped=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        company_address=None,
        description=None,
        employment_type=None,
        key_skills=None,
        is_scraped=None,
        is_archived=False,
        responded=False,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency
    
    )
    
    return parsed_item

def parse_serp_page(html: str, search_string: str):
    """
    Parse the html of a search engine results page (SERP) and extract all the urls from it.
    """
    selectolax = HTMLParser(html)
    items_selectors = selectolax.css("div.serp-item")
    
    parsed_items = []

    for selector in items_selectors:
        parsed_item = parse_serp_item(selector, search_string)
        parsed_items.append(parsed_item)
    
    
    return parsed_items


def parse_pagination(html: str):
    """
    Parse the html of a search engine results page (SERP) and extract all the urls from it.
    """
    selectolax = HTMLParser(html)
    pagination_selector = selectolax.css_first("div[data-qa='pager-block']")
    
    if pagination_selector:
        pages_amount = int(pagination_selector.css("a[data-qa='pager-page']")[-1].text())
        return pages_amount
    
    else:
        logging.warning("No pagination found")
        return 1

if __name__ == "__main__":
    pass