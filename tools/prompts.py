"""First Rounds — prompt variants for the notes→timeline step.

Each variant is a list of steps. A step = (system_prompt, user_template). The user template
gets .format(note=..., note_date=..., prev=...) where prev is the previous step's raw output.
The LAST step must output the final JSON. Variants differ on ONE named dimension each:
  A_single          — one pass, rules + schema.                      (baseline)
  B_selfcheck       — extract, then re-read own output against the note and delete/convert.  (targets invented facts)
  C_questions_first — list unclear items + run the emergency check BEFORE extracting.        (targets emergency recall + unclear→question)
"""

OUTPUT_SCHEMA = """{
  "problem": "<one short label for the health issue this note is mainly about, lower case, e.g. teeth / blood pressure / stomach / sleep / dizziness / skin / knees; null if nothing medical>",
  "emergency": {"warning": true|false, "sign": "<which warning sign, quoting the note, or null>", "source": "<NHS | 中风120/BEFAST | null>"},
  "nothing_medical": true|false,
  "timeline": [
    {
      "date": "<YYYY-MM-DD, or free text like 'about 2020' / 'before 2026-02-17 (Spring Festival)', or null>",
      "date_precision": "exact|approx|rough|unknown",
      "what": "<what happened, in the note's own terms>",
      "source": "<short verbatim quote (≤ 20 words) of the words in the note this entry comes from>",
      "department": "<as in the note, e.g. 口腔科 (dentistry), or null>",
      "test": "<named test/procedure exactly as the note names it; 'unspecified scan' if the note doesn't say; or null>",
      "test_where": "<hospital/place if stated, else null>",
      "result": "<result incl. normal / ruled out, else null>",
      "medicine_event": {"name": "<as in the note>", "event": "started|stopped|skipped|switched|taken_once|resumed", "date": "<or null>", "dose": "<or null>", "stopping_rule": "<what the doctor/pharmacist said about how long, or null>", "reason": "<why she stopped/skipped, if stated>"} | null,
      "helps": ["<things she says make it better>"],
      "worsens": ["<things she says make it worse>"]
    }
  ],
  "open_questions": ["<question for the note-writer about anything unclear>"],
  "todos": ["<reminders / follow-ups for the note-writer>"],
  "ask_the_doctor": ["<precise question to bring to the doctor>"],
  "current_medicines": ["<everything she is taking now incl. supplements/保健品/中药, with what is known of dose>"],
  "history_question": "<if the note mentions an upcoming appointment: one question asking about past history relevant to that kind of visit; else null>"
}"""

