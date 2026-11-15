import asyncio
from pathlib import Path

from bazaar.config import Settings
from bazaar.storage import Store


async def main():
    store = Store(Settings())
    async with store.connection() as connection:
        await connection.execute(Path(__file__).with_name("schema.sql").read_text())
    print("Database schema applied")


if __name__ == "__main__":
    asyncio.run(main())
