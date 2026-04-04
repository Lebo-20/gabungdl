import asyncio
import os
import logging
from typing import Dict, Any

class Downloader:
    def __init__(self, config: Dict[str, Any]):
        self.download_dir = config.get("download_dir", "./downloads")
        self.max_connections = config.get("max_connections", 16)
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    async def download(self, url: str, filename: str, retries: int = 3) -> str:
        output_path = os.path.join(self.download_dir, filename)
        if os.path.exists(output_path):
            os.remove(output_path)

        binary = "aria2c.exe" if os.name == "nt" else "aria2c"
        # command: aria2c -x 16 -s 16 -o filename url
        cmd = [
            binary,
            f"-x{self.max_connections}",
            f"-s{self.max_connections}",
            "--auto-file-renaming=false",
            "--allow-overwrite=true",
            "-d", self.download_dir,
            "-o", filename,
            url
        ]

        for i in range(retries):
            logging.info(f"Downloading {filename} (Attempt {i+1}/{retries})")
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    logging.info(f"Download completed: {output_path}")
                    return output_path
                else:
                    logging.error(f"Download failed: {stderr.decode()}")
            except Exception as e:
                logging.error(f"Execution error ({binary}): {e}")
            
            await asyncio.sleep(5)
        
        return ""

    async def download_m3u8(self, url: str, filename: str) -> str:
        if url.endswith(".m3u8"):
            output_path = os.path.join(self.download_dir, filename)
            binary = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
            cmd = [
                binary, "-i", url, "-c", "copy", "-bsf:a", "aac_adtstoasc", output_path, "-y"
            ]
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                if process.returncode == 0: return output_path
            except Exception as e:
                logging.error(f"Execution error ({binary}): {e}")
            return ""
        else:
            return await self.download(url, filename)
