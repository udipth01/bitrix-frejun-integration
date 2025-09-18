from fastapi import APIRouter, Request, HTTPException
import httpx
import os
import logging
import json
from frejun import initiate_call

router = APIRouter()
logger = logging.getLogger("bitrix")

BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")  # e.g. https://yourdomain/rest

from urllib.parse import parse_qs

@router.post("/bitrix-handler-lead")
async def bitrix_lead_handler(request: Request):
    raw_body = await request.body()
    raw_text = raw_body.decode("utf-8")
    
    logger.info(f"🔹 Raw incoming body: {raw_text}")
    
    payload = parse_qs(raw_text)
    logger.info(f"🔹 Parsed payload: {payload}")
    
    lead_id = None
    if "data[FIELDS][ID]" in payload:
        lead_id = payload["data[FIELDS][ID]"][0]
    elif "id" in payload:
        lead_id = payload["id"][0]

    if not lead_id:
        raise HTTPException(status_code=400, detail="Lead ID missing")
    
    # Fetch lead details from Bitrix
    phone_number = await get_lead_phone(lead_id)
    
    lead_name = payload.get("data[FIELDS][TITLE]", [""])[0].lower() if payload.get("data[FIELDS][TITLE]") else ""
    
    if "udipth" in lead_name and phone_number:
        await initiate_call(lead_id=lead_id, to_number=phone_number)
        return {"status": "forwarded", "lead_id": lead_id, "phone": phone_number}
    
    return {"status": "skipped", "reason": "Lead name does not match or phone missing"}


async def get_lead_phone(lead_id: str) -> str:
    url = f"{BITRIX_WEBHOOK_URL}/crm.lead.get.json"
    params = {"id": lead_id}
    async with httpx.AsyncClient() as client:
        res = await client.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        phones = data.get("result", {}).get("PHONE", [])
        if phones:
            return phones[0].get("VALUE")  # take first phone number
    return None


async def update_lead_with_transcript(lead_id: str, transcript: str, recording_url: str = None):
    """Update a Bitrix lead custom fields with transcript & recording link."""
    if not BITRIX_WEBHOOK_URL:
        logger.error("BITRIX_WEBHOOK_URL not configured")
        return False

    url = f"{BITRIX_WEBHOOK_URL}/crm.lead.update.json"
    payload = {"id": lead_id, "fields": {"UF_CRM_TRANSCRIPT": transcript}}
    if recording_url:
        payload["fields"]["UF_CRM_RECORDING"] = recording_url

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            logger.info(f"Bitrix update response: {data}")
            return True
    except Exception as e:
        logger.exception("Failed to update Bitrix lead")
        return False
