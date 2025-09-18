from fastapi import APIRouter, WebSocket, Body
from pydantic import BaseModel
import json
import logging
import os
from typing import Dict
from transcription import transcribe_with_lemonfox
import aiofiles


router = APIRouter()
logger = logging.getLogger("frejun")

# --- configuration ---
TELER_API_KEY = os.getenv("TELER_API_KEY")
BACKEND_DOMAIN = os.getenv("BACKEND_DOMAIN")
FROM_NUMBER = os.getenv("FROM_NUMBER")

# We will keep a simple in-memory call store for demonstration (replace with DB)
CALLS: Dict[str, Dict] = {}

class CallFlowRequest(BaseModel):
    call_id: str
    account_id: str
    from_number: str
    to_number: str

# Minimal stub connector logic. In production reuse your StreamConnector implementation.
class DummyConnector:
    async def bridge_stream(self, websocket: WebSocket):
        await websocket.send_text(json.dumps({"type": "info", "message": "connected"}))
        while True:
            data = await websocket.receive_text()
            logger.info(f"Media stream recv: {data}")
            # In production parse audio and transcript events here
            # For demo, if receives a transcript type message -> forward to Chatling
            try:
                obj = json.loads(data)
            except Exception:
                obj = {}

            if obj.get("type") == "transcript":
                user_text = obj.get("text", "")
                # send to Chatling
                from chatling import get_chatling_response
                reply = await get_chatling_response(user_text, user_id="frejun_call", bitrix_dialog_id=None)
                # send back to frejun (TTS instruction)
                tts_payload = json.dumps({"type": "tts_reply", "text": reply})
                await websocket.send_text(tts_payload)

connector = DummyConnector()

@router.post('/flow')
async def stream_flow(payload: CallFlowRequest):
    # Build a Teler/Frejun flow definition. Keep minimal for demo.
    stream_flow = {
        "ws_url": f"wss://{BACKEND_DOMAIN}/media-stream",
        "chunk_size": 500,
        "record": True,
    }
    return stream_flow

@router.post('/webhook')
async def webhook_receiver(data: Dict = Body(...)):
    logger.info(f"Frejun webhook received: {data}")
    event = data.get('event')
    call_id = data.get('call_id')
    if event == 'call.completed' and call_id:
        info = CALLS.get(call_id, {})
        lead_id = info.get('lead_id')
        recording_url = info.get('recording_url')
        transcript = ""
        if recording_url:
            async with httpx.AsyncClient() as client:
                r = await client.get(recording_url)
                file_path = f"/tmp/{call_id}.wav"
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(r.content)
                transcript = await transcribe_with_lemonfox(file_path)

        from bitrix import update_lead_with_transcript
        if lead_id:
            await update_lead_with_transcript(lead_id, transcript, recording_url)
    return {"status": "ok"}

@router.get('/initiate-call')
async def initiate_call(lead_id: str, to_number: str):
    import uuid
    call_id = str(uuid.uuid4())
    CALLS[call_id] = {"lead_id": lead_id, "to_number": to_number, "transcript": "", "recording_url": None}
    logger.info(f"Initiating call {call_id} to {to_number} for lead {lead_id}")
    # Here you’d use Frejun/Teler API to actually place the call
    return {"success": True, "call_id": call_id, "to_number": to_number}

@router.websocket('/media-stream')
async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected to /media-stream")
    try:
        await connector.bridge_stream(websocket)
    except Exception as e:
        logger.exception("Error in media stream")
    finally:
        logger.info("WebSocket disconnected")