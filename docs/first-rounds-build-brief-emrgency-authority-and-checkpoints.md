# First Rounds: build brief for the coding session

*Family does the first rounds.*

First Rounds turns quick notes I write after phone calls with my mom into a health timeline, reminders, and a doctor card in Chinese that she shows at appointments. Product details: see `first-rounds.md` and `first-rounds-additions.md`.

**Deadline:** Nebius x NVIDIA Global AI Hackathon, Oct 30, 2026, 10:00 PDT = **18:00 Valencia time**. Target: submitted by **16:00**.

## Model setup
- Nebius Token Factory, OpenAI-compatible API: `https://api.tokenfactory.nebius.com/v1/`
- Default model: `nvidia/Nemotron-3_5-Lightning` (EU-hosted, eu-north1)
- Comparison model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (EU-hosted, eu-north1)
- Do NOT use US-hosted models (Nemotron 3 Super, Ultra, Super VL) for health data.
- API key lives in an environment variable, server-side only. Never in browser code, never in the repo.

## Non-negotiable rules
1. **No medical advice.** The app records, organizes, and prepares questions. It never diagnoses, never judges what a doctor should have done, never decides whether to stop or change a medicine.
2. **Real data never enters git.** My real notes live in `private/`, which is in `.gitignore` from the very first commit. Deleting later does not remove it from git history, and the repo will be public.
3. **Names replaced with "Mom"** before any text is sent to the model.
4. **Public material** (demo data, README, video) uses invented data, generic product names, and generic drug names (e.g. amoxicillin, not a brand name).
5. **The app never contacts Mom directly.** I forward the doctor card myself.

## Checkpoints
At every **STOP** below, pause and show me the results. Do not continue until I approve.

## Sequence

### Step 0: Setup (~15 min)
- Create repo with `.gitignore` containing `private/` and `.env` BEFORE the first commit.
- Write the no-medical-advice rule and the emergency spec (below) into the system prompt and CLAUDE.md.

### Step 1: Model test (~30–45 min, no app yet)
- Simple script: send my 3 real notes (from `private/`) + ~5 Claude-written variations through both models.
- Variations must cover: relative dates ("10 days ago"), a rough date ("about 2020"), a medicine stopped because she felt better, "the scan was fine" without saying which scan, an emergency that already resolved, a normal note.
- Output: one page showing both models' timeline output side by side per note.

**STOP: "correct for Mom" check.** I review: dates right, rough dates still rough, nothing invented, medicine events caught, unclear things turned into questions.

**STOP: emergency sign-off.** I review every note: urgent notes flagged, normal notes not flagged.

Then: I pick the model, we fix the prompt.

### Step 2: App core (most of the day)
- "After the call" note input → timeline (with medicine events, department, test, result, helps/worsens).
- Look of the app: one page with independent toggles (mood / type / density / accent color), max 30 min including my decision. Then lock choices into `design.md` and add to CLAUDE.md: *All UI follows design.md. Don't invent new colors, fonts or spacing.*

### Step 3: Doctor card, stop-check, emergency message
- Doctor card (Chinese, with English version): history, tests already done (what, where, when, result), current medicines incl. supplements / 保健品 / 中药, "ask the doctor" questions, and for every new medicine: 症状好转后，这个药还要继续吃吗？吃多久？
- Stop-check: medicine stopped → show doctor's stopping rule if recorded; otherwise to-do "ask doctor or pharmacist" + drafted question.
- Emergency message (spec below).

**STOP: Chinese wording check.** I review: natural for Mom, readable for a doctor.

**STOP: medical advice check.** I review every generated question and to-do for borderline wording.

### Step 4: Deploy, README, video
- Deploy with demo data (invented).
- README: setup instructions, how Nemotron and Token Factory are used, emergency sources (below), "does not diagnose" statement, open-source license (MIT / Apache 2.0) visible in the repo's About section.

**STOP: privacy check before anything goes public.** Repo (including history), README, video, demo data: no real data about Mom, no brand names.

### Step 5: Submit by 16:00
- Git tag `hackathon-submission` on the submitted version; link that in Devpost.
- After submitting: new work only on a separate branch until judging ends Dec 15.

## Emergency warning spec

### Sources (cite in README and in the message)
- **General emergencies:** NHS guidance on when adults should call an ambulance / go to A&E.
- **Stroke:** "中风120" (promoted by China's National Health Commission for World Stroke Day) + "BEFAST" (Chinese Stroke Association).

### Warning signs (my own wording, based on the sources above)
General:
- chest pain, pressure, heaviness or tightness
- sudden confusion (unsure of own name or age)
- severe difficulty breathing (can't get words out, gasping), choking
- heavy bleeding, severe injury
- seizure
- sudden rapid swelling of lips, mouth, throat or tongue
- suicide attempt or self-harm (different message: crisis support, not only 120)

Stroke (中风120 + BEFAST):
- face uneven, mouth drooping on one side
- one arm or leg suddenly weak or numb
- speech suddenly slurred, confused, or hard to understand
- sudden loss of balance, unsteady walking
- sudden vision problems
- sudden severe dizziness together with any of the above

### Rules
- **Any one sign is enough.** Don't wait for several.
- **Resolved episodes count.** "She felt dizzy for 5 minutes, she's fine now" must still trigger the warning. Guidance says not to wait for symptoms to go away.
- **Don't just file it.** The warning appears immediately, before the timeline entry.
- **Never diagnose.** Say "possible warning sign", never "she's having a stroke", never "it's probably nothing".
- **Remote family:** I'm in Spain; 120 dialed from abroad won't reach her. The message tells me to call Mom now; she or someone near her calls 120.

### Message template
English:
> This note describes a possible warning sign: [sign]. [Source] advises calling emergency services (120 in China) immediately, even if symptoms have passed. Call Mom now. If signs are present, she or someone near her should call 120.

Chinese:
> 这条记录提到了可能的预警信号：[信号]。[来源]建议：即使症状已经消失，也应立即拨打120。请现在给妈妈打电话；如果症状仍在，请她或身边的人拨打120。

### Must-pass test cases
- stroke sign happening now → warning
- stroke sign that resolved ("arm felt weird for a bit, she's fine now") → warning
- sudden dizziness with vision changes → warning
- chest tightness mentioned casually → warning
- ordinary toothache / tired after a walk → no warning

Emergency detection must catch 100% of positives. A few false alarms are acceptable; a missed emergency is not.

## Next steps (README only, not built now)
- evaluation set for extraction accuracy and emergency detection
- saved local contact near Mom for emergencies
- visit recording with consent, photo upload of records, department tree view, body map / tooth chart input
