"""Trusted facts the assistant may state besides the service card and the case record (policy P-17).

The agent has no internet access on purpose: web pages are untrusted text (a route for prompt injection and for
sending case data out), the case study forbids real Ministry systems, and the demo must work offline. A language
model also has no clock, so it invents times and dates (found on 21 October: "The current time in the UAE is 10:45 AM",
which was wrong). So:

  * the date and time come from this computer's clock, in UAE time (UTC+4, no daylight saving), written by code;
  * questions outside the service (weather, news, prices, general knowledge) get a fixed reply, never a guess;
  * the reply checker blocks a clock time or date in any model reply (agent/output_guard.py).

Anything else the agent says comes from the service card, a rule result or a tool result.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import MOE_SUPPORT_NUMBER
from .language import to_ascii_digits

UAE = timezone(timedelta(hours=4), "UAE")          # Gulf Standard Time; the UAE has no daylight saving

CLOCK = re.compile(
    r"\bwhat(?:'?s| is) (?:the )?(?:time|date|day)\b|\bwhat (?:date|day) is (?:it|today)\b|\btime (?:is it|now|right now|here|there)\b|\bwhat time is it\b|\bcurrent (?:time|date)\b"
    r"|\btoday'?s date\b|\bwhat day is (?:it|today)\b|\bwhich day is today\b|\bdate today\b"
    r"|كم الساعة|الساعة كم|الساعه كم|كم الساعه|ما الوقت|الوقت الآن|الوقت الان|كم الوقت|ما التاريخ|تاريخ اليوم|"
    r"ما هو التاريخ|أي يوم|اي يوم|اليوم كم|شو الساعة|شو الوقت|ايش الوقت|إيش الوقت|الساعة كام|الساعه كام", re.I)

OFF_TOPIC = re.compile(
    r"\bweather\b|\btemperature\b|\bforecast\b|\braining\b|\bthe news\b|\bheadlines\b|\bfootball\b|\bmatch score\b|\bstocks?\b"
    r"|\bexchange rate\b|\bgold price\b|\brecipe\b|\btell me a joke\b|\bcapital of\b|\bwho is the (?:president|king|"
    r"prime minister|ceo)\b|\bprayer times?\b|\btraffic\b|\bflight\b|\bbitcoin\b|\bmovie\b"
    r"|الطقس|الجو |درجة الحرارة|نشرة الأخبار|آخر الأخبار في|مباراة|كرة القدم|الأسهم|سعر الذهب|سعر الصرف|وصفة|نكتة|عاصمة|"
    r"مواقيت الصلاة|أوقات الصلاة|الزحمة|رحلة طيران|بيتكوين|فيلم", re.I)

# a clock time or a written date in a model reply: the model has no clock, so it must not state one
MODEL_TIME = re.compile(r"\b\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?\b|الساعة\s*\d", re.I)

DAYS = {"en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "ar": ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]}
MONTHS_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر",
             "ديسمبر"]


def now_uae(now: Optional[datetime] = None) -> datetime:
    return (now or datetime.now(timezone.utc)).astimezone(UAE)


def is_clock_question(text: str) -> bool:
    return bool(CLOCK.search(to_ascii_digits(text or "")))


def is_off_topic(text: str) -> bool:
    return bool(OFF_TOPIC.search(text or ""))


def clock_reply(lang: str, now: Optional[datetime] = None) -> str:
    t = now_uae(now)
    day = DAYS["ar" if lang == "ar" else "en"][t.weekday()]
    if lang == "ar":
        hour = t.hour % 12 or 12
        part = "صباحاً" if t.hour < 12 else "مساءً"
        return (f"الوقت الآن في الإمارات {hour}:{t.minute:02d} {part}، يوم {day} {t.day} {MONTHS_AR[t.month - 1]} "
                f"{t.year} (حسب ساعة هذا النظام، بتوقيت الإمارات). هل يمكنني مساعدتك في طلب المعادلة؟")
    return (f"It is {t.strftime('%I:%M %p').lstrip('0')} on {day}, {t.day} {t.strftime('%B %Y')} in the UAE "
            "(from this system's clock, UAE time). Can I help you with the equivalency request?")


def off_topic_reply(lang: str) -> str:
    if lang == "ar":
        return ("أستطيع المساعدة في خدمة معادلة شهادات صفوف النقل فقط، ولا أملك اتصالاً بالإنترنت، لذلك لا أقدم معلومات "
                f"لا يمكنني التأكد منها. لأي استفسار آخر يمكنك التواصل مع الوزارة على الرقم المجاني {MOE_SUPPORT_NUMBER}.")
    return ("I can only help with the class transfer equivalency service, and I have no internet access, so I don't give "
            "information I cannot confirm. For anything else, the Ministry can help on its toll-free number "
            f"{MOE_SUPPORT_NUMBER}.")


# ------------------------------------------------------------------ two more fixed answers (found live, 21 October)
# "I have 3 children, can I apply for all of them in one request?" got a general description of the service
SEVERAL_CHILDREN = re.compile(
    r"\b(?:\d+|two|three|four|five|several|multiple|many)\s+(?:kids|children|sons|daughters|students)\b"
    r"|\b(?:all|both)\s+(?:of\s+)?(?:my\s+)?(?:kids|children|sons|daughters)\b|\bmore than one (?:child|kid|student)\b"
    r"|(?:\d|اثنين|ثلاثة|أربعة|طفلين|ولدين|بنتين|أكثر من)\s*(?:أطفال|اطفال|أولاد|اولاد|أبناء|ابناء|طلاب|طفل|ولد)"
    r"|(?:كلهم|جميعهم|نفس الطلب)[^.؟?]{0,25}(?:أطفال|اطفال|أولاد|اولاد|أبناء|ابناء)"
    r"|(?:أطفال|اطفال|أولاد|اولاد|أبناء|ابناء)[^.؟?]{0,25}(?:كلهم|جميعهم|نفس الطلب|معاً|معا|سوا)", re.I)

# "Can you give me my son's passport number from the files?" (a request to READ a number out; typing one in is
# handled separately by the privacy check)
ASKS_DOC_NUMBER = re.compile(
    r"\b(?:give|tell|show|send|read|repeat|what(?:'?s| is))\b[^.?]{0,35}\b(?:passport|emirates id|eid|visa|id)\s*"
    r"(?:number|no\b|#)"
    r"|(?:أعطني|اعطني|تعطيني|عطني|أرسل|ارسل|ما هو|ماهو|شو|ايش|إيش|اقرأ|اقرا|كم)[^.؟?]{0,25}رقم\s*"
    r"(?:جواز|الجواز|الهوية|هوية|الإقامة|الاقامة|إقامة|اقامة)", re.I)


def is_several_children(text: str) -> bool:
    return bool(SEVERAL_CHILDREN.search(to_ascii_digits(text or "")))


def asks_doc_number(text: str) -> bool:
    return bool(ASKS_DOC_NUMBER.search(text or ""))


def several_children_reply(lang: str) -> str:
    if lang == "ar":
        return ("كل طلب يخص طالباً واحداً: المستندات والقرار يخصان ذلك الطالب. إذا كان لديك أكثر من طفل، قدّم طلباً "
                "منفصلاً لكل طفل بمستنداته ورسومه. وللتأكد من حالتك يمكنك التواصل مع الوزارة على الرقم المجاني "
                f"{MOE_SUPPORT_NUMBER}.")
    return ("Each request is for one student: the documents and the decision belong to that child. For several "
            "children, submit one request per child, each with their own documents and fee. To confirm anything "
            f"about your case, the Ministry can help on its toll-free number {MOE_SUPPORT_NUMBER}.")


def doc_number_reply(lang: str) -> str:
    if lang == "ar":
        return ("حفاظاً على الخصوصية، لا أعرض أرقام الجوازات أو الهويات أو الإقامات في المحادثة. تجدها في مستنداتك، "
                "ويطّلع عليها الموظف في الطلب. يمكنني إخبارك هل اجتاز كل مستند الفحص.")
    return ("For privacy, I never show passport, ID or visa numbers in the chat. You can see them on your own "
            "documents, and the officer sees them in the case. I can tell you whether each document passed the checks.")
