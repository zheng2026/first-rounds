Claude.md

Open every response to me by addressing me: "Jade,..."

# How anything starts
Do not do anything until I give the "Go". Without the "go", we are still in the discussing/planning stage.


# Agents Use
I use Fable and interact with Fable directly. When you build something, please use lower model agents based on your judgement.

Parallel agents are allowed when the situation justifies, but your children agents may not spawn agents.

When agents have to be spawned. Present the number agents, model and effort level.

# Housekeeping
Maintain a log.md so other sessions can pickup the work right away

# Big file intakes
Before reading content in any large or unfamiliar tree, use the big-intake skill (/big-intake): census first (du/find/wc/grep -l, anchors only), scouts on a cheaper model for orientation, expensive model re-derives every load-bearing claim. Never bulk-read.

# Product rules (non-negotiable)
1. **No medical advice.** The app records, organizes, and prepares questions. It never diagnoses, never judges what a doctor should have done, never decides whether to stop or change a medicine.
2. **Real data never enters git.** My real notes live in `private/`, which is in `.gitignore` from the very first commit. Deleting later does not remove it from git history, and the repo will be public.
3. **Names replaced with "Mom"** before any text is sent to the model.
4. **Public material** (demo data, README, video) uses invented data, generic product names, and generic drug names (e.g. amoxicillin, not a brand name).
5. **The app never contacts Mom directly.** I forward the doctor card myself.

# Emergency warning spec

## Sources (cite in README and in the message)
- **General emergencies:** NHS guidance on when adults should call an ambulance / go to A&E.
- **Stroke:** "中风120" (promoted by China's National Health Commission for World Stroke Day) + "BEFAST" (Chinese Stroke Association).

## Warning signs (my own wording, based on the sources above)
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
- sudden dizziness (on its own — NHS stroke symptoms list; Jade's decision 2026-10-30)

## Rules
- **Any one sign is enough.** Don't wait for several.
- **Resolved episodes count.** "She felt dizzy for 5 minutes, she's fine now" must still trigger the warning. Guidance says not to wait for symptoms to go away.
- **Don't just file it.** The warning appears immediately, before the timeline entry.
- **Never diagnose.** Say "possible warning sign", never "she's having a stroke", never "it's probably nothing".
- **Remote family:** I'm in Spain; 120 dialed from abroad won't reach her. The message tells me to call Mom now; she or someone near her calls 120.

## Message templates
English:
> This note describes a possible warning sign: [sign]. [Source] advises calling emergency services (120 in China) immediately, even if symptoms have passed. Call Mom now. If signs are present, she or someone near her should call 120.

Chinese:
> 这条记录提到了可能的预警信号：[信号]。[来源]建议：即使症状已经消失，也应立即拨打120。请现在给妈妈打电话；如果症状仍在，请她或身边的人拨打120。

## Must-pass test cases
- stroke sign happening now → warning
- stroke sign that resolved ("arm felt weird for a bit, she's fine now") → warning
- sudden dizziness with vision changes → warning
- chest tightness mentioned casually → warning
- ordinary toothache / tired after a walk → no warning

Emergency detection must catch 100% of positives. A few false alarms are acceptable; a missed emergency is not.

# Model setup
- Base URL: https://api.tokenfactory.nebius.com/v1 (Nebius Token Factory, OpenAI-compatible)
- Shipping model: `nvidia/Nemotron-3_5-Lightning` with reasoning OFF (`chat_template_kwargs: {enable_thinking: false}`)
- Comparison model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`
- No US-hosted models (Nemotron 3 Super, Ultra, Super VL) for health data.
- API key only in `.env` / server env, never in browser code, never in the repo.
- The shipping prompt is `tools/prompts.py` → `VARIANTS[SHIPPING_VARIANT]`.

# Repo layout
- `docs/` — specs
- `tools/` — eval runner, scorer, prompts
- `tests/` — private test set + results, gitignored
- `private/` — real notes, gitignored
- `design/` — look variants, then design.md
- `app/` — step 2, not yet

# Checkpoints
Every STOP in docs/first-rounds-build-brief-emrgency-authority-and-checkpoints.md means: show Jade, wait for approval.

# Design
All UI follows `design/design.md`. Don't invent new colors, fonts, sizes or spacing. Locked 2026-10-30: mood=minimal, type=rounded (Nunito), density=spacious, accent=indigo. `design/look.html` is the variants page (glass mood kept there for later, not for the hackathon).
