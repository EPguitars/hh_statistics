import pandas as pd

import asyncio

from db_operations import MongoConnector


async def main():
    db_manager = MongoConnector()
    db_manager.ping()

    selected_columns = ["title", "salary_min", "salary_max", "experience", "company_name", "when_scraped", "employment_type", "key_skills"]
    cursor = db_manager.collection.find({}, {column: 1 for column in selected_columns})
    data = [item async for item in cursor]

    # Convert data to a pandas DataFrame
    df = pd.DataFrame(data)
    df = df.drop('_id', axis=1)
    df.reset_index(drop=True, inplace=True)
    # Save DataFrame to CSV
    df.to_csv('output.csv', index=False)


    await db_manager.close_connection()

if __name__ == "__main__":
    asyncio.run(main()) 