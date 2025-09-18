import logging
logger = logging.getLogger("supabase_utils")

# simple in-memory store for mappings & transcripts for demo
CHAT_MAPPING = {}
TRANSCRIPTS = {}

def upsert_chat_mapping(bitrix_dialog_id: str, chatling_conversation_id: str = None, chatling_contact_id: str = None):
    existing = CHAT_MAPPING.get(bitrix_dialog_id, {})
    if chatling_conversation_id:
        existing['chatling_conversation_id'] = chatling_conversation_id
    if chatling_contact_id:
        existing['chatling_contact_id'] = chatling_contact_id
    CHAT_MAPPING[bitrix_dialog_id] = existing
    logger.info(f"Upserted chat_mapping for {bitrix_dialog_id}: {existing}")

def get_chat_mapping(bitrix_dialog_id: str):
    return CHAT_MAPPING.get(bitrix_dialog_id)

def store_transcript(call_id: str, transcript: str, recording_url: str = None):
    TRANSCRIPTS[call_id] = {"transcript": transcript, "recording_url": recording_url}
    logger.info(f"Stored transcript for {call_id}")
