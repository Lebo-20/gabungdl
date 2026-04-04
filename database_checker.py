import aiosqlite
import logging

class Database:
    def __init__(self, db_name="bot_data.db"):
        self.db_name = db_name

    async def init(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS processed_items (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def is_processed(self, item_id):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT 1 FROM processed_items WHERE id = ?", (item_id,)) as cursor:
                return await cursor.fetchone() is not None

    async def mark_processed(self, item_id, title):
        async with aiosqlite.connect(self.db_name) as db:
            try:
                await db.execute("INSERT INTO processed_items (id, title) VALUES (?, ?)", (item_id, title))
                await db.commit()
            except aiosqlite.IntegrityError:
                pass

    async def is_title_processed(self, title):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT 1 FROM processed_items WHERE title = ?", (title,)) as cursor:
                return await cursor.fetchone() is not None
