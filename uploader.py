from telethon import TelegramClient, events, types
import logging
import os
import aiohttp
from typing import Dict, Any

class Uploader:
    def __init__(self, config: Dict[str, Any]):
        self.api_id = config.get("api_id")
        self.api_hash = config.get("api_hash")
        self.bot_token = config.get("bot_token")
        self.channel_id = config.get("channel_id")
        self.backup_channel_id = config.get("backup_channel_id")
        self.client = TelegramClient('bot_session', self.api_id, self.api_hash)

    async def start(self):
        await self.client.start(bot_token=self.bot_token)
        logging.info("Telegram client started.")

    async def send_photo_with_caption(self, photo_url: str, caption: str):
        temp_photo = "temp_cover.jpg"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(photo_url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(temp_photo, "wb") as f:
                            f.write(content)
                        
                        await self.client.send_file(
                            self.channel_id,
                            temp_photo,
                            caption=caption,
                            force_document=False # Always send as Photo
                        )
                        if os.path.exists(temp_photo):
                            os.remove(temp_photo)
                    else:
                        # Fallback to link if download fails
                        await self.client.send_file(self.channel_id, photo_url, caption=caption, force_document=False)
        except Exception as e:
            logging.error(f"Error sending photo: {e}")
            if os.path.exists(temp_photo): os.remove(temp_photo)

    async def upload_video(self, video_path: str, title: str, meta_info: str, duration: int, width: int = 1280, height: int = 720, thumb: str = None, progress_callback=None) -> bool:
        if not os.path.exists(video_path):
            logging.error(f"Upload failed: File {video_path} does not exist.")
            if progress_callback: await progress_callback(0, 100) # Reset
            return False

        try:
            entity = self.channel_id
            logging.info(f"Uploading {video_path} to {entity}...")
            
            final_caption = f"**{title}**"
            if meta_info:
                final_caption += f"\n\n{meta_info}"
            
            msg = await self.client.send_file(
                entity,
                video_path,
                caption=final_caption,
                thumb=thumb,
                supports_streaming=True,
                progress_callback=progress_callback,
                video_note=False,
                force_document=False,
                attributes=[types.DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True
                )]
            )
            
            if self.backup_channel_id and self.backup_channel_id != self.channel_id:
                logging.info(f"Forwarding to backup channel {self.backup_channel_id}...")
                await self.client.send_message(self.backup_channel_id, msg)
            
            logging.info("Upload completed successfully.")
            return True

        except Exception as e:
            logging.error(f"Exception during upload: {e}")
            return False

    async def disconnect(self):
        await self.client.disconnect()
