"""
التطبيق الرئيسي v2 — مهام + اجتماعات + تقرير يومي + Flutter API
الملف النهائي: backend/main.py
"""
import os
import logging
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from database import (
    init_db, insert_task, insert_meeting,
    list_tasks, list_meetings, update_task_status, update_meeting_status,
    save_push_subscription, get_daily_report, get_today_meetings
)
from ai_classifier import classify_message
from whatsapp_client import send_text_message
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wtb")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
ALLOWED_NUMBER = os.getenv("ALLOWED_SENDER_NUMBER")

app = FastAPI(title="جسر واتساب - المهام v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()
    logger.info("النظام جاهز v2.")


@app.get("/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403)


@app.post("/webhook")
async def receive_message(request: Request):
    payload = await request.json()
    try:
        messages = payload["entry"][0]["changes"][0]["value"].get("messages")
        if not messages:
            return {"status": "ignored"}

        msg = messages[0]
        sender = msg["from"]
        if ALLOWED_NUMBER and sender != ALLOWED_NUMBER:
            return {"status": "rejected"}
        if msg.get("type") != "text":
            await send_text_message(sender, "حالياً أدعم الرسائل النصية فقط.")
            return {"status": "unsupported"}

        raw = msg["text"]["body"]
        result = classify_message(raw)

        if result["type"] == "meeting":
            mid = insert_meeting(
                raw_text=raw,
                title=result["title"],
                attendees=result.get("attendees"),
                location=result.get("location"),
                meeting_date=result.get("meeting_date"),
                meeting_time=result.get("meeting_time"),
                duration_minutes=result.get("duration_minutes", 60),
                notes=result.get("notes"),
            )
            reply = (
                f"📅 تم تسجيل الاجتماع #{mid}\n"
                f"الموضوع: {result['title']}\n"
                f"التاريخ: {result.get('meeting_date','غير محدد')} {result.get('meeting_time','') or ''}\n"
                f"المكان: {result.get('location') or 'غير محدد'}"
            )
            await send_text_message(sender, reply)
            return {"status": "ok", "type": "meeting", "id": mid, "reply": reply}

        else:
            tid = insert_task(
                raw_text=raw,
                title=result["title"],
                category=result["category"],
                priority=result["priority"],
                due_date=result.get("due_date"),
            )
            reply = (
                f"✅ تم تسجيل المهمة #{tid}\n"
                f"العنوان: {result['title']}\n"
                f"التصنيف: {result['category']} | الأولوية: {result['priority']}"
            )
            if result.get("due_date"):
                reply += f"\nالاستحقاق: {result['due_date']}"
            await send_text_message(sender, reply)
            return {"status": "ok", "type": "task", "id": tid, "reply": reply}

    except (KeyError, IndexError) as e:
        logger.error(f"خطأ: {e}")
        return {"status": "error"}


@app.get("/api/tasks")
def api_tasks(status: str | None = None):
    return list_tasks(status)

@app.patch("/api/tasks/{task_id}")
def api_update_task(task_id: int, status: str):
    update_task_status(task_id, status)
    return {"status": "updated"}


@app.get("/api/meetings")
def api_meetings(status: str | None = None):
    return list_meetings(status)

@app.patch("/api/meetings/{meeting_id}")
def api_update_meeting(meeting_id: int, status: str):
    update_meeting_status(meeting_id, status)
    return {"status": "updated"}

@app.get("/api/meetings/today")
def api_today_meetings():
    return get_today_meetings()


@app.get("/api/report/daily")
def api_daily_report():
    return get_daily_report()


@app.post("/api/push/subscribe")
async def api_subscribe(request: Request):
    data = await request.json()
    save_push_subscription(
        endpoint=data.get("endpoint", ""),
        p256dh=data.get("keys", {}).get("p256dh", ""),
        auth=data.get("keys", {}).get("auth", ""),
        device_token=data.get("device_token"),
        platform=data.get("platform", "web"),
    )
    return {"status": "subscribed"}

@app.get("/api/vapid-public-key")
def api_vapid():
    return {"publicKey": os.getenv("VAPID_PUBLIC_KEY")}
