import asyncio
import aiohttp

async def check_all_keys():
    api_code = "A8D6AB170F7B89F2182561D3B32F390D"
    id_to_test = "160000641595"
    url = f"https://idrama.dramabos.my.id/drama/{id_to_test}?lang=id&code={api_code}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            print("Keys available:", sorted(data.keys()))
            if "episodes" in data:
                print("First episode keys:", data["episodes"][0].keys() if len(data["episodes"]) > 0 else "No episodes")
            if "title" in data:
                print("Title:", data["title"])
            if "cover" in data:
                print("Cover:", data["cover"])

if __name__ == "__main__":
    asyncio.run(check_all_keys())