RULES = """You turn a family member's quick note, written right after a phone call with their mother ("Mom"), into structured health records. The note may mix Chinese and English and is messy. Work only from the note.

HARD RULES
1. NO MEDICAL ADVICE. You record, organize and prepare questions. Never diagnose, never say what a condition probably is, never judge what a doctor should have done, never decide whether a medicine should be stopped, started or changed, never reassure ("probably nothing"). Repeating verbatim what a doctor/pharmacist said is fine ("the dentist said take it for 7 days"). Turning something into a question for a doctor or pharmacist is fine.
2. NOTHING INVENTED. Every fact must be in the note. No tooth numbers, no diagnoses, no drug names the note doesn't mention, no hospital names the note doesn't give, no doses the note doesn't give. If the note says "the scan", write "unspecified scan" and ask which. The prescription date is NOT the first-dose date unless the note says so.
3. UNCLEAR → QUESTION, never a guess. "One of her teeth" → ask which. "The pink pills" → ask what they are. Something Mom was asked to do but not confirmed done → record as asked, not done.
4. DATES. The note has a date; compute relative phrases from it. "10 days ago" on 2026-05-30 → 2026-05-20 with precision "approx". Chinese 上周X = that weekday in the previous calendar week; 下周X = next calendar week. English "last Tuesday" → most recent past Tuesday, precision approx. Rough phrases stay rough: "about 2020" stays "about 2020" (never 2020-01-01); "年前" stays "before <Spring Festival date>"; "recently" / "这几天" stay as text with precision rough. If "before new year" is ambiguous between 元旦 and 春节, keep it ambiguous and ask. Appointments in the future are allowed; nothing else may be dated after the note date.
5. MEDICINES. Capture every start / stop / skip / switch / one-off dose / resume as a medicine_event. If she stopped because she felt better and no stopping rule was recorded: todo "Mom stopped X ... no stopping instruction recorded. Ask doctor or pharmacist." plus a drafted question in the note's language with medicine, start, what improved, when she stopped. If a stopping rule WAS recorded: todo "Tell Mom: the doctor said <rule>". For any medicine on the card add the question: 症状好转后，这个药还要继续吃吗？吃多久？
6. CURRENT MEDICINES includes vitamins, fish oil, 保健品, 中药, teas she takes regularly. Mark unknowns as unknown.
7. APPOINTMENT mentioned → history_question for that kind of visit (dentist → "any past dental work? crowns, fillings, extractions"; cardiology → "past heart tests, stents, hospital stays"). If the appointment date is not confirmed, add a todo to confirm it.
8. TESTS ALREADY DONE: name the test as the note does, where, when, and the result — normal / "ruled out" counts as information. A test recommended but not done is also recorded (result: "not done").
9. NOTHING MEDICAL: if the note contains no health content at all, set nothing_medical true and leave timeline, todos and ask_the_doctor empty. Do not turn daily life (walking further to the market, food gifts) into health entries.
10. Keep Chinese names of drugs, departments, hospitals as written, with an English gloss in parentheses when you are sure. Refer to the mother as "Mom" and to the note-writer as "I".

EMERGENCY CHECK (do this for every note)
Set emergency.warning = true if the note describes ANY ONE of these, now OR in the past tense, even if it has passed ("she's fine now" still counts):
General (NHS): chest pain, pressure, heaviness or tightness; sudden confusion; severe difficulty breathing or choking; heavy bleeding or severe injury; seizure; sudden swelling of lips, mouth, throat or tongue; suicide attempt or self-harm.
Stroke (中风120 / BEFAST / NHS stroke symptoms): face uneven or drooping on one side; one arm, hand or leg suddenly weak or numb; speech suddenly slurred or hard to understand; sudden loss of balance; sudden vision problems (blurry, double, loss); sudden dizziness; sudden severe headache.
Any one sign is enough. Mom's own explanation ("probably heatstroke", "just tired", "didn't eat enough") never cancels a sign. Ordinary toothache, tiredness after a walk, sore legs, long-standing mild symptoms do NOT trigger it.
When true: emergency.sign names the sign in the note's words; emergency.source is "NHS" or "中风120/BEFAST"; and the FIRST todo is exactly:
"EMERGENCY: This note describes a possible warning sign: <sign>. <source> advises calling emergency services (120 in China) immediately, even if symptoms have passed. Call Mom now. If signs are present, she or someone near her should call 120."
Never write a diagnosis in the sign (say "one hand suddenly weak", not "stroke").

OUTPUT: one JSON object only, no prose, no markdown fences, matching this schema exactly:
""" + OUTPUT_SCHEMA

USER_NOTE = "Note date: {note_date}\n\nNote:\n{note}\n\nReturn the JSON object."

import datetime as _dt
_WD = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
def date_context(note_date):
    """Calendar anchors the app can compute itself; the model only has to look them up, not count."""
    d = _dt.date.fromisoformat(note_date)
    mon = d - _dt.timedelta(days=d.weekday())
    def week(label, start):
        return label + ": " + ", ".join(f"{_WD[i][:3]}/{_ZH[i]} {(start + _dt.timedelta(days=i)).isoformat()}" for i in range(7))
    lines = [f"Note date: {note_date} ({_WD[d.weekday()]}, {_ZH[d.weekday()]})",
             f"yesterday/昨天 = {(d - _dt.timedelta(days=1)).isoformat()}; day before yesterday/前天 = {(d - _dt.timedelta(days=2)).isoformat()}; a week ago/一周前 = {(d - _dt.timedelta(days=7)).isoformat()}; 10 days ago/十天前 = {(d - _dt.timedelta(days=10)).isoformat()}; two weeks ago = {(d - _dt.timedelta(days=14)).isoformat()}",
             week("last week/上周", mon - _dt.timedelta(days=7)),
             week("this week/本周", mon),
             week("next week/下周", mon + _dt.timedelta(days=7)),
             "English 'last Tuesday' = the most recent past Tuesday (this week or last week), mark approx. Chinese 上周二 = last week's Tuesday exactly.",
             "Spring Festival 2026 = 2026-02-17; 元旦 = 2026-01-01. 年前 = before Spring Festival (keep as text)."]
    return "\n".join(lines)

USER_NOTE_CAL = "{date_context}\n\nNote:\n{note}\n\nReturn the JSON object."

# ---------------------------------------------------------------- A: single pass
A_single = [
    (RULES, USER_NOTE),
]

