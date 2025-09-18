import httpx
import os
import logging

logger = logging.getLogger("chatling")
CHATLING_BOT_ID = os.getenv("CHATLING_BOT_ID")
CHATLING_API_KEY = os.getenv("CHATLING_API_KEY")
CHATLING_API_URL = f"https://api.chatling.ai/v2/chatbots/{CHATLING_BOT_ID}/ai/kb/chat"

from supabase_utils import upsert_chat_mapping, get_chat_mapping

BOT_PROMPT = """You are a Finideas sales agent. Keep replies short, friendly, and guide the user toward KYC/registration.
End with an open question that encourages next steps.
"""

async def get_chatling_response(user_message: str, user_id: str = None, bitrix_dialog_id: str = None):
    conversation_id = None
    contact_id = None

    # If there is an existing mapping, fetch conversation_id
    mapping = None
    if bitrix_dialog_id:
        mapping = get_chat_mapping(bitrix_dialog_id)
        if mapping:
            conversation_id = mapping.get('chatling_conversation_id')
            contact_id = mapping.get('chatling_contact_id')

    # For first message, prepend BOT_PROMPT
    full_message = (BOT_PROMPT + "\n" + user_message) if not conversation_id else user_message

    payload = {
        "message": full_message,
        "conversation_id": conversation_id,
        "contact_id": contact_id,
        "user_id": user_id,
        "ai_model_id": 8
    }
    # remove None
    payload = {k: v for k, v in payload.items() if v is not None}

    headers = {
        "Authorization": f"Bearer {CHATLING_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(CHATLING_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            reply = data.get('data', {}).get('response', 'Sorry, I could not process that right now.')

            # If Chatling returned a new conversation id, upsert mapping
            new_conv = data.get('data', {}).get('conversation_id')
            if new_conv and bitrix_dialog_id:
                upsert_chat_mapping(bitrix_dialog_id, new_conv, contact_id)

            return reply
        except Exception as e:
            logger.exception("Chatling call failed")
            return "Sorry, I'm having trouble answering right now. Can I call you back later?"