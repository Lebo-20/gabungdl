import asyncio
import aiohttp

async def test_other_apis():
    api_code = "A8D6AB170F7B89F2182561D3B32F390D"
    apis = {
        "idrama": "https://idrama.dramabos.my.id/api/idrama/",
        "melolo": "https://melolo.dramabos.my.id/api/melolo/",
        "dramabite": "https://dramabite.dramabos.my.id/api/dramabite/",
        "flickreels": "https://flickreels.dramabos.my.id/api/flickreels/"
    }
    
    async with aiohttp.ClientSession() as session:
        for name, url_base in apis.items():
            test_url = f"{url_base}list?lang=id&page=1&limit=5&code={api_code}"
            print(f"Testing {name}: {test_url}")
            try:
                async with session.get(test_url, timeout=5) as resp:
                    print(f"  Status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"  Success: {data.get('success')}")
                        if data.get('success'):
                            items = data.get('data', {}).get('data', [])
                            print(f"  Found {len(items)} items.")
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_other_apis())
