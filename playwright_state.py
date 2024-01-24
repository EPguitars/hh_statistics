import time

from playwright.sync_api import sync_playwright

def globalsetup(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        page.goto(url, wait_until="commit")
        time.sleep(30)
        page.context.storage_state(path="logined_state.json")
        time.sleep(5)
        browser.close()


if __name__ == "__main__":
    url = "https://www.hh.ru"
    globalsetup(url)