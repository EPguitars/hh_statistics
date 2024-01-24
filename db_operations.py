import os
import logging

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

uri = os.getenv("MONGO_CONNECTION_STRING")
# Create a new client and connect to the server


class MongoConnector:
    def __init__(self):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client.data
        self.collection = self.db.hh
        self.userdata = self.db.userdata
        
    def ping(self):
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print("Don't have a connection to MongoDB")

    async def send_to_db(self, data):
        
        json_to_send = {
            # use models.py to create a json
            "title": data.title,
            "salary_type": data.salary_type,
            "salary": data.salary,
            "url": data.url,
            "city": data.city,
            "experience": data.experience,
            "fresh": data.fresh,
            "is_actual": data.is_actual,
            "company_name": data.company_name,
            "company_page": data.company_page,
            "search_strings": data.search_strings,
            "when_scraped": data.when_scraped,
            "company_address": data.company_address,
            "description": data.description,
            "employment_type": data.employment_type,
            "source_id": data.source_id,
            "key_skills": data.key_skills,
            "is_scraped": data.is_scraped,
            "is_archived": data.is_archived,
            "responded": data.responded,
            "salary_min": data.salary_min,
            "salary_max": data.salary_max
        }

        await self.collection.insert_one(json_to_send)
        logging.info(f"Item {data.source_id} sent to db")

    async def find_item_by_id(self, id):
        result = await self.collection.find_one({"source_id": id})
        return result

    async def refresh_is_actual(self):
        await self.collection.update_many({}, {"$set": {"is_actual": False}})
        logging.info("is_actual refreshed")

    async def set_is_actual_true(self, id):
        await self.collection.update_one({"source_id": id}, {"$set": {"is_actual": True}})
        logging.info(f"Item {id} is_actual set to True")

    async def set_is_archived_true(self, id):
        await self.collection.update_one({"source_id": id}, {"$set": {"is_archived": True}})
        logging.info(f"Item {id} is_archived set to True")

    async def close_connection(self):
        self.client.close()
        print("DB Connection closed")   

    async def grab_for_autosending(self, search_string):
        result = self.collection.find({"is_actual": True, "is_archived": False, "responded": False, "search_strings": search_string})
        return result

    async def grab_userdata(self, user_id):
        result = await self.userdata.find_one({"username": user_id})
        return result
    
    async def set_responded(self, id, value):
        await self.collection.update_one({"_id": id}, {"$set": {"responded": value}})
        logging.info(f"Item {id} responded set to {value}")

    async def update_company_filter(self, username, value):
        await self.userdata.update_one({"username": username}, {"$push": {"blacklisted_companies": value}})
        logging.info(f"User {username} added {value} to blacklist")

    async def update_vacancy_filter(self, username, value):
        await self.userdata.update_one({"username": username}, {"$push": {"stop_words": value}})
        logging.info(f"User {username} added {value} to vacancy_blacklist")
    

if __name__ == "__main__":
    pass