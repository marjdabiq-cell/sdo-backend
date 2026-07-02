"""
مصنّف الرسائل بالذكاء الاصطناعي v2
Claude Haiku (أولوية) + GPT-4o-mini (احتياطي)
"""
import os
import json
import logging
import anthropic
import httpx

logger = logging.getLogger("wtb.classifier")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """أنت مساعد ذكاء اصطناعي يعمل لصالح مساعد المدير التنفيذي في منظمة التنمية السورية (SDO).
مهمتك: تحليل الرسائل الواردة عبر واتساب وتصنيفها كـ "مهمة" أو "اجتماع".

قواعد التصنيف:
- اجتماع: يذكر موعداً/وقتاً + أشخاصاً أو مكاناً
- مهمة: طلب إنجاز عمل، متابعة، تقرير، مراسلة، أي شيء آخر

رد دائماً بـ JSON صحيح فقط — بدون أي نص إضافي.

إذا كانت مهمة:
{
  "type": "task",
  "title": "عنوان مختصر للمهمة (بالعربية)",
  "category": "إدارية|مالية|تقنية|تواصل|متابعة|أخرى",
  "priority": "عالية|متوسطة|منخفضة",
  "due_date": "YYYY-MM-DD أو null"
}

إذا كان اجتماعاً:
{
  "type": "meeting",
  "title": "موضوع الاجتماع (بالعربية)",
  "attendees": "أسماء الحضور أو null",
  "location": "مكان الاجتماع أو null",
  "meeting_date": "YYYY-MM-DD أو null",
  "meeting_time": "HH:MM أو null",
  "duration_minutes": 60,
  "notes": "ملاحظات إضافية أو null"
}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text.strip())


def _fallback_task(raw: str) -> dict:
    return {"type": "task", "title": raw[:80], "category": "أخرى", "priority": "متوسطة", "due_date": None}


def _classify_with_claude(text: str) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return _parse_json(response.content[0].text)


def _classify_with_gpt(text: str) -> dict:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY غير محدد")
    with httpx.Client(timeout=20) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "max_tokens": 512, "temperature": 0,
                  "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]},
        )
        resp.raise_for_status()
        return _parse_json(resp.json()["choices"][0]["message"]["content"])


def classify_message(raw_text: str) -> dict:
    if ANTHROPIC_API_KEY:
        try:
            result = _classify_with_claude(raw_text)
            logger.info(f"Claude <- {result.get('type')} | {result.get('title','')[:40]}")
            return result
        except Exception as e:
            logger.warning(f"Claude فشل ({e}) — جرب GPT")

    if OPENAI_API_KEY:
        try:
            result = _classify_with_gpt(raw_text)
            logger.info(f"GPT <- {result.get('type')} | {result.get('title','')[:40]}")
            return result
        except Exception as e:
            logger.warning(f"GPT فشل ({e}) — Fallback")

    logger.error("كلا النموذجين فشلا — Fallback")
    return _fallback_task(raw_text)
