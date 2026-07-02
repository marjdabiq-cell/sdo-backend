"""
جدولة المهام التلقائية — تذكير يومي
"""
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

TIMEZONE = os.getenv("TIMEZONE", "Asia/Damascus")
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "8"))
REMINDER_MINUTE = int(os.getenv("REMINDER_MINUTE", "0"))

_scheduler = BackgroundScheduler(timezone=pytz.timezone(TIMEZONE))


def start_scheduler():
    from push_service import send_daily_reminder

    _scheduler.add_job(
        send_daily_reminder,
        trigger=CronTrigger(hour=REMINDER_HOUR, minute=REMINDER_MINUTE, timezone=pytz.timezone(TIMEZONE)),
        id="daily_reminder",
        replace_existing=True,
    )
    _scheduler.start()
    print(f"[scheduler] التذكير اليومي مجدول في {REMINDER_HOUR:02d}:{REMINDER_MINUTE:02d} ({TIMEZONE})")
