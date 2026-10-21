"""Answers the parent's actual question, in their language, from the service card and the case record (P-10, P-15).

Before: every service question got the whole service card. Now the question is matched to the card section(s)
it is about (fee, time, documents, attestation, translation, visa, file format, term statements, process,
support) and only those lines are quoted, followed by one line saying what to do next in THIS case.

Everything here is deterministic: the topics are found by fixed word lists (English and Arabic), the answer
lines are the card's own lines (without the internal rule IDs), and the next step comes from the case record.
The language model is not involved, so these answers cannot invent a requirement, a fee or a policy.
"""
from __future__ import annotations

import re
from typing import Optional

from .config import MOE_SUPPORT_NUMBER, SERVICE_FEE_AED
from .language import to_ascii_digits
from .models import CaseState, CaseStatus, Outcome
from .rules import GRADE_MAX, GRADE_MIN, is_gcc
from .service_card import CARD, public

# topic -> pattern (English and Arabic, including Gulf spellings). Order = order of the answer.
TOPICS: dict[str, re.Pattern] = {
    "about": re.compile(r"about (this|the) service|what is this service|what does (this|the) service|tell me about"
                        r"|عن الخدمة|عن هذه الخدمة|ما هي (هذه )?الخدمة|شو هي الخدمة|ايش هي الخدمة|وش هي الخدمة", re.I),
    "steps": re.compile(r"\bhow (do|can|does) (i|we|it)\b.*\b(apply|start|work|submit)|\bsteps?\b|\bprocess\b"
                        r"|كيف (أقدم|اقدم|أبدأ|ابدأ|التقديم|تتم)|الخطوات|إجراءات|اجراءات|طريقة التقديم", re.I),
    "documents": re.compile(r"\bdocuments?\b|\bpapers?\b|\brequirements?\b|\brequired\b|\bwhat (do|does) (i|we|he|she) need"
                            r"|\bwhat.*\bneed\b|\bupload what\b|\brequi?re?ments?\b|\brequir\w*|\bneeded\b"
                            r"|المستندات|مستندات|الوثائق|وثائق|المطلوب|أحتاج|احتاج|نحتاج"
                            r"|الورق|ورق المطلوب|الاوراق|أوراق"
                            r"|شو المطلوب|ايش المطلوب|إيش المطلوب|المتطلبات|متطلبات|الأوراق|اوراق", re.I),
    "attestation": re.compile(r"attest|stamp|embassy|attach[eé]|foreign affairs|\bmofa\b|legali[sz]"
                              r"|تصديق|مصدق|ختم|السفارة|سفارة|الخارجية|الملحق", re.I),
    "translation": re.compile(r"translat|\bfrench\b|\bgerman\b|\bspanish\b|\burdu\b|other language|not in english"
                              r"|ترجمة|مترجم|الفرنسية|بالفرنسي|لغة أخرى|لغه", re.I),
    "visa": re.compile(r"\bvisa\b(?!\s*card)|residen|\bgcc\b|kuwait|saudi|\bksa\b|emirati|qatari|bahraini|omani|\bgulf\b"
                       r"|إقامة|اقامة|الإقامة|تأشيرة|خليجي|مجلس التعاون|كويتي|سعودي|قطري|بحريني|عماني|إماراتي", re.I),
    "format": re.compile(r"\bpdf\b|\bjpe?g\b|\bpng\b|\bphoto\b|\bpicture\b|\bscan|\bfile (size|format|type)|\bmb\b"
                         r"|\bmegabyte|how big|صيغة|حجم|صورة|ميجا|الملف|ملفات", re.I),
    "term": re.compile(r"term (report|statement|certificate)|mid[- ]?year|half[- ]?year|interim|not finished the year"
                       r"|middle of the (school |academic )?year|before the end of the year|first term|second term"
                       r"|إفادة فصلية|افادة فصلية|الفصل الأول|نصف العام|منتصف العام", re.I),
    "payment": re.compile(r"apple ?pay|google ?pay|samsung ?pay|credit card|debit card|\bcard\b|pay (online|by|with)"
                          r"|\b(how|where|can) (do|can|should)? ?(i|we) pay\b|\bpayment (method|options?)\b"
                          r"|كيف (أدفع|ادفع|يتم الدفع|الدفع)|وين ادفع|أين أدفع"
                          r"|أبل باي|ابل باي|آبل باي|جوجل باي|قوقل باي|سامسونج باي|بطاقة|ببطاقة|فيزا كارد|طريقة الدفع", re.I),
    "fee": re.compile(r"\bfees?\b|\bcost\b|\bprice\b|how much|\bcharge"
                      r"|رسوم|الرسوم|تكلفة|التكلفة|كم السعر|بكم|كم يكلف", re.I),
    "time": re.compile(r"how long|\bhow many days\b|\bwhen will\b|\bservice time\b|\bduration\b|\btake\b.*\b(days?|long)\b"
                       r"|كم المدة|كم مدة|المدة|كم يستغرق|كم يوم|متى (سأحصل|يصدر|تصدر|يصل|أستلم)|وقت الخدمة"
                       r"|ياخذ وقت|تاخذ وقت|يأخذ وقت|كم ياخذ|كم تاخذ|قديش بياخذ|اد ايه|أد إيه|متى يطلع|متى تطلع", re.I),
    "eligible": re.compile(r"\beligib|\bqualif|\bcan (he|she|my \w+) (apply|transfer|join)|will (it|he|she|they) be "
                           r"(accepted|approved)|مؤهل|يستحق|تنطبق علي|هل (يقبل|تقبل|ينقبل) (ابني|بنتي|ابنتي|طلبي)", re.I),
    "support": re.compile(r"\bcontact\b|\bphone\b|\bcall\b|\bhotline\b|\bcustomer service\b|\bspeak to\b.*\bministry\b"
                          r"|رقم الهاتف|التواصل|اتصل|خدمة العملاء|الرقم المجاني", re.I),
}
STRONG_DOCS = re.compile(r"\bdocuments?\b|\bpapers?\b|\brequirements?\b|\brequi?re?ments?\b|المستندات|مستندات|الوثائق|وثائق|المتطلبات"
                         r"|متطلبات|الأوراق|اوراق|أوراق|الورق|شو المطلوب|ايش المطلوب|إيش المطلوب|ايه المطلوب|إيه المطلوب", re.I)
