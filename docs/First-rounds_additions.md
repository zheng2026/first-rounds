First-rounds_additions

# First Rounds: additions (11 items)

## Build tomorrow (cheap: extraction fields, card sections, simple rules)

### Extraction format
every note → timeline entries. each entry has:
- date (exact or approximate; rough dates stay rough: "about 2020" never becomes "2020-01-01")
- what happened
- department (dentistry, urology, neurology…) if mentioned
- test / procedure (name it exactly: "plain MRI", not "a scan") + where it was done
- result, including normal / ruled out
- medicine event: started / stopped / skipped / switched, + stopping rule if mentioned
- helps / makes it worse (heat helps, bananas make it worse…)
- link to the note it came from
- open questions for me, if anything is unclear

### 1. Ask for history when it matters
- when a note mentions an upcoming appointment → one history question for that kind of visit
  ("dentist next week — any past dental work you know of? crowns, fillings, extractions?")
- my answer is saved as a normal note
- no setup step, no onboarding screen

### 3. Tell the doctor what was already done
- doctor card section: **tests already done** (what, where, when, result)
- especially tests done at another hospital, which the new doctor can't see
- normal results included: "ruled out" is information

### 4. Turn vague or missing questions into real ones
- doctor card "ask the doctor" section, built from notes:
  "what does this result mean?" / "what should she do next?" / "was [specific test] considered?"
- precise questions, never judgments of what the doctor should have done

### 5. Emergency warnings
- if a note describes sudden or severe symptoms (sudden dizziness or vision changes, weakness on one side, trouble speaking, chest pain, severe sudden pain) → don't just file it
- show a clear message: seek urgent care now
- a short warning-sign list + one rule

### 6. Current medicines on the doctor card
- everything she's taking now, including vitamins, fish oil, 保健品, 中药
- doctors always ask; supplements are where interactions hide

### 7. Medicine stop-check
- she stopped a medicine → doctor's stopping rule recorded? show it
- no rule recorded → to-do: "ask doctor or pharmacist" + drafted question (medicine, start date, what improved, when she stopped)
- doctor card: 症状好转后，这个药还要继续吃吗？吃多久？ for every new medicine

### 8. Ruled out + what helps / what makes it worse
- extraction fields only (see format above)
- shown on the card as short lists if there's room

### 9. Trust rules
- every entry links to its source note
- unclear → question, never a guess
- rough dates stay rough

### 10. No medical advice
- the app records, organizes and prepares questions
- it never judges what a doctor should have done
- it never decides whether to stop or change a medicine

### 11. Privacy defaults
- names replaced with "Mom" before anything reaches the AI
- EU-hosted model (Nemotron-3.5-Lightning)
- open source: each family runs its own copy
- the app never contacts mom directly; I forward the card myself
- public material (demo, README, repo): invented data, generic product names, generic drug names

### Only if the core works
- body outline / tooth chart on the doctor card, display only (marks areas or tooth numbers already in the data)

## Leave for v2
- **1. records:** photo upload of 病历本 / prescriptions / reports, "from a record" vs "from memory" labels, conflict flags, vision model decision (Super VL is US-only; MiniCPM-V-4.5 is EU but not NVIDIA)
- **3. department tree view:** what was checked in which department, for problems that bounce between departments
- **4. visit recording:** consent card in Chinese, speech-to-text, extract diagnosis / meds / stopping rules / follow-ups, delete audio, check against prescription photo, "was the card covered?" check
- **body map / tooth chart input:** paper chart on her fridge with numbered areas, or I tap while she describes; FDI tooth numbers for the dentist
- **step-goal coaching** (Longcut) and web push notifications (ntfy until then)

## Variants: additions
### Test notes
- **2. small real input, Claude makes variations, I write what correct looks like**
  - give Claude 2–3 real cases + dimensions, ask for ~15 notes in my style, then I edit them
  - dimensions: kind of problem (teeth, blood pressure, stomach, sleep, a fall) / language (Chinese, English, mixed) / date phrasing ("10 days ago", "last Tuesday", "about 2020", "before New Year") / medicine events (started, stopped because better, skipped, switched) / unclear details ("one of her teeth", "the pink pills")
  - **I write the expected answer for every note.** that's the real work; the runner can't score without it
- **sources:** mom's real cases + XHS for situations. rewrite, never copy; read manually, no scraping. write everything as a quick messy note after a call, not as a polished post
- **names:** real brand and drug names in the test set (realistic difficulty); generic in anything public
- **10–15 notes total.** coverage matters more than count: every tricky case at least once

### New tricky cases
- a multi-department journey (stomach → gynecology → urology, mostly normal results)
- "the scan was fine" without saying which scan → must become a question
- a sudden-symptom note → must trigger the urgent-care message, not a timeline entry only
- a stopped medicine because she felt better → stop-check
- a note listing supplements / 中药 → current medicine list
- a rough date → must stay rough
- an appointment mentioned → history question for that type of visit

### Scoring additions
- department / test / result captured correctly, including normal results
- emergency notes flagged every time (this one must be 100%)
- no medical advice anywhere in the output