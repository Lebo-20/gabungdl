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

    async def upload_video(self, video_path: str, caption: str) -> bool:
        if not os.path.exists(video_path):
            logging.error(f"Upload failed: File {video_path} does not exist.")
            return False

        try:
            # Try to resolve the channel entity first
            # If it's a link, bots might have trouble resolving private ones
            entity = self.channel_id
            if isinstance(self.channel_id, str) and "+" in self.channel_id:
                logging.warning("Channel ID is an invite link. Bots cannot resolve private links automatically.")
                logging.warning("Please use the numeric Channel ID (e.g., -100...) for better reliability.")
            
            # Upload to main channel
            logging.info(f"Uploading {video_path} to {entity}...")
            msg = await self.client.send_file(
                entity,
                video_path,
                caption=caption,
                supports_streaming=True,
                attributes=[types.DocumentAttributeVideo(
                    duration=0,
                    w=1280,
                    h=720,
                    supports_streaming=True
                )]
            )
            
            # Forward or re-upload to backup channel
            if self.backup_channel_id:
                logging.info(f"Forwarding to backup channel {self.backup_channel_id}...")
                await self.client.send_message(self.backup_channel_id, msg)
            
            logging.info("Upload completed successfully.")
            return True

        except Exception as e:
            err_msg = str(e)
            logging.error(f"Exception during upload: {err_msg}")
            if "CheckChatInviteRequest" in err_msg or "restricted" in err_msg:
                logging.error("CRITICAL: Bot cannot use invite links. Please change channel_id to a numeric ID in config.json")
            return False

    async def disconnect(self):
        await self.client.disconnect()