QUESTION = re.compile(r"\?|؟|^(what|which|how|when|do|does|can|is|are|should|where|why)\b"
                      r"|^(ما|ماذا|كم|كيف|هل|متى|أين|وين|ليش|لماذا|شو|ايش|إيش|وش)\b"
                      r"|\b(i want to know|tell me|i would like to know|i'd like to know)\b"
                      r"|(عايز|عاوز|ابغى|أبغى|ابي|أبي|بدي|اريد|أريد|حاب) (اعرف|أعرف|افهم|أفهم)|قل لي|قولي|ابي اعرف", re.I)

LEAD = {
    "steps": ("How the service works:", "إجراءات الخدمة:"),
    "documents": ("Documents to attach:", "المستندات المطلوبة:"),
    "attestation": ("Attestation:", "التصديق:"),
    "translation": ("Certificates in another language:", "الشهادات بلغة أخرى:"),
    "visa": ("UAE visa:", "الإقامة:"),
    "format": ("Files:", "الملفات:"),
    "term": ("Term statements:", "الإفادات الفصلية:"),
    "fee": ("Fee:", "الرسوم:"),
    "payment": ("Payment:", "الدفع:"),
    "time": ("Service time:", "وقت الخدمة:"),
    "support": ("Support:", "الدعم:"),
    "eligible": ("Eligibility:", "الأهلية:"),
}
PHOTO = re.compile(r"\bphoto|\bpicture|\bjpe?g\b|\bpng\b|\bscreenshot|صورة|صوره|جوال|الجوال|الهاتف", re.I)
PHOTO_NOTE = ("A photo (JPG or PNG) is not accepted as it is: please save or scan it as a PDF first.",
              "لا تُقبل الصورة (JPG أو PNG) كما هي: يرجى حفظها أو مسحها ضوئياً بصيغة PDF أولاً.")
