import asyncio
import aiohttp

async def test_idrama():
    api_code = "A8D6AB170F7B89F2182561D3B32F390D"
    id_to_test = "160000641595"
    
    urls = [
        f"https://idrama.dramabos.my.id/detail?bookId={id_to_test}&lang=in&code={api_code}",
        f"https://idrama.dramabos.my.id/drama/{id_to_test}?lang=id&code={api_code}",
        f"https://idrama.dramabos.my.id/api/idrama/drama/{id_to_test}?lang=id&code={api_code}",
        f"https://idrama.dramabos.my.id/api/v1/detail?bookId={id_to_test}&lang=in&code={api_code}"
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            print(f"Testing: {url}")
            try:
                async with session.get(url, timeout=5) as resp:
                    print(f"  Status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"  Response: {str(data)[:200]}...")
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_idrama())
