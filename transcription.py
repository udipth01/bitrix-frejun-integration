import os
import httpx
import logging

logger = logging.getLogger("transcription")

LEMONFOX_API_KEY = os.getenv("LEMONFOX_API_KEY")
LEMONFOX_URL = "https://api.lemonfox.ai/v1/transcribe"

async def transcribe_with_lemonfox(file_path: str) -> str:
    headers = {"Authorization": f"Bearer {LEMONFOX_API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": f}
                resp = await client.post(LEMONFOX_URL, headers=headers, files=files)
                resp.raise_for_status()
                data = resp.json()
                return data.get("text", "")
    except Exception as e:
        logger.exception("Lemonfox transcription failed")
        return ""