GREETING = re.compile(r"^\s*(hi+|hello|hey|good (morning|afternoon|evening)|salam|assalamu? ?alaikum|السلام عليكم"
                      r"|سلام|مرحبا|مرحباً|أهلا|اهلا|أهلاً|صباح الخير|مساء الخير|هلا)\W*$", re.I)
GREETING_REPLY = (
    "Hello, and welcome. I can help you request the equivalency certificate for school grades completed outside the "
    "UAE (Grades 2 to 11). Tell me which grade was completed and in which country, ask me anything about the service, "
    "or attach the documents and I will check them.",
    "أهلاً وسهلاً بك. يمكنني مساعدتك في طلب شهادة معادلة للصفوف الدراسية المنجزة خارج الدولة (من الصف الثاني إلى "
    "الحادي عشر). أخبرني بالصف الذي أنهاه الطالب وفي أي دولة، أو اسألني عن أي شيء يخص الخدمة، أو أرفق المستندات وسأقوم "
    "بفحصها.")
THANKS = re.compile(r"^\W*(thanks?( you)?( so much| a lot)?|thx|ty|cheers|great|perfect|ok(ay)?( thanks?)?|good"
                    r"|شكرا|شكراً|شكرًا|مشكور|مشكورة|يعطيك العافية|تسلم|جزاك الله خير(ا)?|ممتاز|تمام|طيب|اوكي|حلو)\W*"
                    r"(very much|جزيلا|جزيلاً|كثير)?\W*$", re.I)
PERSONAL = re.compile(r"\b784[\s-]?\d{4}[\s-]?\d{7}[\s-]?\d\b|\b0?5\d[\s-]?\d{3}[\s-]?\d{4}\b|\+971"
                      r"|[\w.+-]+@[\w-]+\.[\w.]+|\bpassport (no|number)\b.*\d{5,}")
PRIVACY_REPLY = ("For your privacy, please do not type ID numbers, phone numbers or email addresses in the chat. Attach "
                 "the documents instead, and I will read what is needed from them.",
                 "حفاظاً على خصوصيتك، يرجى عدم كتابة أرقام الهوية أو الهاتف أو البريد الإلكتروني في المحادثة. أرفق "
                 "المستندات بدلاً من ذلك وسأقرأ منها ما يلزم.")
WELCOME_BACK = ("You're welcome.", "على الرحب والسعة.")
UNCLEAR = ("I did not quite understand that. You can ask me about the documents, the fee or the service time, tell me "
           "which grade was completed, or attach the documents and I will check them.",
           "لم أفهم رسالتك تماماً. يمكنك أن تسألني عن المستندات أو الرسوم أو وقت الخدمة، أو تخبرني بالصف الذي أنهاه "
           "الطالب، أو ترفق المستندات وسأقوم بفحصها.")


def is_unclear(text: str) -> bool:
    """No words at all (empty, punctuation, emoji) or one long run of the same letter."""
    t = (text or "").strip()
    letters = re.sub(r"[\W\d_]", "", t)
    return not letters or (len(letters) >= 6 and len(set(letters.lower())) <= 2)


GCC_NOTE = ("This depends on the student's nationality, not on the country where the student studied or lived: a "
            "student who holds the nationality of a GCC country does not need a UAE visa, while a student of another "
            "nationality does, even if the family lived in a GCC country.",
            "يعتمد ذلك على جنسية الطالب، وليس على الدولة التي درس أو أقام فيها: الطالب الذي يحمل جنسية إحدى دول مجلس "
            "التعاون لا يحتاج إلى إقامة، أما الطالب من جنسية أخرى فيحتاج إليها حتى لو كانت الأسرة مقيمة في إحدى دول المجلس.")
ON_RECORD = (("The student's identity record (UAE Pass) shows a GCC nationality, so no UAE visa is needed.",
              "يُظهر سجل هوية الطالب (الهوية الرقمية) جنسية إحدى دول مجلس التعاون، لذلك لا تلزم الإقامة."),
             ("The student's identity record (UAE Pass) shows a nationality outside the GCC, so a valid UAE visa is "
              "required.",
              "يُظهر سجل هوية الطالب (الهوية الرقمية) جنسية من خارج دول مجلس التعاون، لذلك تلزم إقامة سارية المفعول."))


