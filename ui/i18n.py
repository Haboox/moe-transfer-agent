"""Every word on the screen, in English and Arabic. The page language is chosen with the language switch.

The assistant's replies do not come from here: they follow the language the parent writes in
(agent/language.py) and come from the agent (model text checked by the guards, or fixed messages).
"""
from __future__ import annotations

S = {
    # header and navigation
    "ministry": ("Ministry of Education", "وزارة التربية والتعليم"),
    "home": ("Home", "الرئيسية"),
    "services": ("Services", "الخدمات"),
    "page_title": ("Equivalency of Class Transfer Certificates Issued from Outside the UAE",
                   "معادلة شهادة دراسية صفوف النقل من خارج الدولة"),
    "service_title": ("Request for Equivalency Certificate for a Class Transfer from Outside the UAE",
                      "طلب معادلة شهادة دراسية صفوف النقل من خارج الدولة"),
    "view_parent": ("Parent portal", "بوابة ولي الأمر"),
    "view_staff": ("Staff portal", "بوابة الموظفين"),
    "other_lang": ("عربي", "English"),
    "theme_dark": ("Dark mode", "الوضع الداكن"),
    "theme_light": ("Light mode", "الوضع الفاتح"),
    "demo_ribbon": ("DEMO", "عرض تجريبي"),
    "demo_text": ("Prototype with synthetic data only. No real Ministry system, person or payment is involved.",
                  "نموذج أولي ببيانات اصطناعية فقط. لا يتصل بأي نظام حقيقي للوزارة ولا يتضمن أشخاصاً أو مدفوعات حقيقية."),
    "demo_controls": ("Demo controls", "أدوات العرض"),
    # demo controls
    "dc_title": ("Set up the demonstration", "إعداد العرض التجريبي"),
    "dc_applicant": ("Signed-in parent (mock UAE Pass) and test situation", "ولي الأمر المسجل (هوية رقمية تجريبية) وحالة الاختبار"),
    "dc_model": ("AI model", "نموذج الذكاء الاصطناعي"),
    "dc_failure": ("Simulate a Ministry system problem", "محاكاة عطل في أحد أنظمة الوزارة"),
    "dc_inner": ("Show how the agent decides", "عرض كيف يتخذ الوكيل قراراته"),
    "dc_start": ("Start new session", "بدء جلسة جديدة"),
    "dc_start_help": ("Start the same situation again with an empty chat", "إعادة بدء الحالة نفسها بمحادثة فارغة"),
    "dc_restarted": ("Started again.", "تمت إعادة البدء."),
    "dc_howto": ("Every choice applies at once and starts the demonstration again. Switching the page language keeps "
                 "the request.",
                 "كل اختيار يُطبَّق فوراً ويعيد بدء العرض. أما تغيير لغة الصفحة فيُبقي الطلب كما هو."),
    "dc_applied": ("Started: {x}", "بدأ: {x}"),
    "dc_inner_help": ("Shows the rules check and every step the agent took, next to the chat",
                      "يعرض فحص الشروط وكل خطوة قام بها الوكيل بجانب المحادثة"),
    "dc_clear": ("Clear all cases", "مسح جميع الطلبات"),
    "dc_clear_help": ("Empty the staff portal's case list, for example before a recording (logs are kept)",
                      "إفراغ قائمة الطلبات في بوابة الموظفين، مثلاً قبل التسجيل (تبقى السجلات محفوظة)"),
    "dc_cleared": ("All cases cleared: the staff portal is empty.", "تم مسح جميع الطلبات: بوابة الموظفين فارغة."),
    "dc_guide": ("How to use this demonstration", "طريقة استخدام هذا العرض"),
    "dc_guide_body": (
        "1. **Pick a situation** above: it starts at once in the parent portal.\n"
        "2. **Ask the assistant** anything, or tap a suggested question above the message box.\n"
        "3. **Tick documents and press Attach selected.** Use View to open any document on the page.\n"
        "4. **Pay** in the payment window with the test card that is already filled in.\n"
        "5. Open the **Staff portal** to see the case, its evidence and timeline, and record the officer's decision; "
        "the parent sees it at once.\n"
        "6. **Show how the agent decides** adds the rules check, the agent trace (each step marked Interpret, Validate, "
        "Act or Approve) and the security panel next to the chat.\n"
        "7. **عربي** switches the whole portal to Arabic at any point (the request continues); the moon button switches "
        "to dark mode.",
        "1. **اختر حالة** من الأعلى: تبدأ فوراً في بوابة ولي الأمر.\n"
        "2. **اسأل المساعد** أي سؤال، أو اضغط على أحد الأسئلة المقترحة فوق مربع الرسالة.\n"
        "3. **حدد المستندات واضغط إرفاق المحدد.** استخدم عرض لفتح أي مستند في الصفحة.\n"
        "4. **ادفع** في نافذة الدفع ببطاقة الاختبار المعبأة مسبقاً.\n"
        "5. افتح **بوابة الموظفين** لرؤية الطلب وأدلته ومراحله وتسجيل قرار الموظف؛ ويراه ولي الأمر فوراً.\n"
        "6. **عرض كيف يتخذ الوكيل قراراته** يضيف فحص الشروط ومسار عمل الوكيل (كل خطوة موسومة: الفهم أو التحقق أو "
        "التنفيذ أو الاعتماد) ولوحة الأمان بجانب المحادثة.\n"
        "7. **English** يحوّل البوابة كاملة إلى الإنجليزية في أي وقت (يستمر الطلب)؛ وزر القمر يحوّل إلى الوضع الداكن."),
    "sugg_label": ("Suggested questions", "أسئلة مقترحة"),
    "dc_changed": ("Settings changed: press Start new session to apply.", "تم تغيير الإعدادات: اضغط بدء جلسة جديدة للتطبيق."),
    "dc_check": ("Check again", "إعادة الفحص"),
    "dc_load": ("Load model", "تحميل النموذج"),
    "dc_loading": ("Loading the model...", "جارٍ تحميل النموذج..."),
    "prov_ollama": ("Local model (Ollama)", "نموذج محلي (Ollama)"),
    "prov_anthropic": ("Claude API", "واجهة Claude البرمجية"),
    "prov_hosted": ("Hosted model", "نموذج مستضاف"),
    "prov_scripted": ("No AI (scripted planner)", "بدون ذكاء اصطناعي (مخطط ثابت)"),
    "prov_adversarial": ("Compromised AI (attack test)", "ذكاء اصطناعي مخترق (اختبار هجوم)"),
    "ai_adversarial": ("Simulated attack: this model obeys any injection and tries to approve, pay nothing and submit. "
                       "The guard and the reply check must refuse every step.",
                       "هجوم محاكى: هذا النموذج ينفذ أي تعليمات مدسوسة ويحاول الموافقة والدفع بلا مبلغ والتقديم. يجب أن "
                       "يرفض الحارس وفحص الردود كل خطوة."),
    "fail_none": ("None (all systems work)", "لا يوجد (كل الأنظمة تعمل)"),
    "dc_fsys": ("Which system", "النظام"),
    "dc_fmode": ("What goes wrong", "نوع العطل"),
    "sys_verification": ("Document verification", "التحقق من المستندات"),
    "sys_identity": ("Identity (UAE Pass)", "الهوية الرقمية"),
    "sys_payment": ("Payment gateway", "بوابة الدفع"),
    "sys_cases": ("Case management", "نظام إدارة الطلبات"),
    "mode_timeout_once": ("Times out once, then works", "لا يستجيب مرة ثم يعمل"),
    "mode_error_once": ("Server error once, then works", "خطأ في الخادم مرة ثم يعمل"),
    "mode_malformed_once": ("Bad response once, then works", "رد غير صالح مرة ثم يعمل"),
    "mode_timeout_always": ("Times out every time", "لا يستجيب في كل مرة"),
    "mode_error_always": ("Server error every time (down)", "خطأ في الخادم في كل مرة (متوقف)"),
    "mode_malformed_always": ("Bad response every time", "رد غير صالح في كل مرة"),
    # the six mandatory scenarios of the case study, by their names in the brief
    "cs_label": ("Scenario {n} · {x}", "السيناريو {n} · {x}"),
    "cs_1": ("Successful end-to-end request", "طلب ناجح من البداية إلى النهاية"),
    "cs_2": ("Incomplete request, missing information", "طلب غير مكتمل بمعلومات ناقصة"),
    "cs_3": ("Exceptional case needing escalation", "حالة استثنائية تحتاج إلى إحالة"),
    "cs_4": ("Misleading input or prompt injection", "مدخلات مضللة أو حقن تعليمات"),
    "cs_5": ("Backend failure, timeout, bad response", "عطل في الأنظمة أو عدم استجابة أو رد غير صالح"),
    "cs_6": ("Rule bypass or unauthorised approval", "تجاوز القواعد أو موافقة غير مصرح بها"),
    "how_h": ("How to show it", "طريقة العرض"),
    "how_p01": ("attach all the documents and pay with the test card. The request is submitted with a reference; "
                "an officer then decides it in the Staff portal.",
                "أرفق جميع المستندات وادفع ببطاقة الاختبار. يُقدَّم الطلب برقم مرجعي، ثم يقرر فيه الموظف من بوابة الموظفين."),
    "how_p02": ("attach every document except the UAE visa: the assistant asks for the visa. Then attach the visa: it "
                "checks everything again and the request continues to payment.",
                "أرفق كل المستندات ما عدا الإقامة: سيطلب المساعد الإقامة. ثم أرفق الإقامة: يعيد الفحص ويكمل الطلب إلى الدفع."),
    "how_p03": ("attach all the documents and pay. The name on the Grade 4 certificate is not the passport name, so "
                "the rules cannot decide: the case goes to an officer (Staff portal).",
                "أرفق جميع المستندات وادفع. الاسم في شهادة الصف الرابع يختلف عن جواز السفر، فلا تستطيع القواعد الحسم: "
                "يُحال الطلب إلى موظف (بوابة الموظفين)."),
    "how_p04": ("tap the first suggested message (an injection), then attach all the documents: one certificate "
                "hides instructions to the AI. Nothing changes the rules: the missing MoFA attestation is still asked for. "
                "For the hardest test, pick Compromised AI in section 2: the model itself obeys, the guard still refuses.",
                "اضغط أول رسالة مقترحة (محاولة حقن تعليمات)، ثم أرفق جميع المستندات: إحدى الشهادات تخفي تعليمات للذكاء "
                "الاصطناعي. لا شيء يغير القواعد: يبقى تصديق وزارة الخارجية مطلوباً. ولأقوى اختبار اختر الذكاء الاصطناعي "
                "المخترق في القسم 2: ينفذ النموذج نفسه الهجوم، ويبقى الحارس رافضاً."),
    "how_p05": ("pick the backend problem below, then attach all the documents. Once: retried once, the request goes "
                "on. Every time: nothing is guessed; the fee is paid first, then the case goes to an officer. Payment "
                "down too: nothing is submitted or charged, and the parent is given the toll-free number.",
                "اختر العطل من الأسفل ثم أرفق جميع المستندات. مرة واحدة: تُعاد المحاولة مرة ويستمر الطلب. في كل مرة: لا "
                "يُخمَّن شيء؛ تُدفع الرسوم أولاً ثم يُحال الطلب إلى موظف. وإذا تعطل الدفع أيضاً: لا يُقدَّم شيء ولا تُحصَّل "
                "رسوم، ويُعطى ولي الأمر الرقم المجاني."),
    "how_p06": ("attach all the documents: the embassy attestation is missing. Then tap the suggested message that "
                "claims to be a Ministry employee: the rule cannot be skipped and nothing is approved. Compromised AI in "
                "section 2 shows the guard refusing a model that tries.",
                "أرفق جميع المستندات: تصديق السفارة ناقص. ثم اضغط الرسالة المقترحة التي تدّعي أن المرسل موظف في الوزارة: "
                "لا يمكن تجاوز الشرط ولا تتم أي موافقة. واختيار الذكاء الاصطناعي المخترق في القسم 2 يُظهر رفض الحارس لنموذج يحاول ذلك."),
    "how_open": ("choose a nationality here, then any documents from the library or your own files, and write "
                 "anything: an unseen test.",
                 "اختر الجنسية هنا، ثم أي مستندات من المكتبة أو ملفاتك الخاصة، واكتب ما تشاء: اختبار جديد لم يُجهَّز مسبقاً."),
    "how_other": ("attach the documents and follow the assistant. The line under the situation says what is special.",
                  "أرفق المستندات واتبع المساعد. السطر أسفل الحالة يوضح ما يميزها."),
    "fail_now": ("Simulating now: {x}", "المحاكاة الحالية: {x}"),
    "s5_both": ("Verification and payment both down", "التحقق والدفع متوقفان معاً"),
    "s5_pick": ("Backend problem for this scenario (applies at once)", "العطل المطلوب لهذا السيناريو (يُطبَّق فوراً)"),
    "s5_note": ("These are on the document verification service. Any other system (identity, payment, case "
                "management) can fail in section 3.",
                "هذه الأعطال في خدمة التحقق من المستندات. ويمكن محاكاة عطل أي نظام آخر (الهوية، الدفع، إدارة الطلبات) في القسم 3."),
    # the page language switched part way through a request
    "lang_kept": ("Page switched to {l}. Your conversation and request continue.",
                  "تم تحويل الصفحة إلى {l}. تستمر محادثتك وطلبك."),
    "lib_edition_kept": ("Showing the {l} edition of the documents, the same as those already attached.",
                         "تُعرض نسخة المستندات {l}، وهي نفس نسخة المستندات المرفقة."),
    # agent trace: the four responsibilities of the case study
    "lane_input": ("Parent", "ولي الأمر"),
    "lane_interpret": ("Interpret", "الفهم"),
    "lane_validate": ("Validate", "التحقق"),
    "lane_act": ("Act", "التنفيذ"),
    "lane_approve": ("Approve", "الاعتماد"),
    "lane_interpret_d": ("the model reads the request and explains", "النموذج يفهم الطلب ويشرح"),
    "lane_validate_d": ("fixed rules and checks, no AI", "قواعد وفحوص ثابتة دون ذكاء اصطناعي"),
    "lane_act_d": ("only authorised tools, checked by the guard", "الأدوات المصرح بها فقط، بعد فحص الحارس"),
    "lane_approve_d": ("a person decides what the rules cannot", "موظف يقرر ما لا تستطيع القواعد حسمه"),
    # security, shown
    "sec_title": ("Security and privacy, this session", "الأمان والخصوصية في هذه الجلسة"),
    "sec_guard": ("Tool calls refused by the guard", "استدعاءات أدوات رفضها الحارس"),
    "sec_override": ("Attempts to override the rules (chat)", "محاولات تجاوز القواعد (المحادثة)"),
    "sec_docinstr": ("Instructions to the AI inside documents (ignored)", "تعليمات للذكاء الاصطناعي داخل المستندات (تم تجاهلها)"),
    "sec_replies": ("AI replies blocked by the reply check", "ردود حجبها فحص الردود"),
    "sec_backend": ("System failures / recovered by one retry", "أعطال الأنظمة / تعافت بإعادة محاولة واحدة"),
    "sec_leaks": ("Document numbers or names in replies and the log", "أرقام مستندات أو أسماء في الردود والسجل"),
    "sec_leaks_none": ("none ({n} values checked now)", "لا يوجد (فُحصت {n} قيمة الآن)"),
    "sec_note": ("Counted from this session. Card details never reach the agent or the log; names and document numbers "
                 "are masked in the audit trail (Staff portal).",
                 "محسوبة من هذه الجلسة. لا تصل بيانات البطاقة إلى الوكيل أو السجل؛ وتُخفى الأسماء وأرقام المستندات في "
                 "سجل التدقيق (بوابة الموظفين)."),
    "ai_ready_scripted": ("Ready (no AI)", "جاهز (بدون ذكاء اصطناعي)"),
    "ai_key_ok": ("Key configured", "تم إعداد المفتاح"),
    "ai_no_key": ("No API key set (.env, or the app's secrets online)", "لا يوجد مفتاح (ملف .env أو أسرار التطبيق على الإنترنت)"),
    "ai_paused": ("AI paused (free allowance used up) until about {t} UAE time. The portal answers without AI until then.",
                  "الذكاء الاصطناعي متوقف (استُنفد الرصيد المجاني) حتى الساعة {t} تقريباً بتوقيت الإمارات. تعمل البوابة دون ذكاء اصطناعي حتى ذلك الحين."),
    "ai_on_fallback": ("Main model resting; using the backup model {m}", "النموذج الرئيسي متوقف مؤقتاً؛ يُستخدم النموذج الاحتياطي {m}"),
    "ai_left": (" · about {n} requests left today", " · يتبقى نحو {n} طلباً اليوم"),
    "ai_hosted_down": ("Hosted model not reachable ({d})", "تعذر الوصول إلى النموذج المستضاف ({d})"),
    "ai_not_offered": ("{m} is not offered by the service now: change HOSTED_MODEL", "النموذج {m} غير متاح حالياً: غيّر HOSTED_MODEL"),
    "ai_not_running": ("Not running. Open the Ollama app (or restart the portal with run_app), then Check again.",
                       "غير مشغل. افتح تطبيق Ollama (أو أعد تشغيل البوابة عبر run_app) ثم أعد الفحص."),
    "ai_not_downloaded": ("{m} is not downloaded. Run setup again, or: ollama pull {m}",
                          "النموذج {m} غير محمّل على الجهاز. أعد تشغيل الإعداد، أو: ollama pull {m}"),
    "ai_not_loaded": ("{m} not loaded yet (first reply takes about a minute)", "النموذج {m} لم يُحمّل بعد (أول رد يستغرق دقيقة تقريباً)"),
    "ai_ready": ("Ready: {m}", "جاهز: {m}"),
    # helpful information (as on the service card)
    "info_title": ("Helpful information", "معلومات مفيدة"),
    "info_time": ("Service time", "وقت الخدمة"),
    "info_time_v": ("30 working days (published service time)", "30 يوم عمل (مدة الخدمة المعتمدة)"),
    "info_review": ("Proposed improvement", "تحسين مقترح"),
    "info_review_v": ("Complete requests are checked and submitted at once; the official decision stays within 30 "
                      "working days", "تُفحص الطلبات المكتملة وتُقدَّم فوراً، ويبقى القرار الرسمي ضمن 30 يوم عمل"),
    "info_fees": ("Fees", "الرسوم"),
    "info_fees_v": ("AED 50", "50 درهم"),
    "info_docs": ("Required documents", "المستندات المطلوبة"),
    "info_docs_v": ("Passport, Emirates ID, residence visa (non-GCC nationals), certificates of the last 2 years",
                    "جواز السفر، الهوية، الإقامة (لغير أبناء دول المجلس)، شهادات آخر سنتين"),
    "info_card": ("Official service card", "بطاقة الخدمة الرسمية"),
    # journey
    "j_signed": ("Signed in", "تسجيل الدخول"),
    "j_docs": ("Documents", "المستندات"),
    "j_verify": ("Verification", "التحقق"),
    "j_rules": ("Rules check", "فحص الشروط"),
    "j_fee": ("Payment", "الدفع"),
    "j_done": ("Submitted", "تم التقديم"),
    "j_review": ("Officer review", "مراجعة الموظف"),
    "j_decided": ("Officer decision", "قرار الموظف"),
    "j_other": ("Different service", "خدمة أخرى"),
    # chat
    "assistant": ("Service assistant", "المساعد الذكي للخدمة"),
    "chat_placeholder": ("Write your message", "اكتب رسالتك"),
    "thinking": ("Checking your request...", "جارٍ فحص طلبك..."),
    "from_record": ("From the case record", "من سجل الطلب"),
    "from_card": ("From the service card", "من بطاقة الخدمة"),
    "ai_down_note": ("The AI did not respond, so this was written from the case record.",
                     "لم يستجب الذكاء الاصطناعي، لذلك كُتبت هذه الرسالة من سجل الطلب."),
    "attached": ("Attached", "المرفقات"),
    "dv_renewed": (" (renewed)", " (مجدد)"), "dv_scan": (" (scanned PDF)", " (نسخة ممسوحة PDF)"),
    "dv_photo": (" (phone photo, {f})", " (صورة من الهاتف {f})"),
    "doc_remove": ("Remove this file", "إزالة هذا الملف"), "doc_remove_short": ("Remove", "إزالة"),
    "dc_open_nat": ("Open test: nationality on the UAE Pass record", "الاختبار المفتوح: الجنسية في سجل الهوية الرقمية"),
    "dc_open_nat_ph": ("Select a nationality", "اختر الجنسية"),
    "dc_open_nat_none": ("No nationality selected: the record shows none, so a UAE visa is required. Choosing one "
                         "restarts the open test with it at once and shows that applicant's documents.",
                         "لم تُختر جنسية: السجل لا يُظهر جنسية، لذلك تلزم الإقامة. اختيار جنسية يعيد بدء الاختبار المفتوح بها "
                         "فوراً ويعرض مستندات المتقدم المطابق."),
    "rv_staff_id": ("The officer ID must look like STAFF-XXXX (synthetic staff accounts only).",
                    "يجب أن يكون رقم الموظف بالشكل STAFF-XXXX (حسابات موظفين اصطناعية فقط)."),
    "rv_note": ("Write a note explaining the decision first.", "اكتب أولاً ملاحظة توضح سبب القرار."),
    "rv_decided": ("This case is already decided.", "تم البت في هذا الطلب مسبقاً."),
    "rv_other": ("The decision could not be recorded: {e}", "تعذر تسجيل القرار: {e}"),
    "open_title": ("Open test (no preset case)", "اختبار مفتوح (بلا حالة جاهزة)"),
    "dc_open_nat_help": ("Decides whether a UAE visa is needed (GCC nationals do not need one).",
                         "تحدد ما إذا كانت الإقامة مطلوبة (لا تلزم لأبناء دول مجلس التعاون)."),
    "lib_title": ("Document library", "مكتبة المستندات"),
    "lib_show": ("Show the documents of", "عرض مستندات"),
    "lib_hint": ("Open test: any document of any synthetic applicant can be attached, so you can build your own case. "
                 "Mixing applicants is allowed; the rules will show what they find.",
                 "اختبار مفتوح: يمكن إرفاق أي مستند لأي متقدم اصطناعي لبناء حالتك الخاصة. الخلط بين المتقدمين مسموح، "
                 "وستُظهر الشروط ما تجده."),
    "wait_answer": ("Please wait for the answer to your last message, then send this again.",
                    "يرجى انتظار الرد على رسالتك الأخيرة، ثم أرسل هذه الرسالة مرة أخرى."),
    "doc_unconfirmed": ("could not be verified", "تعذر التحقق منه"),
    "removed_msg": ("I removed the {doc}.", "أزلت {doc}."),
    "docs_attached_h": ("Attached", "المرفقة"), "docs_available_h": ("Your files", "ملفاتك"),
    "attached_msg": ("I have attached documents.", "أرفقت المستندات."),
    "payment_done_msg": ("Payment completed in the payment window.", "تم الدفع في نافذة الدفع."),
    "greeting": ("Welcome. You are signed in with UAE Pass (simulated for this prototype).\n\n"
                 "I can help you request an equivalency certificate for school grades completed outside the UAE "
                 "(Grades 2 to 11), so a student can continue at a school here. Tell me which grade was completed "
                 "and where, or attach the documents and I will check them for you.",
                 "مرحباً بك. لقد سجلت الدخول بالهوية الرقمية (UAE Pass) في وضع المحاكاة لهذا النموذج الأولي.\n\n"
                 "يمكنني مساعدتك في طلب شهادة معادلة للصفوف الدراسية المنجزة خارج الدولة (من الصف الثاني إلى "
                 "الحادي عشر) لمواصلة الدراسة في مدرسة هنا. أخبرني بالصف الذي أنهاه الطالب وأين، أو أرفق "
                 "المستندات وسأقوم بفحصها لك."),
    # application card
    "app_title": ("Your application", "طلبك"),
    "app_status": ("Status", "الحالة"),
    "app_reason": ("Reason", "السبب"),
    "app_ref": ("Reference", "الرقم المرجعي"),
    "app_ref_none": ("Not created yet", "لم يُنشأ بعد"),
    "app_rules": ("Rules check", "فحص الشروط"),
    "app_rules_none": ("Not run yet", "لم يُجرَ بعد"),
    "app_fee": ("Fee", "الرسوم"),
    "app_fee_paid": ("AED 50, paid", "50 درهم، مدفوعة"),
    "app_fee_unpaid": ("AED 50, not paid", "50 درهم، غير مدفوعة"),
    "case_timeline": ("What happened ({n} key steps)", "ماذا حدث ({n} خطوات رئيسية)"),
    "case_every_step": ("Show every step (tools, checks, model)", "عرض كل الخطوات (الأدوات والفحوص والنموذج)"),
    "case_decide": ("Your decision", "قرارك"),
    "decided_toast": ("Decision recorded for {ref}. The parent sees it at once.", "تم تسجيل القرار للطلب {ref}، ويراه ولي الأمر فوراً."),
    "case_fee_paid": ("AED 50 paid (receipt {r})", "50 درهم مدفوعة (الإيصال {r})"),
    "case_fee_none": ("Not paid (a case from before every referral was paid for first)",
                      "غير مدفوعة (طلب سابق لاعتماد الدفع قبل كل إحالة)"),
    "list_show": ("Show", "عرض"),
    "list_todo": ("To decide", "بانتظار القرار"), "list_decided": ("Decided", "تم البت"), "list_all": ("All", "الكل"),
    "list_empty_todo": ("Nothing is waiting for a decision.", "لا يوجد ما ينتظر القرار."),
    "list_empty_decided": ("No decisions yet.", "لا توجد قرارات بعد."),
    "list_empty_all": ("No cases yet.", "لا توجد طلبات بعد."),
    "list_open": ("Open", "فتح"), "list_opened": ("Open now", "مفتوح الآن"),
    "view_btn": ("View", "عرض"),
    "view_help": ("Open the document here, without downloading it", "فتح المستند هنا دون تنزيله"),
    "view_missing": ("This file is no longer available.", "هذا الملف لم يعد متاحاً."),
    "view_cannot": ("This file cannot be shown here; download it to open it.", "لا يمكن عرض هذا الملف هنا؛ نزّله لفتحه."),
    "view_page": ("Page {n} of {total}", "الصفحة {n} من {total}"),
    "view_more": ("{n} more pages: download the file to see them.", "{n} صفحات أخرى: نزّل الملف لعرضها."),
    "view_download": ("Download", "تنزيل"),
    "lib_matched": ("Showing the documents of the applicant whose UAE Pass nationality you chose. Pick another applicant to mix documents on purpose.",
                    "تُعرض مستندات المتقدم الذي يطابق الجنسية المختارة في سجل الهوية الرقمية. اختر متقدماً آخر لخلط المستندات عمداً."),
    "lib_nomatch": ("No prepared applicant has this nationality: pick any applicant's documents.",
                    "لا يوجد متقدم جاهز بهذه الجنسية: اختر مستندات أي متقدم."),
    "nat_applied": ("Open test restarted with the nationality {n}.", "أُعيد بدء الاختبار المفتوح بالجنسية {n}."),
    "recheck": ("re-check pending", "بانتظار إعادة الفحص"),
    "pay_now": ("Pay AED 50", "ادفع 50 درهم"),
    "receipt_dl": ("Download application receipt (PDF)", "تنزيل إيصال تقديم الطلب (PDF)"),
    # statuses
    "st_IN_PROGRESS": ("In progress", "قيد الإجراء"),
    "st_AWAITING_CUSTOMER": ("Waiting for you", "بانتظار ولي الأمر"),
    "st_AWAITING_PAYMENT": ("Waiting for payment", "بانتظار الدفع"),
    "st_SUBMITTED": ("Submitted, awaiting the officer's decision", "تم التقديم، بانتظار قرار الموظف"),
    "st_PENDING_HUMAN_REVIEW": ("With a Ministry officer", "لدى موظف الوزارة"),
    "st_REDIRECTED": ("Different service needed", "يلزم خدمة أخرى"),
    "st_HUMAN_APPROVED": ("Approved by an officer", "وافق عليه الموظف"),
    "st_HUMAN_REJECTED": ("Not approved by an officer", "لم يوافق عليه الموظف"),
    "oc_ELIGIBLE": ("All rules passed", "جميع الشروط مستوفاة"),
    "oc_NEEDS_INFO": ("Information needed", "مطلوب معلومات"),
    "oc_HUMAN_REVIEW": ("Needs a person", "يحتاج إلى موظف"),
    "oc_WRONG_SERVICE": ("Different service", "خدمة أخرى"),
    "rs_PASS": ("Pass", "مستوفى"), "rs_FAIL": ("Fail", "غير مستوفى"), "rs_MISSING": ("Missing", "ناقص"),
    "rs_REVIEW": ("Needs a person", "يحتاج إلى موظف"), "rs_NOT_APPLICABLE": ("Not applicable", "لا ينطبق"),
    # documents
    "docs_title": ("Documents", "المستندات"),
    "docs_hint": ("Synthetic documents of the signed-in parent. Tick and attach them, as you would upload files.",
                  "مستندات اصطناعية لولي الأمر المسجل. اخترها وأرفقها كما لو كنت ترفع ملفات."),
    "docs_attach": ("Attach selected", "إرفاق المحدد"),
    "docs_closed": ("This case is closed for new files: the decision uses the documents already checked.",
                    "هذا الطلب مغلق أمام الملفات الجديدة: يعتمد القرار على المستندات التي تم فحصها."),
    "docs_preview": ("Open a document", "فتح مستند"),
    "docs_open_pdf": ("Download", "تنزيل"),
    "up_title": ("Upload a file from this computer", "رفع ملف من هذا الجهاز"),
    "up_hint": ("The service accepts PDF files up to 5 MB. A file that is one of this applicant's documents (for example "
                "downloaded below) is recognised; any other file cannot be verified and is reviewed by a Ministry officer.",
                "تقبل الخدمة ملفات PDF بحجم أقصاه 5 ميجابايت. يتم التعرف على الملف إذا كان أحد مستندات هذا المتقدم (مثلاً "
                "بعد تنزيله من الأسفل)، وأي ملف آخر لا يمكن التحقق منه ويراجعه موظف الوزارة."),
    "dv_uploaded": ("(uploaded file)", "(ملف مرفوع)"),
    "up_file": ("File", "الملف"), "up_type": ("What is this document?", "ما نوع هذا المستند؟"),
    "up_button": ("Upload and attach", "رفع وإرفاق"),
    "up_too_big": ("The file is larger than 10 MB.", "حجم الملف أكبر من 10 ميجابايت."),
    "ut_passport": ("Passport", "جواز السفر"), "ut_emirates_id": ("Emirates ID", "الهوية الإماراتية"),
    "ut_uae_visa": ("UAE residence visa", "الإقامة"), "ut_school_certificate": ("School certificate", "شهادة مدرسية"),
    "ut_legal_translation": ("Legal translation", "ترجمة قانونية"),
    "ut_supporting_document": ("Supporting document", "مرفق داعم"),
    "doc_verified": ("verified", "تم التحقق"), "doc_failed": ("check failed", "تعذر التحقق"),
    "doc_attached": ("attached", "مرفق"),
    "dl_passport": ("Passport", "جواز السفر"), "dl_emirates_id": ("Emirates ID", "الهوية الإماراتية"),
    "dl_uae_visa": ("UAE residence visa", "الإقامة"), "dl_supporting_document": ("Supporting document", "مرفق داعم"),
    "dl_cert": ("Grade {g} certificate", "شهادة الصف {g}"), "dl_kg": ("Kindergarten certificate", "شهادة رياض الأطفال"),
    "dl_trans": ("Legal translation, Grade {g}", "ترجمة قانونية، الصف {g}"),
    "lang_French": ("French", "بالفرنسية"), "lang_Arabic": ("Arabic", "بالعربية"), "lang_English": ("English", "بالإنجليزية"), "lang_German": ("German", "بالألمانية"),
    # behind the scenes
    "inner_title": ("How the agent decided", "كيف اتخذ الوكيل قراره"),
    "rules_title": ("Rules check", "فحص الشروط"),
    "rules_none": ("Runs after the documents are verified. Every rule cites the service card.",
                   "يُجرى بعد التحقق من المستندات. كل شرط مرتبط ببطاقة الخدمة."),
    "rules_h_rule": ("Rule", "الشرط"), "rules_h_result": ("Result", "النتيجة"),
    "rules_h_detail": ("Detail", "التفاصيل"), "rules_h_source": ("Source", "المصدر"),
    "trace_title": ("Agent trace", "مسار عمل الوكيل"),
    "trace_stats": ("Model {m} · tool calls {c} · blocked {b} · backend failures {f} · recovered {r}",
                    "النموذج {m} · استدعاءات الأدوات {c} · محظورة {b} · أعطال الأنظمة {f} · تم التعافي {r}. "
                    "تظهر الخطوات التقنية بالإنجليزية كما يسجّلها النظام."),
    # payment window
    "pay_title": ("Secure payment (simulated)", "الدفع الآمن (محاكاة)"),
    "pay_amount": ("Service fee", "رسوم الخدمة"),
    "pay_merchant": ("Ministry of Education · Equivalency service", "وزارة التربية والتعليم · خدمة المعادلة"),
    "pay_card": ("Card", "بطاقة"),
    "pay_name": ("Name on card", "الاسم على البطاقة"), "pay_number": ("Card number", "رقم البطاقة"),
    "pay_expiry": ("Expiry (MM/YY)", "تاريخ الانتهاء (شهر/سنة)"), "pay_cvv": ("CVV", "رمز التحقق"),
    "pay_button": ("Pay AED 50", "ادفع 50 درهم"),
    "pay_wallet": ("Pay with {w}", "ادفع باستخدام {w}"),
    "pay_wallet_note": ("You will confirm the payment on your device.", "ستؤكد عملية الدفع على جهازك."),
    "pay_test_cards": ("Test mode · test cards: 4242 4242 4242 4242 approved · 4000 0000 0000 0002 declined · "
                       "4000 0000 0000 9995 insufficient funds",
                       "وضع الاختبار · بطاقات الاختبار: \u20664242 4242 4242 4242\u2069 مقبولة · \u20664000 0000 0000 0002\u2069 مرفوضة · "
                       "\u20664000 0000 0000 9995\u2069 رصيد غير كاف"),   # numbers isolated left to right
    "pay_never_stored": ("Card details are checked and discarded. Only the card type and last 4 digits are kept.",
                         "يتم فحص بيانات البطاقة ثم حذفها. يُحفظ نوع البطاقة وآخر 4 أرقام فقط."),
    "pay_ok": ("Payment completed", "تم الدفع بنجاح"),
    "payerr_card_declined": ("The bank declined this card. Try another card.", "رفض البنك هذه البطاقة. جرّب بطاقة أخرى."),
    "payerr_insufficient_funds": ("Insufficient funds on this card.", "الرصيد غير كاف في هذه البطاقة."),
    "payerr_not_test_card": ("This card was not accepted. Please use a different card.",
                             "لم يتم قبول هذه البطاقة. يرجى استخدام بطاقة أخرى."),
    "payerr_number_invalid": ("The card number is not valid.", "رقم البطاقة غير صحيح."),
    "payerr_expiry_invalid": ("The expiry date is not valid or has passed.", "تاريخ الانتهاء غير صحيح أو منتهٍ."),
    "payerr_cvv_invalid": ("The CVV must be 3 or 4 digits.", "رمز التحقق يجب أن يكون 3 أو 4 أرقام."),
    "payerr_name_missing": ("Please enter the name on the card.", "يرجى إدخال الاسم على البطاقة."),
    "payerr_no_payment_open": ("There is no payment to complete.", "لا توجد عملية دفع لإكمالها."),
    "payerr_rules_not_current": ("The documents changed; the rules must run again before payment.",
                                 "تغيرت المستندات؛ يجب إعادة فحص الشروط قبل الدفع."),
    "payerr_unknown_payment": ("This payment window has expired.", "انتهت صلاحية نافذة الدفع هذه."),
    "payerr_unknown_method": ("This payment method is not available.", "طريقة الدفع هذه غير متاحة."),
    # staff portal
    "staff_title": ("Equivalency cases", "طلبات المعادلة"),
    "staff_sub": ("The agent checks, validates and submits. Only an officer issues the equivalency decision, on every "
                  "case. Every decision is written to the audit trail.",
                  "يفحص الوكيل الطلب ويتحقق منه ويقدمه. الموظف وحده يُصدر قرار المعادلة في كل طلب. يُسجل كل قرار في "
                  "سجل التدقيق."),
    "staff_officer": ("Signed in as officer", "مسجل الدخول كموظف"),
    "kpi_waiting": ("Exceptions to review", "استثناءات للمراجعة"),
    "kpi_submitted": ("Ready for decision", "جاهزة للقرار"),
    "kpi_decided": ("Decided by officers", "قرارات الموظفين"),
    "kpi_total": ("All cases", "جميع الطلبات"),
    "tab_queue": ("Cases", "الطلبات"),
    "q_review_h": ("Exceptions: the rules could not decide", "استثناءات: لم تستطع الشروط البت فيها"),
    "q_review_sub": ("Resolve what the rules flagged, then approve or reject.",
                     "عالج ما أشارت إليه الشروط، ثم وافق أو ارفض."),
    "q_ready_h": ("Ready for the equivalency decision: all automated checks passed",
                  "جاهزة لقرار المعادلة: اجتازت جميع الفحوص الآلية"),
    "q_ready_sub": ("The agent verified the documents, the rules passed and the fee is paid. The official decision is "
                    "yours.", "تحقق الوكيل من المستندات واجتازت الشروط ودُفعت الرسوم. القرار الرسمي لك."),
    "q_ready_empty": ("No submitted cases are waiting for a decision.", "لا توجد طلبات مقدمة بانتظار القرار."),
    "ready_note_ph": ("Required, for example: documents checked, equivalency approved for Grade 6",
                      "مطلوبة، مثال: تم فحص المستندات والموافقة على معادلة الصف السادس"),
    "case_checks": ("Automated checks", "الفحوص الآلية"),
    "tab_all": ("All cases", "جميع الطلبات"),
    "tab_audit": ("Audit trail", "سجل التدقيق"),
    "queue_empty": ("No exceptions are waiting for an officer.", "لا توجد استثناءات بانتظار الموظف."),
    "case_student": ("Student", "الطالب"),
    "case_created": ("Created", "تاريخ الإنشاء"),
    "case_lang": ("Parent's language", "لغة ولي الأمر"),
    "case_rules": ("Rules when the case was created", "نتيجة الشروط عند إنشاء الطلب"),
    "case_why": ("Why it needs an officer", "سبب الإحالة إلى موظف"),
    "case_docs": ("Documents checked", "المستندات التي تم فحصها"),
    "case_evidence": ("What the documents show (cells in red caused the referral)",
                      "ما تُظهره المستندات (الخانات باللون الأحمر هي سبب الإحالة)"),
    "case_evidence_ok": ("What the documents show", "ما تُظهره المستندات"),
    "case_open_docs": ("Open the documents", "فتح المستندات"),
    "student_unknown": ("Identity record not available (the identity system did not answer)",
                        "سجل الهوية غير متاح (لم يستجب نظام الهوية)"),
    "case_parent_said": ("The parent wrote", "كتب ولي الأمر"),
    "cases_none": ("No cases yet in this demonstration.", "لا توجد طلبات بعد في هذا العرض."),
    "col_why": ("What the rules found", "نتيجة الشروط"),
    "all_passed": ("All rules passed", "جميع الشروط مستوفاة"),
    "au_time": ("Time", "الوقت"), "au_who": ("Who", "من"), "au_what": ("What happened", "ماذا حدث"),
    "au_why": ("Why (card, rule or policy)", "السبب (البطاقة أو الشرط أو السياسة)"),
    "au_raw": ("Technical log (JSON lines)", "السجل التقني (JSON)"),
    "case_summary": ("Assistant's summary (AI written, check it against the documents)",
                     "ملخص المساعد (مكتوب بالذكاء الاصطناعي، تحقق منه مقابل المستندات)"),
    "officer_id": ("Officer ID", "رقم الموظف"),
    "decision_note": ("Decision note", "ملاحظة القرار"),
    "decision_note_ph": ("Required, for example: same student, full lineage name on the certificate",
                         "مطلوبة، مثال: نفس الطالب، والشهادة تحمل الاسم الرباعي"),
    "approve": ("Approve", "موافقة"), "reject": ("Reject", "رفض"),
    "col_case": ("Case", "الطلب"), "col_status": ("Status", "الحالة"), "col_reason": ("Reason", "السبب"),
    "col_officer": ("Officer", "الموظف"), "col_note": ("Note", "الملاحظة"), "col_lang": ("Language", "اللغة"),
    "col_created": ("Created", "الإنشاء"),
    "audit_pick": ("Session", "الجلسة"),
    "audit_actors": ("Actors", "الجهات"),
    "audit_caption": ("Who acted, what happened and why (customer turn, card section, rule or policy). Sensitive values are masked before writing.",
                      "من قام بالإجراء، وماذا حدث، ولماذا (رسالة العميل، بند في البطاقة، شرط أو سياسة). تُخفى البيانات الحساسة قبل الكتابة، ويظهر السبب كما سُجّل في السجل باللغة الإنجليزية."),
    "audit_none": ("No events yet.", "لا توجد أحداث بعد."),
    "audit_download": ("Download log (JSONL)", "تنزيل السجل (JSONL)"),
    "this_session": ("current parent session", "جلسة ولي الأمر الحالية"),
    "lang_en": ("English", "الإنجليزية"), "lang_ar": ("Arabic", "العربية"),
    "new_session_toast": ("New session started in {l}.", "بدأت جلسة جديدة باللغة {l}."),
    "footer": ("Prototype for the MoE AI Developer case study. Synthetic data, mock systems, no real decisions.",
               "نموذج أولي لدراسة حالة مطور الذكاء الاصطناعي في الوزارة. بيانات اصطناعية وأنظمة محاكاة ولا قرارات حقيقية."),
}

