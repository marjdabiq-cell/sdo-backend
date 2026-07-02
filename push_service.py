"""
إرسال إشعارات Push (Web Push) — التذكير اليومي
"""
import os
import json
from pywebpush import webpush, WebPushException
from database import get_all_subscriptions, count_open_tasks_by_category

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "mailto:admin@syrdev.org")


def build_daily_summary_text() -> str:
    counts = count_open_tasks_by_category()
    if not counts:
        return "لا توجد مهام مفتوحة اليوم. صباح ممتاز."
    total = sum(counts.values())
    parts = " | ".join(f"{cat}: {n}" for cat, n in counts.items())
    return f"لديك {total} مهمة مفتوحة اليوم — {parts}"


def send_daily_reminder():
    body = build_daily_summary_text()
    payload = json.dumps({"title": "ملخص مهامك اليوم", "body": body})
    for sub in get_all_subscriptions():
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
            )
        except WebPushException as e:
            print(f"فشل إرسال إشعار: {e}")