NO_NATIONALITY = ("The student's identity record (UAE Pass) shows no nationality, so the GCC exemption cannot apply and "
                  "a valid UAE visa is required.",
                  "لا يُظهر سجل هوية الطالب (الهوية الرقمية) أي جنسية، لذلك لا ينطبق إعفاء مواطني دول مجلس التعاون وتلزم "
                  "إقامة سارية المفعول.")


def visa_on_record(s: CaseState, lang: str) -> str:
    """One line: does THIS student need a UAE visa, from the nationality on record."""
    if not (s.profile.student.nationality or "").strip():
        return NO_NATIONALITY[1 if lang == "ar" else 0]
    return ON_RECORD[0 if is_gcc(s.profile.student.nationality) else 1][1 if lang == "ar" else 0]


def topics_in(text: str) -> list[str]:
    t = to_ascii_digits(text or "")
    found = [k for k, p in TOPICS.items() if p.search(t)]
    if ("documents" in found and not STRONG_DOCS.search(t)
            and set(found) & {"visa", "translation", "format", "attestation", "term", "eligible"}):
        found.remove("documents")                 # "do I need a visa?" is about the visa, not the whole list
        # ("what do I need and how much is it?" keeps the documents: the fee is a separate question)
    if "documents" in found:                      # already part of the documents answer
        found = [k for k in found if k not in ("attestation", "term", "translation", "visa")]
    return found


# Topics a parent raises by stating a fact ("we are Syrians but lived in Saudi Arabia", "the report is in French"):
# answered even without a question mark, because the statement is the concern.
RAISED = {"visa", "translation", "format", "term", "attestation"}


def is_question(text: str) -> bool:
    return bool(QUESTION.search((text or "").strip()))


def _card_lines(topic: str, lang: str) -> list[str]:
    c = CARD["ar" if lang == "ar" else "en"]
    docs, cond, notes = c["documents"], c["conditions"], c["notes"]
    if topic == "steps":
        return [f"{i}. {x}" for i, x in enumerate(c["steps"], 1)]
    if topic == "documents":
        # the documents and the conditions they must meet (attestation, complete year) belong together
        return [f"- {public(x)}" for x in docs] + ["", f"**{c['conditions_label']}:**"] + [f"- {public(x)}" for x in cond]
    if topic == "attestation":
        return [f"- {public(x)}" for x in cond[:2]]
    if topic == "translation":
        return [f"- {public(docs[4])}"]
    if topic == "visa":
        return [f"- {public(docs[2])}"]
    if topic == "format":
        return [f"- {public(x)}" for x in notes]
    if topic == "term":
        return [f"- {public(cond[2])}"]
    if topic == "fee":
        return [f"- {c['fee']}"]
    if topic == "time":
        return [f"- {c['time']}"]
    if topic == "support":
        return [f"- {c['support']}"]
    return []


# Single facts are answered in one plain sentence (the values are the card's: Fees, Service time, Support).
SENTENCE = {
    "fee": (f"The fee for this service is {SERVICE_FEE_AED} AED. You pay it online in the secure payment window once "
            "your documents pass the checks.",
            f"رسوم هذه الخدمة {SERVICE_FEE_AED} درهماً، وتُدفع إلكترونياً في نافذة الدفع الآمنة بعد اجتياز المستندات "
            "للفحص."),
    "time": ("The service time is 30 working days. Your documents are checked here as soon as you attach them, and once "
             "every requirement is met the request is submitted straight away. A Ministry officer then issues the "
             "equivalency decision within the 30 working days, and it is sent to the email registered in UAE Pass.",
             "مدة الخدمة 30 يوم عمل. يتم فحص مستنداتك هنا فور إرفاقها، وعند استيفاء جميع المتطلبات يُقدَّم الطلب مباشرة. "
             "بعد ذلك يُصدر موظف الوزارة قرار المعادلة خلال 30 يوم عمل، ويُرسل إلى البريد الإلكتروني المسجل في الهوية "
             "الرقمية."),
    "payment": ("The payment window accepts a bank card, Apple Pay, Google Pay or Samsung Pay. It opens here as soon "
                "as your documents pass the checks.",
                "تقبل نافذة الدفع البطاقة البنكية أو Apple Pay أو Google Pay أو Samsung Pay، وتفتح هنا فور اجتياز "
                "المستندات للفحص."),
    "eligible": ("Whether a request meets the service requirements is decided by checking the attached documents against "
                 "the service rules, not in advance. The service covers certificates for Grades 2 to 11 issued outside "
                 "the UAE. Attach the documents and I will check them straight away; a Ministry officer issues the "
                 "equivalency decision.",
                 "يتم التحقق من استيفاء الطلب لمتطلبات الخدمة بفحص المستندات المرفقة وفق شروط الخدمة، وليس مسبقاً. تشمل "
                 "الخدمة شهادات الصفوف من الثاني إلى الحادي عشر الصادرة من خارج الدولة. أرفق المستندات وسأفحصها فوراً، "
                 "ويُصدر موظف الوزارة قرار المعادلة."),
    "support": (f"You can reach the Ministry on its toll-free number {MOE_SUPPORT_NUMBER}.",
                f"يمكنك التواصل مع الوزارة على الرقم المجاني {MOE_SUPPORT_NUMBER}."),
}


