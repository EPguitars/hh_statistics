import os
import logging
import asyncio

from bson import ObjectId
import httpx
from dotenv import load_dotenv
from rich import print

from db_operations import MongoConnector

load_dotenv()

CUR_CONVERTER_KEY = os.getenv("CURRENCY_API_KEY")  
CURRENCIES = {
    "RUB": "₽",
    "USD": "$",
    "EUR": "€",
    "KZT": "₸",
    "AZN": "₼"
}

async def get_currency_rates():
    async with httpx.AsyncClient() as client:
        url = "https://api.freecurrencyapi.com/v1/latest"
        
        params = {
            "apikey" : CUR_CONVERTER_KEY,
            "base_currency" : "RUB",
            "currencies" : "RUB,USD,EUR"
        }
        response = await client.get(url, params=params)
        currency_rates = response.json()["data"]
        print(currency_rates)

        return currency_rates

def split_salary(salary_type, value, currency):
    # 1. По договоренности - "no numbers"
    # 2. Вилка "fork"
    # 3. Одно число "fixed"
    # 4. от "min"
    # 5. до "max"

    if salary_type == "no numbers":
        return None, None
    
    elif salary_type == "fork":
        
        salary_min, salary_max = value.replace(CURRENCIES[currency], "").split("–")
        salary_min = int(salary_min.replace(" ", "").replace("на руки", ""))
        salary_max = int(salary_max.replace(" ", "").replace("на руки", ""))
        return salary_min, salary_max
    
    elif salary_type == "fixed":
        print(value)
        salary_min = int(value.replace(CURRENCIES[currency], "")
                         .replace(" ", "")
                         .replace("на руки", ""))
        return salary_min, salary_min
    
    elif salary_type == "min":
        salary_min = int(value.replace(CURRENCIES[currency], "")
                         .replace("на руки", "")
                         .replace(" ", "")
                         .replace("от", ""))
        return salary_min, None

    elif salary_type == "max":
        salary_max = int(value.replace(CURRENCIES[currency], "")
                            .replace("на руки", "")
                            .replace(" ", "")
                            .replace("до", ""))
        
        return None, salary_max


def detect_currency(value):
    
    if "₽" in value:
        return "RUB"
    elif "$" in value:
        return "USD"
    elif "€" in value:
        return "EUR"
    elif "₸" in value:
        return "KZT"
    elif "₼" in value:
        return "AZN"
    else:
        print(value)
        print("Can't detect currency")


def convert_currency(currency, salary_min, 
                     salary_max, rates):
    
    if currency == "KZT":
        converted_min = round(salary_min / 5.1) if salary_min is not None else None
        converted_max = round(salary_max / 5.1) if salary_max is not None else None
        return converted_min, converted_max
    
    elif currency == "AZN":
        converted_min = round(salary_min / 0.019) if salary_min is not None else None
        converted_max = round(salary_max / 0.019) if salary_max is not None else None
        return converted_min, converted_max

    converted_min = round(salary_min / rates[currency]) if salary_min is not None else None
    converted_max = round(salary_max / rates[currency]) if salary_max is not None else None

    return converted_min, converted_max


async def main():
    db = MongoConnector()
    rates = await get_currency_rates()
    result = db.collection.find({})
    counter = 4500
    
    async for item in result:
        salary = item["salary"]
        
        currency = detect_currency(salary) if salary else "RUB"
        salary_min, salary_max = split_salary(item["salary_type"], item["salary"], currency)
        
        if "salary_min" in item.keys():
            print("Already updated")
            continue

        if currency != "RUB":
            salary_min, salary_max = convert_currency(currency, salary_min, 
                                                      salary_max, rates)
        query = {"_id": ObjectId(item["_id"])}
        
        new_fields = {
            "salary_min": salary_min,
            "salary_max": salary_max
        }

        await db.collection.update_one(query, {"$set": new_fields})
        counter += 1
        print(f"Items updated: {counter}")    


    await db.close_connection()


async def update_key(old_key, new_key):
    db = MongoConnector()
    await db.collection.update_many({}, {"$rename": {old_key: new_key}})
    await db.close_connection()


async def set_currency():
    db = MongoConnector()
    result = db.collection.find({"salary_currency": {"$exists": False}})
    counter = 0

    async for item in result:
        query = {"_id": ObjectId(item["_id"])}
        salary = item["salary"]
        currency = detect_currency(salary) if salary else "RUB"
        
        await db.collection.update_one(query, {"$set": {"salary_currency": currency}})
        counter += 1
        print(f"Items updated: {counter}")  
    # async for item in result:
    #     item["key_skills"]    
    #     for skill in item["key_skills"]:
    #         skills_list.add(skill)

    

    await db.close_connection()

if __name__ == "__main__":
    asyncio.run(set_currency())
