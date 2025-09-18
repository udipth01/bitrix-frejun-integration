from fastapi import APIRouter, Request, HTTPException
import httpx
import os
import logging
import json
from frejun import initiate_call

router = APIRouter()
logger = logging.getLogger("bitrix")

BACKEND_DOMAIN = os.getenv("BACKEND_DOMAIN")
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")  # e.g. https://yourdomain/rest
BITRIX_USER = os.getenv("BITRIX_USER")
BITRIX_TOKEN = os.getenv("BITRIX_TOKEN")

# endpoint for Bitrix to POST lead events (make sure Bitrix sends JSON)
@router.post('/bitrix-handler-lead')
async def bitrix_lead_handler(request: Request):
    payload = await request.json()
    lead_fields = payload.get('FIELDS', {})
    lead_id = lead_fields.get('ID')

    if not lead_id:
        raise HTTPException(status_code=400, detail="Missing lead ID")

    lead_name = (lead_fields.get('NAME') or "").lower()

    if "udipth" in lead_name:
        # Fetch lead details from Bitrix to get phone number
        phone_number = await get_lead_phone(lead_id)


        await initiate_call(lead_id=lead_id, to_number=phone_number)


    return {"status": "ok"}

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