def answer_topics(found: list[str], text: str, lang: str, s: Optional[CaseState] = None, repeat: bool = False) -> str:
    """repeat: the same sections were quoted in the previous reply, so they are not quoted again in full."""
    ar = lang == "ar"
    parts = []
    for topic in found:
        if topic == "about" and s is not None:
            parts.append(overview(s, lang))
            continue
        if repeat and topic == "documents" and s is not None:
            from .messages import say
            parts.append(say("as_above", lang) + " " + documents_for(s, s.stated_grade, lang))
            continue
        if topic == "documents" and s is not None:
            parts.append(case_documents(s, lang))
            note = nationality_note(s, lang)
            if note:
                parts.append(note)
            continue
        if topic in SENTENCE:
            parts.append(SENTENCE[topic][1 if ar else 0])
            continue
        block = [f"**{LEAD[topic][1 if ar else 0]}**", *_card_lines(topic, lang)]
        if topic == "visa":
            block += ["", GCC_NOTE[1 if ar else 0]]
            if s is not None and s.profile is not None:
                block.append(visa_on_record(s, lang))
        if topic == "format" and PHOTO.search(text or ""):
            block += ["", PHOTO_NOTE[1 if ar else 0]]
        parts.append("\n".join(block))
    return "\n\n".join(parts)


# ------------------------------------------------------------------ what to do next, from the case record
def stated_grade_ok(grade: Optional[int]) -> bool:
    return grade is not None and GRADE_MIN <= grade <= GRADE_MAX


def documents_for(s: CaseState, grade: Optional[int], lang: str) -> str:
    """The documents this parent needs, worded for their case (grade stated, GCC known from the record)."""
    ar = lang == "ar"
    gcc = s.profile is not None and is_gcc(s.profile.student.nationality)
    if stated_grade_ok(grade):
        certs = (f"شهادتي الصف {grade} والصف {grade - 1}" if ar
                 else f"the Grade {grade} and Grade {grade - 1} certificates")
    else:
        certs = "شهادات آخر سنتين دراسيتين" if ar else "the certificates of the last two years of study"
    if ar:
        visa = "" if gcc else ("، والإقامة" if s.profile is not None else "، والإقامة (لغير أبناء دول مجلس التعاون)")
        return (f"جواز سفر الطالب، والهوية الإماراتية{visa}، و{certs}، مع تصديقها كما تشترط الخدمة. "
                "الشهادة بغير العربية أو الإنجليزية تحتاج إلى ترجمة قانونية. الملفات بصيغة PDF وبحجم 5 ميجابايت كحد أقصى.")
    visa = "" if gcc else (", the UAE visa" if s.profile is not None else ", the UAE visa (not needed for GCC nationals)")
    return (f"the student's passport, Emirates ID{visa}, and {certs}, attested as the service requires. "
            "A certificate in a language other than Arabic or English needs a legal translation. "
            "Files are PDF, 5 MB maximum each.")


