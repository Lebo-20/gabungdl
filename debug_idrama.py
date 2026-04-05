import asyncio
import aiohttp
import json

async def check_idrama_details():
    api_code = "A8D6AB170F7B89F2182561D3B32F390D"
    id_to_test = "160000641595"
    url = f"https://idrama.dramabos.my.id/drama/{id_to_test}?lang=id&code={api_code}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            print("Status Code:", resp.status)
            print("All Keys:", sorted(data.keys()))
            print("Title:", data.get("title") or data.get("bookName") or data.get("drama_name"))
            print("Episodes Count:", len(data.get("episodes", [])) if "episodes" in data else "No episodes field")
            if "episodes" in data and len(data["episodes"]) > 0:
                 print("Sample Episode Keys:", data["episodes"][0].keys())

if __name__ == "__main__":
    asyncio.run(check_idrama_details())