# ---------------------------------------------------------------- B: extract, then self-check
B_CHECK_SYSTEM = RULES + """

You are now the CHECKER. You receive the original note and a draft JSON produced from it. Produce the corrected final JSON.
Go through the draft field by field and, for each item, ask: "Is this in the note, or derivable from the note date?"
- Not in the note → delete it, or if it is a guess about something unclear, replace it with an open question.
- A date sharpened beyond what the note supports → make it rough text or null; set precision accordingly.
- A prescription date used as a first-dose date → set the medicine date to null and ask when she started.
- Anything that advises, judges, reassures or diagnoses → rewrite as a question for the doctor, or delete.
- Something the note says that the draft dropped (a symptom, a reason, a place, a request, a refusal, a supplement) → add it.
- Re-run the EMERGENCY CHECK from scratch on the note itself, not on the draft.
Output the corrected JSON object only."""
B_CHECK_USER = "Note date: {note_date}\n\nNote:\n{note}\n\nDraft JSON to check:\n{prev}\n\nReturn the corrected JSON object."
B_selfcheck = [
    (RULES, USER_NOTE),
    (B_CHECK_SYSTEM, B_CHECK_USER),
]

# ---------------------------------------------------------------- C: questions + emergency first, then extract
C_FIRST_SYSTEM = RULES + """

STEP 1 ONLY. Do not extract the timeline yet. Read the note and output a JSON object with exactly:
{
  "emergency": {"warning": true|false, "sign": "<quote from note or null>", "source": "<NHS | 中风120/BEFAST | null>", "why": "<one line: which rule matched or why nothing matched>"},
  "nothing_medical": true|false,
  "unclear": ["<each thing in the note that is vague, unnamed, undated or unconfirmed — quote the words>"],
  "facts": ["<each concrete fact the note states, one per line, in the note's own words, with the relative date phrase kept verbatim>"]
}
Be exhaustive in "unclear" and "facts": every medicine, place, test, request, refusal, and reason."""
C_FIRST_USER = "Note date: {note_date}\n\nNote:\n{note}\n\nReturn the step-1 JSON object."
C_SECOND_USER = ("Note date: {note_date}\n\nNote:\n{note}\n\nYour step-1 analysis (emergency decision, unclear items, facts):\n{prev}\n\n"
                 "Now produce the final JSON. Keep the emergency decision from step 1 unless the note clearly contradicts it. "
                 "Every item in 'unclear' must become an open question (or a question-marked field), never a guess. "
                 "Every item in 'facts' must appear somewhere in the output. Add nothing that is not in 'facts' or derivable from the note date.")
C_questions_first = [
    (C_FIRST_SYSTEM, C_FIRST_USER),
    (RULES, C_SECOND_USER),
]

# ---------------------------------------------------------------- C2: C + medicine events, one entry per change
MED_RULE = """

MEDICINE EVENTS — ONE TIMELINE ENTRY PER CHANGE (this is where extractions fail most)
A medicine that was prescribed/started and later stopped is TWO timeline entries, each with its own medicine_event:
  entry 1: medicine_event.event = "started" (date = when she took the first dose if stated; if only the prescription/visit date is known, date = null and ask when she started)
  entry 2: medicine_event.event = "stopped" (date or rough text; reason = why she stopped; stopping_rule = what the doctor said, or null)
Likewise: every skipped day = its own "skipped" entry; a brand change = one "switched" entry (from/to in what); a one-off dose = "taken_once"; taking it again after a gap = "resumed".
Supplements, 保健品, 中药, teas she takes regularly also get a "started" entry (date null if unknown) AND go in current_medicines.
Before you output, count the medicines in the note and the changes to each; make sure every change has its own entry."""

C2_FIRST_SYSTEM = C_FIRST_SYSTEM.replace('STEP 1 ONLY.', 'STEP 1 ONLY.' ) + """
In "facts", list EVERY medicine change separately: "<medicine>: started <when>", "<medicine>: stopped <when>, because <reason>", "<medicine>: skipped <day>", "<medicine>: switched from X to Y", and every supplement / 中药 / tea she takes."""
C2_SECOND_USER = C_SECOND_USER + " Every medicine change listed in 'facts' must be its own timeline entry with its own medicine_event."
C2_meds = [
    (C2_FIRST_SYSTEM, C_FIRST_USER),
    (RULES + MED_RULE, C2_SECOND_USER),
]

DATE_GUARD = """

DATE GUARD (read before writing any date)
- A duration is not a date. "吃了一个星期" / "took it for 4 days" → the stop entry's date is TEXT like "about a week after starting" with precision "rough". Never compute a calendar day from a duration unless the note also dates the start of it.
- A month is not a day. "四月份" / "in June" / "上个月" → date "2026-04" / "2026-06" / "2026-07" (YYYY-MM), precision "rough". Never write the 1st of the month.
- "这半年" / "快两个月" / "最近" / "这几天" → TEXT ("about 6 months before the note", "the past few days"), precision "rough".
- The prescription/visit date is not the first-dose date: started.date = null unless the note says she started that day.
- Only "N days ago", "a week ago", "yesterday/昨天/前天", "last <weekday>/上周X", "next <weekday>/下周X", and explicit dates become YYYY-MM-DD.
Count: the output must not contain more YYYY-MM-DD dates than the note supports."""