def next_step(s: CaseState, lang: str, grade: Optional[int] = None, listed: bool = False) -> str:
    """One line: what the parent should do now in this case. `listed`: the documents were just listed above."""
    ar = lang == "ar"
    if s.status == CaseStatus.AWAITING_PAYMENT:
        return (f"الخطوة التالية: ادفع رسوم الخدمة البالغة {SERVICE_FEE_AED} درهماً في نافذة الدفع لتقديم طلبك." if ar
                else f"Next step: pay the AED {SERVICE_FEE_AED} fee in the payment window to submit your request.")
    if s.is_closed() or s.status == CaseStatus.REDIRECTED:
        return ""
    if not s.uploads:
        if listed:
            return ("الخطوة التالية: أرفق هذه المستندات هنا وسأقوم بفحصها فوراً." if ar
                    else "Next step: attach these documents here and I will check them straight away.")
        gcc = s.profile is not None and is_gcc(s.profile.student.nationality)
        certs = (f"شهادتي الصف {grade} والصف {grade - 1}" if ar else f"the Grade {grade} and Grade {grade - 1} certificates") \
            if stated_grade_ok(grade) else ("شهادات آخر سنتين" if ar else "the certificates of the last two years")
        known = s.profile is not None
        if ar:
            visa = "" if gcc else (" والإقامة" if known else " والإقامة (لغير أبناء دول المجلس)")
            return f"الخطوة التالية: أرفق جواز السفر والهوية الإماراتية{visa} و{certs}."
        visa = "" if gcc else (", UAE visa" if known else ", UAE visa (not needed for GCC nationals)")
        return f"Next step: attach the passport, Emirates ID{visa} and {certs}."
    if s.rule_report is not None and not s.rules_stale and s.rule_report.outcome == Outcome.NEEDS_INFO:
        return ("الخطوة التالية: أرفق ما ينقص من القائمة أعلاه وسأعيد فحص الطلب." if ar
                else "Next step: attach what is still missing from the list above, and I will check the request again.")
    return ""


def guided_start(s: CaseState, grade: int, lang: str) -> str:
    """The parent told us the grade (inside this service) but has not attached anything yet."""
    if lang == "ar":
        return (f"الصف {grade} ضمن نطاق هذه الخدمة (من الصف الثاني إلى الحادي عشر). لتقديم الطلب، أرفق "
                + documents_for(s, grade, lang) + " سأقوم بفحصها فور إرفاقها.")
    return (f"Grade {grade} is covered by this service (Grades 2 to 11). To apply, attach "
            + documents_for(s, grade, lang) + " I will check them as soon as they are attached.")


def overview(s: CaseState, lang: str) -> str:
    """A general question about the service: what it is, what to attach, fee and time, in a few lines (P-15),
    instead of the whole card. Every fact is the card's."""
    ar = lang == "ar"
    c = CARD["ar" if ar else "en"]
    lines = [public(c["covers"]), "",
             ("للتقديم، أرفق " if ar else "To apply, attach ") + documents_for(s, s.stated_grade, lang), "",
             SENTENCE["fee"][1 if ar else 0], SENTENCE["time"][1 if ar else 0], "",
             ("اسألني عن أي تفصيل، مثل التصديق أو الترجمة أو الإقامة." if ar
              else "Ask me about any detail, for example attestation, translation or the visa.")]
    return "\n".join(lines)


