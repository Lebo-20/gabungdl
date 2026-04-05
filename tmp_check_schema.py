import asyncio
import aiohttp
import json

async def check_schema():
    api_code = "A8D6AB170F7B89F2182561D3B32F390D"
    id_to_test = "160000641595"
    url = f"https://idrama.dramabos.my.id/drama/{id_to_test}?lang=id&code={api_code}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            print("Response Keys:", data.keys())
            if "success" in data:
                print("Success field found:", data["success"])
            if "data" in data:
                print("Data field found, keys inside:", data["data"].keys() if isinstance(data["data"], dict) else "Not a dict")
            else:
                print("No 'data' field at top level.")

if __name__ == "__main__":
    asyncio.run(check_schema())