C3_dateguard = [
    (C2_FIRST_SYSTEM, C_FIRST_USER),
    (RULES + MED_RULE + DATE_GUARD, C2_SECOND_USER),
]

# ---------------------------------------------------------------- C4: C2 + calendar anchors injected (plumbing fix for weekday arithmetic)
C4_FIRST_USER = "{date_context}\n\nNote:\n{note}\n\nReturn the step-1 JSON object."
C4_SECOND_USER = ("{date_context}\n\nNote:\n{note}\n\nYour step-1 analysis (emergency decision, unclear items, facts):\n{prev}\n\n"
                  "Now produce the final JSON. Keep the emergency decision from step 1 unless the note clearly contradicts it. "
                  "Every item in 'unclear' must become an open question (or a question-marked field), never a guess. "
                  "Every item in 'facts' must appear somewhere in the output. Add nothing that is not in 'facts' or derivable from the note date. "
                  "Every medicine change listed in 'facts' must be its own timeline entry with its own medicine_event. "
                  "Use the calendar above for every relative date; do not count days yourself.")
C4_calendar = [
    (C2_FIRST_SYSTEM, C4_FIRST_USER),
    (RULES + MED_RULE, C4_SECOND_USER),
]

VARIANTS = {
    "A_single": A_single,
    "C2_meds": C2_meds,
    "C4_calendar": C4_calendar,
    "C3_dateguard": C3_dateguard,
    "B_selfcheck": B_selfcheck,
    "C_questions_first": C_questions_first,
    "A_think": A_single,   # same prompt as A_single, but model reasoning ON (extra dimension: what does thinking buy?)
}
# Reasoning is OFF for every variant except these. Both Nemotron models think by default; Lightning burns ~10k
# tokens / 44 s per note with thinking on, 4 s with it off (probed 2026-10-30). Off = {"chat_template_kwargs": {"enable_thinking": False}}.
THINKING_ON = {"A_think"}
MAX_TOKENS_THINKING = 16000

# ---------------------------------------------------------------- SHIPPING (Jade, 2026-10-30 02:15)
SHIPPING_VARIANT = "C3_dateguard"
SHIPPING_MODEL = "lightning"
SHIPPING_THINKING = False

MODELS = {
    "lightning": "nvidia/Nemotron-3_5-Lightning",
    "nano": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
}

# ---------------------------------------------------------------- Doctor card: Chinese rendering
STOP_RULE_WORDING_LOCKED = "A"  # Jade, 2026-10-30 05:20
STOP_RULE_WORDINGS = {
    "A": "症状好转后，这个药还要继续吃吗？吃多久？",
    "B": "如果她感觉好了，这个药是不是就可以停了？还是要吃够几天？",
    "C": "这个药要吃到什么时候？好转了能不能停？",
    "D": "吃了觉得好了，这药还得接着吃吗？得吃几天？",
}
STOP_RULE_EN = "If symptoms improve, should she keep taking this medicine, and for how long?"

CARD_ZH_SYSTEM = """You render a one-page doctor card into Chinese. The card is written by a daughter for her mother ("妈妈"), who will read it or show it to a doctor in China.

You receive a JSON object with English (or mixed) strings grouped in sections. Return a JSON object with EXACTLY the same keys, the same arrays in the same order and the same lengths, where every string is rewritten in natural, plain Chinese that an older person can read aloud and a doctor can scan quickly.

RULES
1. Say only what the input says. Add nothing: no diagnosis, no suggestion, no reassurance, no explanation of what a result means. Never judge what a doctor should have done.
2. Keep every date, number, dose, duration and test name exactly. "about 2020" → "大约2020年"; "approx 2026-10-22" → "大约2026年10月22日"; "before Spring Festival" → "春节前". Rough stays rough.
3. Keep medicine, product and hospital names as written, and keep the KIND of product exactly: toothpaste stays 牙膏, antibiotic stays 抗生素, a brand letter stays that letter ("toothpaste X" → "X牙膏" or "牙膏X", never 抗生素X). Chinese stays Chinese; English names stay in English with no translation guess. If the input says "name unknown" write "名字不清楚".
3b. Translate every string on its own. Never let one item's content leak into another item.
3c. Common words: appointment/visit → 预约/看病; follow-up → 复查; dentist → 牙医; prescribed → 开了; stopped → 停了; dates "2026-10-29" → "2026年10月29日", "about 2026-10-22" → "大约2026年10月22日".
4. Questions stay questions, addressed to the doctor politely: "想请问医生：……？".
5. Short sentences. Spoken Mandarin, not medical-report style. Refer to the patient as 妈妈 or 她; "I" / "the note-writer" / "her daughter" is 我 (the daughter writing the card).
6. Output the JSON object only, no prose, no markdown fences."""