# ------------------------------------------------------------------ the documents for THIS case (P-15)
# Countries a parent may name, English and Arabic -> one display name per language. Used only to word the attestation
# lines ("attested in Oman"); the rules use the verified documents, and the visa uses the nationality on record.
COUNTRIES = {
    "oman": ("Oman", "عُمان", r"\boman\b|عمان|عُمان"), "kuwait": ("Kuwait", "الكويت", r"\bkuwait\b|الكويت"),
    "saudi": ("Saudi Arabia", "السعودية", r"\bsaudi\b|\bksa\b|السعودية|السعوديه"),
    "qatar": ("Qatar", "قطر", r"\bqatar\b|قطر"), "bahrain": ("Bahrain", "البحرين", r"\bbahrain\b|البحرين"),
    "india": ("India", "الهند", r"\bindia\b|الهند"), "pakistan": ("Pakistan", "باكستان", r"\bpakistan\b|باكستان"),
    "egypt": ("Egypt", "مصر", r"\begypt\b|مصر"), "jordan": ("Jordan", "الأردن", r"\bjordan\b|الأردن|الاردن"),
    "syria": ("Syria", "سوريا", r"\bsyria\b|سوريا|سورية"), "lebanon": ("Lebanon", "لبنان", r"\blebanon\b|لبنان"),
    "iraq": ("Iraq", "العراق", r"\biraq\b|العراق"), "sudan": ("Sudan", "السودان", r"\bsudan\b|السودان"),
    "yemen": ("Yemen", "اليمن", r"\byemen\b|اليمن"), "morocco": ("Morocco", "المغرب", r"\bmorocco\b|المغرب"),
    "tunisia": ("Tunisia", "تونس", r"\btunisia\b|تونس"), "algeria": ("Algeria", "الجزائر", r"\balgeria\b|الجزائر"),
    "palestine": ("Palestine", "فلسطين", r"\bpalestine\b|فلسطين"), "kenya": ("Kenya", "كينيا", r"\bkenya\b|كينيا"),
    "sri lanka": ("Sri Lanka", "سريلانكا", r"\bsri lanka\b|سريلانكا|سري لانكا"),
    "philippines": ("the Philippines", "الفلبين", r"\bphilippines\b|الفلبين"),
    "bangladesh": ("Bangladesh", "بنغلاديش", r"\bbangladesh\b|بنغلاديش"), "nepal": ("Nepal", "نيبال", r"\bnepal\b|نيبال"),
    "uk": ("the United Kingdom", "المملكة المتحدة", r"\buk\b|united kingdom|\bengland\b|بريطانيا|المملكة المتحدة"),
    "usa": ("the United States", "الولايات المتحدة", r"\busa\b|united states|\bamerica\b|أمريكا|امريكا|الولايات المتحدة"),
    "canada": ("Canada", "كندا", r"\bcanada\b|كندا"), "france": ("France", "فرنسا", r"\bfrance\b|فرنسا"),
    "germany": ("Germany", "ألمانيا", r"\bgermany\b|ألمانيا|المانيا"),
}
GCC_KEYS = {"oman", "kuwait", "saudi", "qatar", "bahrain"}


def country_in(text: str) -> Optional[str]:
    t = (text or "").lower()
    for key, (_, _, pat) in COUNTRIES.items():
        if re.search(pat, t):
            return key
    return None


