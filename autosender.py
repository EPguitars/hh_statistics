import asyncio
import time
import logging

from rich import print
from rich.logging import RichHandler
from bson import ObjectId
from playwright.async_api import async_playwright

from db_operations import MongoConnector
from headers import hh_browser_headers as headers
from cover_letter import cover_letter

logging.basicConfig(
    level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)

async def check_blacklist(item, blacklisted_companies, stop_words):
    if item.get("company_name") is None:
        return True
    
    for company in blacklisted_companies:
        if company.lower() in item["company_name"].lower():
            print(f"Company {item['company_name']} is blacklisted")
            return True

    for word in stop_words:
        if word.lower() in item["title"].lower():
            print(f"Vacancy {item['title']} is blacklisted")
            return True


async def start_autosending(items: list, db_manager: MongoConnector, username: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="logined_state.json")
        page = await context.new_page()

        userdata = await db_manager.grab_userdata(username)
        
        if userdata:
            print("Userdata found")
            stop_words = userdata["stop_words"]
            blacklisted_companies = userdata["blacklisted_companies"]

        else:
            raise Exception("Userdata not found")    


        for item in items:
            # filter by company and stopwords in vacancy name
            skipping = await check_blacklist(item, blacklisted_companies, stop_words)

            if skipping:
                await db_manager.set_responded(item["_id"], True)
                continue
            
            item_id = ObjectId(item["_id"])
            await page.goto(item["url"], wait_until="commit")
            # here is manual seting
            # for continue execution press y
            # for skip vacancy press n
            pressed = input("Send letter or set as a responsed already? y/n: ")
            
            if pressed == "y":
                time.sleep(2)
                respond = await page.query_selector("a[data-qa='vacancy-response-link-top']")
                await respond.click()
                time.sleep(1)
                
                try:
                    still_respond = page.locator("span").get_by_text("Все равно откликнуться")
                    await still_respond.click()
                
                except TypeError:
                    pass
                
                time.sleep(2)
                send_letter = None
                
                try:
                    send_letter = page.locator("span").get_by_text("Написать сопроводительное")
                    await send_letter.click()
                    textarea = await page.query_selector("textarea[name='text']")
                    time.sleep(0.5)
                    await textarea.fill(cover_letter)
                    confirm = page.locator("span").get_by_text("Отправить")
                    await confirm.click()
                    await db_manager.set_responded(item_id, True)
                    time.sleep(1)
                
                except Exception:
                
                    textarea = await page.query_selector("textarea[data-qa='vacancy-response-popup-form-letter-input']")
                    await textarea.fill(cover_letter)
                    confirm = await page.query_selector("button[form='RESPONSE_MODAL_FORM_ID']")
                    await confirm.click()
                    await db_manager.set_responded(item_id, True)
                    time.sleep(1)


            elif pressed == "n":
                reason = input("""Select a reason:
                            1. Company
                            2. Vacancy name
                               """)
                
                if reason == "1":
                    new_company_filter = input("Enter a word which will be used to filter companies: \n")
                    await db_manager.set_responded(item_id, True)
                    await db_manager.update_company_filter(username, new_company_filter)
                    userdata = await db_manager.grab_userdata(username)
                    blacklisted_companies = userdata["blacklisted_companies"]

                elif reason == "2":
                    new_vacancy_filter = input("Enter a word which will be used to filter vacancies: \n")
                    await db_manager.set_responded(item_id, True)
                    await db_manager.update_vacancy_filter(username, new_vacancy_filter)
                    userdata = await db_manager.grab_userdata(username)
                    stop_words = userdata["stop_words"]

                else:
                    await db_manager.set_responded(item_id, True)
                    continue

            else:
                print("Wrong input")
                continue

        await browser.close()


async def grab_items(search_string, db_manager):

    cursor = await db_manager.grab_for_autosending(search_string)
    data = [item async for item in cursor]
    
    return data



async def main():
    db_manager = MongoConnector()
    db_manager.ping()
    items = await grab_items("python", db_manager)
    print(len(items))
    # items = [{"url": "https://hh.ru/vacancy/90329992"}]
    username = "eugene"
    await start_autosending(items, db_manager, username)

if __name__ == "__main__":
    asyncio.run(main())
    
# алгоритм работы авторассылки
# Дёргаем из базы все записи с is_actual = True, is_archived = False, responded = False
# Открываем один браузер и в нём по очереди переходим по ссылкам на вакансии и оставляем отклики
# нужно делать большие паузы между откликами, чтобы не забанили
# после отклика в базе меняем responded на True
# если вакансия в архиве, то меняем is_archived на True
# если произошла ошибка, то добавляем новое поле error = True
# обязательно счётчик откликов, чтобы остановиться на 200 в день