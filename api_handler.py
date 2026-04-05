import aiohttp
import logging
import asyncio
from typing import List, Dict, Any

class APIHandler:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_code = config.get("api_code", "A8D6AB170F7B89F2182561D3B32F390D")
        self.apis = config.get("apis", {})

    async def fetch_json(self, url: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    logging.error(f"Error fetching API: {url} status: {response.status}")
            except Exception as e:
                logging.error(f"Exception fetching {url}: {e}")
        return {}

    async def get_list(self, source, category="popular", page=1, limit=20) -> List[Dict[str, Any]]:
        if source not in self.apis: return []
        
        # microdrama pattern: base + list?lang=id...
        url = f"{self.apis[source]}list?lang=id&page={page}&limit={limit}&code={self.api_code}"
        data = await self.fetch_json(url)
        items = []
        if data.get("success") and "data" in data:
            inner_data = data["data"].get("data", [])
            for d in inner_data:
                items.append({
                    "id": str(d.get("id")),
                    "title": d.get("title"),
                    "category": category,
                    "source": source
                })
        return items

    async def get_microdrama_play(self, drama_id, ep_no) -> Dict[str, Any]:
        url = f"{self.apis['microdrama']}play/{drama_id}/{ep_no}?lang=id&code={self.api_code}"
        data = await self.fetch_json(url)
        if data.get("success") and "data" in data:
            return data["data"]
        return {}

    async def get_all_episodes(self, source, drama_id) -> Dict[str, Any]:
        if source == "dramabox":
            return await self.get_dramabox_all_episodes(drama_id)
            
        if source not in self.apis: return {"episodes": [], "metadata": {}}
        
        url = f"{self.apis[source]}drama/{drama_id}?lang=id&code={self.api_code}"
        data = await self.fetch_json(url)
        episodes = []
        metadata = {}
        if data.get("success") and "data" in data:
            drama_data = data["data"]
            metadata = {
                "cover": drama_data.get("cover"),
                "description": drama_data.get("description") or drama_data.get("synopsis") or "No description available.",
                "title": drama_data.get("title")
            }
            if "episodes" in drama_data:
                for ep in drama_data["episodes"]:
                    v_url = ""
                    if "videos" in ep:
                        for v in ep["videos"]:
                            if v.get("quality") == "720P":
                                v_url = v.get("url")
                                break
                        if not v_url and ep["videos"]:
                            v_url = ep["videos"][0].get("url")
                    
                    episodes.append({
                        "id": f"{drama_id}_{ep.get('episode')}",
                        "video_url": v_url,
                        "subtitle_url": ep.get("subtitle_url"),
                        "episode_no": int(ep.get('episode', 0))
                    })
            episodes.sort(key=lambda x: x.get('episode_no', 0))
        return {"episodes": episodes, "metadata": metadata}

    async def get_dramabox_all_episodes(self, book_id) -> Dict[str, Any]:
        # Get metadata first
        meta_url = f"{self.apis['dramabox']}detail?bookId={book_id}&lang=in&code={self.api_code}"
        meta_data = await self.fetch_json(meta_url)
        metadata = {}
        if meta_data.get("code") == 200 and "data" in meta_data:
            d = meta_data["data"]
            metadata = {
                "cover": d.get("cover"),
                "description": d.get("description") or d.get("bookDescription") or "No description available.",
                "title": d.get("bookName")
            }

        url = f"{self.apis['dramabox']}allepisode?bookId={book_id}&lang=in&code={self.api_code}"
        data = await self.fetch_json(url)
        episodes = data.get("data", []) if data.get("code") == 200 else []
        return {"episodes": episodes, "metadata": metadata}

    async def get_dramabox_homepage(self, page=1) -> List[Dict[str, Any]]:
        url = f"{self.apis['dramabox']}homepage?page={page}&lang=in"
        data = await self.fetch_json(url)
        items = []
        if data.get("code") == 200 and "data" in data:
            for item in data["data"]:
                items.append({
                    "id": str(item.get("bookId")),
                    "title": item.get("bookName"),
                    "category": "home",
                    "source": "dramabox"
                })
        return items

    async def get_dramabox_play(self, book_id) -> Dict[str, Any]:
        url = f"{self.apis['dramabox']}detail?bookId={book_id}&lang=in&code={self.api_code}"
        data = await self.fetch_json(url)
        return data.get("data", {})

    async def search_source(self, source, query: str) -> List[Dict[str, Any]]:
        if source == "dramabox": return await self.search_dramabox(query)
        if source not in self.apis: return []
        
        url = f"{self.apis[source]}search?q={query}&lang=id&code={self.api_code}"
        data = await self.fetch_json(url)
        items = []
        if data.get("success") and "data" in data:
            results = data["data"]
            for d in results:
                items.append({
                    "id": str(d.get("id")),
                    "title": d.get("title"),
                    "source": source,
                    "cover": d.get("cover")
                })
        return items

    async def search_dramabox(self, query: str) -> List[Dict[str, Any]]:
        url = f"{self.apis['dramabox']}search?query={query}&lang=in"
        data = await self.fetch_json(url)
        items = []
        if data.get("code") == 200 and "data" in data:
            results = data["data"]
            for d in results:
                items.append({
                    "id": str(d.get("bookId")),
                    "title": d.get("bookName"),
                    "source": "dramabox",
                    "cover": d.get("cover")
                })
        return items

    async def search_all(self, query: str) -> List[Dict[str, Any]]:
        results = []
        tasks = []
        for source in self.apis:
            tasks.append(self.search_source(source, query))
            
        all_results = await asyncio.gather(*tasks)
        for r in all_results:
            results.extend(r)
        return results

    # Helper function to consolidate data for downloading
    async def get_new_items(self) -> List[Dict[str, Any]]:
        """Fetches items from all sources and interleaves them to alternate processing."""
        tasks = []
        for source in self.apis:
            if source == "dramabox":
                tasks.append(self.get_dramabox_homepage())
            else:
                tasks.append(self.get_list(source, category="popular"))
        
        all_lists = await asyncio.gather(*tasks)
        
        interleaved = []
        max_len = max(len(l) for l in all_lists) if all_lists else 0
        
        for i in range(max_len):
            for l in all_lists:
                if i < len(l):
                    interleaved.append(l[i])
                    
        return interleaved