def case_documents(s: CaseState, lang: str) -> str:
    """The card's documents and conditions filled in with what is known about THIS case: the grade the parent
    stated, the nationality on the UAE Pass record (visa) and the country they named (attestation). Each line is a
    card line (R-02 to R-11); only the blanks are filled. Nothing here decides anything: the rules check the files."""
    ar = lang == "ar"
    g = s.stated_grade if stated_grade_ok(s.stated_grade) else None
    known = s.profile is not None
    gcc = known and is_gcc(s.profile.student.nationality)
    named = COUNTRIES.get(s.stated_country or "")
    where = (named[1] if ar else named[0]) if named else None
    if ar:
        head = "**المستندات المطلوبة لطلبك:**" if (g or known or where) else "**المستندات المطلوبة:**"
        lines = [head, "- جواز سفر الطالب ساري المفعول", "- الهوية الإماراتية سارية المفعول"]
        if not known:
            lines.append("- الإقامة سارية المفعول (لغير أبناء دول مجلس التعاون الخليجي)")
        elif not (s.profile.student.nationality or "").strip():
            lines.append("- الإقامة سارية المفعول (لا يُظهر سجل الهوية الرقمية جنسية الطالب)")
        elif not gcc:
            lines.append("- الإقامة سارية المفعول (جنسية الطالب في سجل الهوية الرقمية من خارج دول مجلس التعاون)")
        else:
            lines.append("- لا تلزم الإقامة: سجل الهوية الرقمية يُظهر جنسية إحدى دول مجلس التعاون")
        lines.append(f"- شهادتا الصف {g} والصف {g - 1} (آخر سنتين دراسيتين)" if g else "- شهادات آخر سنتين دراسيتين")
        cond = [public(x) for x in CARD["ar"]["conditions"]]      # the card's own words, then the case facts
        lines += ["- ترجمة قانونية لأي شهادة بغير العربية أو الإنجليزية",
                  "- مرفقات داعمة إن وجدت (مرفقان كحد أقصى)", "", "**التصديق:**",
                  f"- {cond[0]}" + (f" (بلد الإصدار: {where} إذا كان هو بلد الدراسة)" if where else ""),
                  f"- {cond[1]}" + (f" (آخر شهادة هنا هي شهادة الصف {g}.)" if g else ""),
                  f"- {cond[2]}", "",
                  "الملفات بصيغة PDF وبحجم 5 ميجابايت كحد أقصى لكل ملف، والمستند الواحد في ملف واحد."]
        if g:
            lines += ["", f"(بناءً على أن الصف {g} هو آخر صف أنهاه الطالب. إذا كان قد أنهى الصف {g + 1}، "
                          f"فأرفق شهادتي الصف {g + 1} والصف {g}.)" if g < GRADE_MAX else
                      f"(بناءً على أن الصف {g} هو آخر صف أنهاه الطالب.)"]
        return "\n".join(lines)
    head = "**Documents for your request:**" if (g or known or where) else "**Documents to attach:**"
    lines = [head, "- The student's valid passport", "- Valid Emirates ID"]
    if not known:
        lines.append("- Valid UAE visa (not needed for GCC nationals)")
    elif not (s.profile.student.nationality or "").strip():
        lines.append("- Valid UAE visa (the student's UAE Pass record shows no nationality)")
    elif not gcc:
        lines.append("- Valid UAE visa (the nationality on the student's UAE Pass record is outside the GCC)")
    else:
        lines.append("- No UAE visa needed: the UAE Pass record shows a GCC nationality")
    lines.append(f"- Grade {g} and Grade {g - 1} certificates (the last two years of study)" if g
                 else "- Certificates of the last two years of study")
    lines += ["- Legal translation of any certificate that is not in Arabic or English",
              "- Supporting documents if you have any (2 at most)", "", "**Attestation:**"]
    cond = [public(x) for x in CARD["en"]["conditions"]]          # the card's own words, then the case facts
    lines += [f"- {cond[0]}" + (f" (Country of study: {where}, if that is where the student studied.)" if where else ""),
              f"- {cond[1]}" + (f" (Here the last certificate is the Grade {g} certificate.)" if g else ""),
              f"- {cond[2]}", "",
              "Files are PDF, 5 MB maximum each; one document goes in one file."]
    if g:
        lines += ["", (f"(Based on Grade {g} being the last grade completed. If Grade {g + 1} is already completed, "
                       f"attach the Grade {g + 1} and Grade {g} certificates instead.)") if g < GRADE_MAX else
                  f"(Based on Grade {g} being the last grade completed.)"]
    return "\n".join(lines)


def nationality_note(s: CaseState, lang: str) -> str:
    """The parent named a GCC country but the record says otherwise (or the reverse): say which one counts."""
    if s.profile is None or s.stated_country not in GCC_KEYS or not (s.profile.student.nationality or "").strip():
        return ""
    if is_gcc(s.profile.student.nationality):
        return ""
    name = COUNTRIES[s.stated_country][1 if lang == "ar" else 0]
    return (f"ذكرتَ {name}. بالنسبة للإقامة، المعتمد هو جنسية الطالب في سجل الهوية الرقمية، وهي من خارج دول مجلس "
            "التعاون، لذلك تلزم إقامة سارية المفعول. إذا كان السجل غير صحيح، يمكن للوزارة مساعدتك على الرقم المجاني "
            f"{MOE_SUPPORT_NUMBER}." if lang == "ar" else
            f"You mentioned {name}. For the visa, what counts is the student's nationality on the UAE Pass record, and "
            "it is outside the GCC, so a valid UAE visa is needed. If the record is wrong, the Ministry can help on its "
            f"toll-free number {MOE_SUPPORT_NUMBER}.")
