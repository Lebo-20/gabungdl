from telethon import TelegramClient, events, types
import logging
import os
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

    async def upload_video(self, video_path: str, caption: str, progress_callback=None) -> bool:
        if not os.path.exists(video_path):
            logging.error(f"Upload failed: File {video_path} does not exist.")
            if progress_callback: await progress_callback(0, 100) # Reset
            return False

        try:
            entity = self.channel_id
            logging.info(f"Uploading {video_path} to {entity}...")
            
            msg = await self.client.send_file(
                entity,
                video_path,
                caption=caption,
                supports_streaming=True,
                progress_callback=progress_callback,
                attributes=[types.DocumentAttributeVideo(
                    duration=0,
                    w=1280,
                    h=720,
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
