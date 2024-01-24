import logging

import httpx
import playwright

from headers import headers
from tools import proxy_gen, playwright_proxy_gen
from automated_browser import scrape_html

async def get_html_httpx(url, semaphore):

    proxy = next(proxy_gen) 
    async with semaphore:
        async with httpx.AsyncClient(headers=headers, proxies=proxy) as client:
            try:
                response = await client.get(url, timeout=60, follow_redirects=True)
                return response.text

            except (httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                    httpx.ConnectError,
                    httpx.ReadError):
                
                logging.warning("Connection error, retrying request")
                return None
            
            except httpx.ProxyError:
                
                logging.warning("Proxy error when getting page urls")
                return None
                    
            except Exception as exc:
                logging.warning("Exception when scraping pages : %s", exc)
                return None


async def get_html(url, parameter, semaphore, attempts=11):
    
    if parameter == "httpx":

        html = await get_html_httpx(url, semaphore)
        
        if not html:
            if attempts > 0:
                logging.warning("Retrying request")
                return await get_html(url, parameter, semaphore, attempts - 1)
            
        else:
            return html        


    elif parameter == "browser":
        try:
            html = await scrape_html(url, semaphore)
        
        except playwright._impl._errors.TimeoutError:
            if attempts > 0:
                logging.warning("Retrying request")
                return await get_html(url, parameter, semaphore, attempts - 1)

            else:
                return None
        
        except playwright._impl._errors.Error:
            if attempts > 0:
                logging.warning("Retrying request")
                return await get_html(url, parameter, semaphore, attempts - 1)

            else:
                return None
            
        if not html:
            if attempts > 0:
                logging.warning("Retrying request")
                return await get_html(url, parameter, semaphore, attempts - 1)

        else:
            return html        

        
    else:
        logging.error("Invalid parameter for html scraping")
        return None