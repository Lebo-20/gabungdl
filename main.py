import asyncio
import os
import json
import logging
from telethon import events
from api_handler import APIHandler
from downloader import Downloader
from processor import Processor
from uploader import Uploader
from database_checker import Database

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)

class AutoBot:
    def __init__(self, config_file="config.json"):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        self.admins = self.config.get("admins", [])
        self.db = Database()
        self.api = APIHandler(self.config)
        self.downloader = Downloader(self.config)
        self.processor = Processor(self.config)
        self.uploader = Uploader(self.config)
        self.check_interval = self.config.get("check_interval", 300)
        self.is_active = True
        self.semaphore = asyncio.Semaphore(1) # Limit to 1 merge at a time for safety

    async def is_admin(self, event):
        sender_id = (await event.get_sender()).id
        return sender_id in self.admins

    async def handle_search(self, event):
        if not await self.is_admin(event): return
        
        query = event.pattern_match.group(1).strip()
        if not query:
            await event.reply("Silakan ketik `/cari <judul>`")
            return
            
        logging.info(f"Admin {event.sender_id} searching for: {query}")
        results = await self.api.search_all(query)
        
        if not results:
            await event.reply(f"Tidak ditemukan hasil untuk: `{query}`")
            return

        # Store results for pagination in memory (stateful for simplicity)
        # For a production bot, you'd store this in a cache or db.
        self.last_results = results 
        await self.show_page(event, 0)

    async def show_page(self, event, page_index):
        results = self.last_results
        items_per_page = 5
        start = page_index * items_per_page
        end = start + items_per_page
        current_items = results[start:end]
        
        text = f"**Hasil Pencarian (Halaman {page_index + 1}):**\n\n"
        buttons = []
        
        for item in current_items:
            # Button for each result to "Download"
            # format: dl_<source>_<id>
            btn_data = f"dl_{item['source']}_{item['id']}"
            text += f"🎬 **{item['title']}** (`{item['source']}`)\n"
            buttons.append([events.Button.inline(f"⬇️ {item['title'][:20]}...", btn_data)])

        # Pagination buttons
        nav_buttons = []
        if page_index > 0:
            nav_buttons.append(events.Button.inline("⬅️ Prev", f"page_{page_index - 1}"))
        if end < len(results):
            nav_buttons.append(events.Button.inline("Next ➡️", f"page_{page_index + 1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)

        if isinstance(event, events.CallbackQuery.Event):
            await event.edit(text, buttons=buttons)
        else:
            await event.reply(text, buttons=buttons)

    async def handle_callback(self, event):
        if not await self.is_admin(event): return
        
        data = event.data.decode()
        if data.startswith("page_"):
            page = int(data.split("_")[1])
            await self.show_page(event, page)
        elif data.startswith("dl_"):
            parts = data.split("_")
            source = parts[1]
            item_id = parts[2]
            await event.answer("⬇️ Mengunduh sedang diproses...", alert=True)
            # Find title from last_results
            title = next((i['title'] for i in self.last_results if i['id'] == item_id), "Unknown")
            # Trigger process for this item manually
            asyncio.create_task(self.process_item({"id": item_id, "title": title, "source": source, "category": "search"}))

    async def handle_start(self, event):
        if not await self.is_admin(event): 
            await event.reply("❌ Anda tidak memiliki akses ke bot ini.")
            return
        await event.reply(
            "👋 **Selamat datang di Bot Auto Downloader!**\n\n"
            "Bot ini otomatis memantau drama baru dan menggabungkannya.\n\n"
            "**Perintah Admin:**\n"
            "🔍 `/cari <judul>` - Cari drama secara manual\n"
            "🔄 `/update` - Perbarui bot dari Git\n\n"
            "Status: **Monitoring Aktif** 🟢"
        )

    async def notify_admin(self, text):
        try:
            await self.uploader.client.send_message(self.admins[0], text)
        except Exception as e:
            logging.error(f"Failed to notify admin: {e}")

    def get_progress_bar(self, current, total):
        percentage = current * 100 / total
        finished = int(percentage // 10)
        bar = "█" * finished + "░" * (10 - finished)
        return f"[{bar}] {percentage:.1f}%"

    async def progress_callback(self, current, total, status_msg, task_name, start_time):
        # Throttle updates to avoid FloodWait (every 5 seconds or 10%)
        now = asyncio.get_event_loop().time()
        if not hasattr(self, '_last_update'): self._last_update = 0
        if now - self._last_update < 3: return
        self._last_update = now
        
        elapsed = now - start_time
        bar = self.get_progress_bar(current, total)
        try:
            await status_msg.edit(f"📤 **{task_name}:**\n{bar}\n⏱️ Elapsed: {int(elapsed)}s")
        except: pass

    async def process_item(self, item):
        async with self.semaphore:
            item_id = item.get("id")
            title = item.get("title")
            category = item.get("category")
            source = item.get("source")

            if category != "search":
                if await self.db.is_processed(item_id) or await self.db.is_title_processed(title):
                    return

            logging.info(f"Processing Drama: {title} ({source})")
            
            # Initial Notification in Private DM
            status_msg = await self.uploader.client.send_message(self.admins[0], f"⏳ **Mulai Memproses:** `{title}`")

            video_paths = []
            sub_paths = []
            merged_raw = ""
            final_video_path = ""
            
            try:
                episodes = []
                if source == "microdrama":
                    episodes = await self.api.get_microdrama_all_episodes(item_id)
                elif source == "dramabox":
                    episodes = await self.api.get_dramabox_all_episodes(item_id)

                if not episodes:
                    await status_msg.edit(f"❌ **Error:** Tidak ada episode ditemukan untuk `{title}`")
                    return

                total = len(episodes)
                await status_msg.edit(f"📥 **Downloading:** `{title}`\nProgres: 0/{total} episode")

                for i, ep in enumerate(episodes):
                    ep_vid_url = ep.get("video_url")
                    ep_sub_url = ep.get("subtitle_url")
                    if not ep_vid_url: continue
                    v_path = await self.downloader.download_m3u8(ep_vid_url, f"ep_{i}_{item_id}.mp4")
                    if v_path:
                        video_paths.append(v_path)
                        s_path = ""
                        if ep_sub_url:
                            s_path = await self.downloader.download(ep_sub_url, f"ep_{i}_{item_id}.srt")
                            s_path = await self.processor.convert_to_srt(s_path)
                        sub_paths.append(s_path if s_path else None)
                    
                    if (i + 1) % 5 == 0 or (i + 1) == total:
                        bar = self.get_progress_bar(i+1, total)
                        await status_msg.edit(f"📥 **Downloading {title}:**\n{bar}\n(Pesan ini akan dihapus setelah selesai)")

                await status_msg.edit(f"🔀 **Merging & Processing:** `{title}`... (Mohon tunggu)")
                start_merge = asyncio.get_event_loop().time()
                
                output_fn = f"full_{item_id}.mp4"
                merged_raw = await self.processor.merge_multiple_videos(video_paths, f"merged_raw_{item_id}.mp4")
                
                status_sub = "no subtitle"
                if any(sub_paths):
                    status_sub = "hardsub"
                    sub_to_burn = next((s for s in sub_paths if s), None)
                    final_video_path = await self.processor.burn_subtitle(merged_raw, sub_to_burn, output_fn)
                else:
                    final_video_path = await self.processor.merge_multiple_videos(video_paths, output_fn)

                if final_video_path and os.path.exists(final_video_path):
                    start_upload = asyncio.get_event_loop().time()
                    
                    async def u_cb(current, total):
                        await self.progress_callback(current, total, status_msg, f"Uploading {title}", start_upload)
                    
                    caption = (
                        f"🎬 **{title} (Full Episode)**\n\n"
                        f"🆔 ID: `{item_id}`\n"
                        f"📂 Kategori: {category}\n"
                        f"💬 Status Subtitle: {status_sub}\n"
                        f"📁 Source: {source.capitalize()}"
                    )
                    success = await self.uploader.upload_video(final_video_path, caption, progress_callback=u_cb)
                    if success:
                        await self.db.mark_processed(item_id, title)
                        await status_msg.delete() # Hapus Bar Persen setelah selesai
                    else:
                        await status_msg.edit(f"❌ **Upload Gagal:** `{title}`")
            except Exception as e:
                logging.error(f"Error processing {title}: {e}")
                await self.notify_admin(f"❌ **Processing Error:** `{title}`\n`{str(e)}`")
            finally:
                await self.processor.cleanup(video_paths, sub_paths, merged_raw, final_video_path)

    async def background_loop(self):
        while self.is_active:
            try:
                items = await self.api.get_new_items()
                logging.info(f"Auto-checking {len(items)} items...")
                for item in items:
                    await self.process_item(item)
            except Exception as e:
                logging.error(f"Error in background loop: {e}")
            await asyncio.sleep(self.check_interval)

    async def run(self):
        await self.db.init()
        await self.uploader.start()
        
        # Handlers
        self.uploader.client.add_event_handler(self.handle_start, events.NewMessage(pattern=r'/start'))
        self.uploader.client.add_event_handler(self.handle_search, events.NewMessage(pattern=r'/cari (.*)'))
        self.uploader.client.add_event_handler(self.handle_update, events.NewMessage(pattern=r'/update'))
        self.uploader.client.add_event_handler(self.handle_callback, events.CallbackQuery)
        
        logging.info("Bot started with /update support.")
        
        await asyncio.gather(
            self.uploader.client.run_until_disconnected(),
            self.background_loop()
        )

    async def handle_update(self, event):
        if not await self.is_admin(event): return
        
        await event.reply("🔄 Memperbarui script dari Git...")
        repo_url = "https://github.com/Lebo-20/gabungdl.git"
        
        try:
            import subprocess
            import sys
            
            # Ensure git repo is initialized if not
            if not os.path.exists(".git"):
                subprocess.run(["git", "init"], check=True)
                subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
            
            # Fetch and reset
            subprocess.run(["git", "fetch", "--all"], check=True)
            subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
            
            await event.reply("✅ Update selesai. Merestart bot...")
            
            # Restart
            os.execl(sys.executable, sys.executable, *sys.argv)
            
        except Exception as e:
            await event.reply(f"❌ Gagal update: {str(e)}")
            logging.error(f"Update error: {e}")

if __name__ == "__main__":
    bot = AutoBot()
    asyncio.run(bot.run())
