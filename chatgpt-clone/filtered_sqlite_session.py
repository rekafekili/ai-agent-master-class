from agents import SQLiteSession


class FilterSQLiteSession(SQLiteSession):
    async def get_items(self):
        items = await super().get_items()
        filtered = []
        for item in items:
            if isinstance(item, dict) and item.get("type") == "image_generation_call":
                item = {k: v for k, v in item.items() if k != "action"}
            filtered.append(item)
        return filtered