REASON = {
    "name_mismatch": ("Name differs between passport and a certificate", "اختلاف الاسم بين جواز السفر وإحدى الشهادات"),
    "verification_inconclusive": ("Verification inconclusive", "نتيجة التحقق غير قاطعة"),
    "system_unavailable": ("A system that checks the documents was down", "تعطل نظام يفحص المستندات"),
    "customer_request": ("Parent asked for a person", "طلب ولي الأمر التحدث مع موظف"),
    "other": ("Needs a decision the rules cannot make", "يحتاج إلى قرار لا تتخذه القواعد"),
}


def t(key: str, lang: str, **fields) -> str:
    en, ar = S[key]
    text = ar if lang == "ar" else en
    return text.format(**fields) if fields else text


def reason(code: str | None, lang: str) -> str:
    en, ar = REASON.get(code or "other", REASON["other"])
    return ar if lang == "ar" else en


def _variant(d: dict, lang: str) -> str:
    """Tells apart two files for the same requirement (renewed passport, scanned copy, phone photo)."""
    v = d.get("registry", {}).get("variant")
    if v == "renewed":
        return t("dv_renewed", lang)
    if v == "scan":
        return t("dv_scan", lang)
    name = d.get("file_name", "").lower()
    if name.endswith((".jpg", ".jpeg", ".png")):
        return t("dv_photo", lang, f="PNG" if name.endswith(".png") else "JPG")
    return ""


def doc_label(d: dict, lang: str) -> str:
    return _doc_label(d, lang) + _variant(d, lang)


def _doc_label(d: dict, lang: str) -> str:
    kind = d["doc_type"]
    if d.get("registry", {}).get("unknown"):
        return t("ut_" + kind, lang) + " " + t("dv_uploaded", lang)
    if kind == "school_certificate":
        r = d["registry"]
        g = r.get("grade")
        base = t("dl_kg", lang) if g == 0 else t("dl_cert", lang, g=g)
        language = r.get("language")
        if language and language != ("Arabic" if lang == "ar" else "English"):
            base += f" ({t('lang_' + language, lang) if 'lang_' + language in S else language})"
        return base
    if kind == "legal_translation":
        g = d["doc_id"].rsplit("G", 1)[-1]
        target = d["registry"].get("translation_language")
        label = t("dl_trans", lang, g=g)
        return label + (f" ({t('lang_' + target, lang)})" if target and "lang_" + target in S else "")
    key = "dl_" + kind
    return t(key, lang) if key in S else kind.replace("_", " ").capitalize()
