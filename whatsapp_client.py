import os
import httpx

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
GRAPH_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

async def send_text_message(to_number: str, body: str):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print(f"[Baileys reply] -> {to_number}: {body}")
        return
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": body}}
    async with httpx.AsyncClient() as client:
        resp = await client.post(GRAPH_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
