"""Language helpers. Deterministic: no language model is involved.

  * detect_language   which language the customer wrote in (decides the reply language, not the model)
  * to_ascii_digits   Arabic-Indic digits to 0-9, so number checks work on Arabic text too
  * normalize_name    compare names fairly: case, spaces and, for Arabic, diacritics and letter variants
  * stated_grade      the grade a customer says was completed, in English or Arabic (used by the no AI
                      interpreter and tests; the live model does its own reading, which is logged)
"""
from __future__ import annotations

import re
from typing import Optional

ARABIC_LETTER = re.compile(r"[ء-يٱ-ۓۺ-ۿ]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_TASHKEEL = re.compile(r"[ً-ْٰـ]")          # vowel marks and tatweel


def detect_language(text: str, default: str = "en") -> str:
    """'ar' or 'en' by the letters the customer used.
    * no letters (only digits, emoji, files)        -> the portal language (default)
    * Arabic and Latin mixed, on the Arabic portal  -> Arabic (e.g. "ابني finished Grade 6، what documents أحتاج؟")
    * otherwise                                     -> the script with more letters"""
    text = text or ""
    n_ar, n_en = len(ARABIC_LETTER.findall(text)), len(LATIN_LETTER.findall(text))
    if n_ar == 0 and n_en == 0:
        return default if default in ("en", "ar") else "en"
    if n_ar and default == "ar":
        return "ar"
    return "ar" if n_ar >= n_en else "en"


def to_ascii_digits(text: str) -> str:
    return (text or "").translate(_DIGITS)


def normalize_arabic(text: str) -> str:
    t = _TASHKEEL.sub("", text or "")
    t = re.sub("[إأآٱ]", "ا", t)
    t = t.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    return " ".join(t.split())


def normalize_name(name: Optional[str]) -> str:
    """Lower case, single spaces; Arabic diacritics and letter variants unified (ASSUMPTION A-05)."""
    return normalize_arabic(name or "").lower()


# ------------------------------------------------------------------ grades in Arabic
_ORDINALS = [  # longest first, so "الثاني عشر" is not read as "الثاني"
    ("الحادي عشر", 11), ("الثاني عشر", 12), ("الأول", 1), ("الاول", 1), ("الثاني", 2), ("الثالث", 3),
    ("الرابع", 4), ("الخامس", 5), ("السادس", 6), ("السابع", 7), ("الثامن", 8), ("التاسع", 9), ("العاشر", 10),
]
_STAGE = {"الابتدائي": 0, "الإعدادي": 6, "الاعدادي": 6, "المتوسط": 6, "الثانوي": 9}   # e.g. "الثاني المتوسط" = 8
_DONE_AR = re.compile(r"(أنه[ىت]|انه[ىت]|أكمل|اكمل|أكملت|اكملت|أتم|اتم|خلص|نجح|نجحت|تخرج|تخرجت|اجتاز|اجتازت)")
_JOIN_AR = re.compile(r"(سينتقل|ستنتقل|ينتقل|تنتقل|سيدخل|ستدخل|يلتحق|تلتحق|سيلتحق|ستلتحق)\s+(?:إلى|الى|ب)?\s*(?:ال)?صف")


# Egyptian and Levantine way of naming a year without the word "grade": "تانية اعدادي", "سادسة ابتدائي"
_COLLOQ = [("اولى", 1), ("أولى", 1), ("اول", 1), ("أول", 1), ("تانية", 2), ("تانيه", 2), ("ثانية", 2), ("ثانيه", 2),
           ("تاني", 2), ("ثاني", 2), ("تالتة", 3), ("تالته", 3), ("ثالثة", 3), ("ثالثه", 3), ("تالت", 3), ("ثالث", 3),
           ("رابعة", 4), ("رابعه", 4), ("رابع", 4), ("خامسة", 5), ("خامسه", 5), ("خامس", 5), ("سادسة", 6),
           ("سادسه", 6), ("سادس", 6)]
_STAGE_RE = r"(ابتدائي|ابتدائى|إعدادي|اعدادي|اعدادى|متوسط|ثانوي|ثانوى)"


def _arabic_grade(t: str) -> Optional[int]:
    t = to_ascii_digits(t)
    if "الثانوية العامة" in t:
        return 12
    for word, n in _COLLOQ:
        m = re.search(r"(?:^|\s)" + word + r"\s+(?:ال)?" + _STAGE_RE, t)
        if m:
            stage = m.group(1).replace("ى", "ي").replace("إ", "ا")
            return n + {"ابتدائي": 0, "اعدادي": 6, "متوسط": 6, "ثانوي": 9}[stage]
    if re.search(r"رياض الأطفال|الروضة|الروضه", t):
        return 0
    m = re.search(r"(?:ال)?صف\s*(\d{1,2})", t)
    if m:
        return int(m.group(1))
    for word, n in _ORDINALS:
        m = re.search(r"(?:ال)?صف\s+" + word + r"(?:\s+(الابتدائي|الإعدادي|الاعدادي|المتوسط|الثانوي))?", t)
        if m:
            return n + _STAGE.get(m.group(1) or "", 0)
    return None


_WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
_WORDS.update({w: i for i, w in enumerate(
    "zeroth first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth".split())})
_WORD_GRADE = re.compile(r"\b(?:grade|class|year)\s+(" + "|".join(_WORDS) + r")\b|\b(" + "|".join(_WORDS)
                         + r")\s+(?:grade|class)\b")
_CORRECTION = re.compile(r"\b(sorry|i meant|i mean|meant|actually|correction|no,?)\b")


def any_grade(text: str) -> int:
    """Any grade named, completed or not ("grade six", "الصف 6"); used only to read a correction after a redirect."""
    t = to_ascii_digits((text or "").lower())
    t = _WORD_GRADE.sub(lambda m: "grade " + str(_WORDS[m.group(1) or m.group(2)]), t)
    if (g := re.search(r"\b(?:grade|class|year)\s*(\d{1,2})\b", t)):
        return int(g.group(1))
    return (_arabic_grade(t) or 0) if ARABIC_LETTER.search(t) else 0


def stated_grade(text: str) -> int:
    """Last COMPLETED grade the customer states, 0 if not stated. 'Joining grade N' means N-1 was completed."""
    t = to_ascii_digits((text or "").lower())
    t = _WORD_GRADE.sub(lambda m: "grade " + str(_WORDS[m.group(1) or m.group(2)]), t)   # "grade six", "sixth grade"
    if _CORRECTION.search(t) and (g := re.search(r"grade\s*(\d{1,2})\b", t)) and not re.search(r"moving|join", t):
        return int(g.group(1))                                     # "sorry, I meant grade 6"
    done = re.search(r"(?:finished|completed|passed|graduated from)\s+(?:class|grade|year)\s*(\d{1,2})", t)
    joining = re.search(r"(?:moving|going|transferring)\s+(?:in)?to\s+(?:class|grade|year)\s*(\d{1,2})"
                        r"|join(?:ing)?\s+(?:class|grade|year)\s*(\d{1,2})", t)
    if done:
        return int(done.group(1))
    current = re.search(r"\b(?:is|are|was|son|daughter|child|kid|boy|girl) (?:now |currently )?in (?:class|grade|year)\s*(\d{1,2})\b", t)
    if current and 3 <= int(current.group(1)) <= 12:
        return int(current.group(1)) - 1                 # "my son is in grade 7": Grade 6 is the last one completed
    if joining:
        return int(joining.group(1) or joining.group(2)) - 1
    if any(w in t for w in ("finished", "completed", "passed", "graduated")) and (g := re.search(r"grade\s*(\d{1,2})", t)):
        return int(g.group(1))
    if ARABIC_LETTER.search(t):
        done = _DONE_AR.search(t)
        if done:
            # "أنهى الصف الأول وسينتقل إلى الصف الثاني": the grade right after the "finished" verb counts
            g_done = _arabic_grade(t[done.start():])
            if g_done is not None:
                return g_done
        g = _arabic_grade(t)
        if g is not None:
            if _JOIN_AR.search(t):
                return max(g - 1, 0)
            if _DONE_AR.search(t):
                return g
            if re.search(r"(?:^|\s)(?:في|بال)\s*الصف|يدرس|تدرس|حاليا|حالياً", t):
                return max(g - 1, 0)                     # "في الصف السابع" (now in Grade 7): Grade 6 completed
    return 0


# ------------------------------------------------------------------ asking for a person
# The customer must ASK for a person: a verb of asking or speaking plus a person word. A bare noun is not
# enough. Found by the Arabic scenarios: "أنا موظف في الوزارة" ("I AM a Ministry employee") and
# "وضع المسؤول" ("admin mode") contain the same nouns as "أريد موظف" ("I want an employee").
_PERSON_EN = r"(human|person|officer|staff( member)?|employee|someone|somebody|representative|agent|manager|supervisor|real person)"
_PERSON_AR = r"(موظف|موظفة|شخص|[إا]نسان|مسؤول|[أا]حد|خدمة العملاء|بشري)"
_ASK_PERSON = re.compile(
    r"\b(speak|talk|chat)\s+(to|with)\s+(a|an|the|some|your)?\s*(human|real\s+)?" + _PERSON_EN
    + r"|\b(want|need|like|get|connect me|transfer me|put me through)\b[^.?!\n]{0,25}\b" + _PERSON_EN
    + r"|\bcustomer service\b|\bcall (centre|center)\b"
    + r"|(أريد|اريد|[أا]بغى|[أا]بي|بدي|[أا]ود|ممكن|[أا]حتاج|[أا]رغب|حو[ّ]?لني|اربطني|وصلني)[^.؟?!\n]{0,25}" + _PERSON_AR
    + r"|(التحدث|[أا]تحدث|[أا]كلم|التواصل|الحديث)\s+(مع\s+)?" + _PERSON_AR,
    re.IGNORECASE)


# A question ABOUT a person's role is not a request to speak to one. Found in the final browser check: the suggested
# question "Why does my request need an officer?" was answered with the toll-free number first.
_ABOUT_PERSON = re.compile(r"\bwhy\b|\b(request|case|application)\s+(still\s+)?(needs?|requires?|goes|went|sent)\b"
                           r"|\bلماذا\b|\bليش\b|\bليه\b", re.IGNORECASE)
_SPEAK = re.compile(r"\b(speak|talk|chat)\s+(to|with)\b|التحدث|[أا]تحدث|[أا]كلم|التواصل", re.IGNORECASE)
_FIRST_PERSON = re.compile(r"\b(i|i'd|i'm|me|we)\b|[أا]ريد|[أا]بغى|[أا]بي\b|بدي|[أا]ود|[أا]حتاج|حو[ّ]?لني|اربطني|وصلني",
                           re.IGNORECASE)


def asks_for_person(text: str) -> bool:
    text = text or ""
    if not _ASK_PERSON.search(text):
        return False
    # "Why does my request need an officer?" asks about the referral; "why can't I talk to a person" still asks
    return not (_ABOUT_PERSON.search(text) and not _SPEAK.search(text) and not _FIRST_PERSON.search(text))


# "Why does my request need an officer?" is answered from the case record (P-04), whichever model is used
_WHY_OFFICER = re.compile(r"\bwhy\b[^?.!]*\b(officer|staff|employee|person|human|review\w*|referr\w*|escalat\w*)\b"
                          r"|(لماذا|ليش|ليه)[^؟?.!]*(موظف|مراجع|إحال|احال|أحيل|احيل)", re.IGNORECASE)


def asks_why_officer(text: str) -> bool:
    return bool(_WHY_OFFICER.search(text or "")) and not asks_for_person(text)
