import asyncio
import logging

import playwright
import aiolimiter
from playwright.async_api import async_playwright
from playwright.async_api._generated import Request, Route
from undetected_playwright import stealth_async
from rich import print
from tools import playwright_proxy_gen

responses = []
limiter = aiolimiter.AsyncLimiter(10, 1)

# ===================================== HTML RENDERER =====================================

async def scrape_html(url, semaphore):
    global responses
    items = []
    proxy = next(playwright_proxy_gen) 

    async with semaphore:
        async with async_playwright() as p:
            # first set browser
            browser = await p.chromium.launch(headless=True, proxy=proxy)
            context = await browser.new_context(ignore_https_errors=True)
            await stealth_async(context)
            page = await context.new_page()
            await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")
            
            
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("load")
            
            html = await page.inner_html("html")

            logging.info("Succesfully rendered and scraped item's page")
            await browser.close()

            return html



# ===================================== HEADERS SCRAPER =====================================

async def on_request(route: Route, request: Request):
    global responses
    global headers
    global status

    await route.continue_()
    response = await route.request.response()

    if response:
        status = response.status
        print(status)
    if "https://www.titan.co.in/wps/proxy/https/searchweb.titanprodlive.crown.in/search/resources/txapi/v1/store" in request.url:
        headers = request.headers
        print(headers)

async def try_request(url, semaphore):
    global headers
    global responses
    global status
    items = []

    async with semaphore:
        
        async with async_playwright() as p:
            print("Starting browser")
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            # first set browser
            proxy = next(playwright_proxy_gen)  # get proxy
     
            browser = await p.chromium.launch(headless=True, proxy=proxy)
            
            context = await browser.new_context(ignore_https_errors=True, user_agent=user_agent)
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false });")

            await stealth_async(context)
            await context.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")

            await context.route("**", lambda route, request: on_request(route, request))
            page = await context.new_page()
            await page.goto(url, timeout=150000)
            
            # Print browser information
            while not status:
                print("Waiting for status")
                await asyncio.sleep(0.5)

            if status == 407:
                # print(407)
                await browser.close()
                return "proxy error"

            elif status == 200:
                # print(200)
                

                while not headers:
                    # print("waiting for headers")
                    await asyncio.sleep(0.5)
                await browser.close()
                
                return headers["cookie"]


async def scrape_cookies(url, semaphore):
    try:
        result = await try_request(url, semaphore)
    except:
        return await scrape_cookies(url, semaphore)
    
    if result == "proxy error" or not result:
        print("Proxy error when getting cookies, repeating request...")
        return await scrape_cookies(url, semaphore)
    else:
        return result


if __name__ == "__main__":
    url = "https://www.myntra.com/men-clothing?p=7&rf=Discount%20Range%3A20.0_100.0_20.0%20TO%20100.0"
    result = asyncio.run(scrape_cookies(url, limiter))
    print(result)