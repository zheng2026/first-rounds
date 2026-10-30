# First Rounds

*Family does the first rounds.*

First Rounds is for the daughter or son of a parent who never remembers her own medical history. After a phone call, the daughter types or dictates what Mom said. The app turns it into a timeline, reminders and a one-page doctor card in Chinese. Most of Mom's health happens outside the hospital, before the doctor writes the first line, and this is where it gets captured.

## What it does

- **After the call:** you note whatever Mom told you about discomfort or medicine, typed or dictated with your phone keyboard, and the app reads it.
- **Timeline:** every event gets an entry with a date (relative dates like "10 days ago" are calculated from the note date and shown as approximate), a link back to the note it came from, and a question for you whenever something is unclear instead of a guess.
- **Today:** reminders, open questions, upcoming appointments and any warning, with ntfy push as an optional fallback.
- **Doctor card:** a one-page card in Chinese (English version for you) with past history, tests already done, current medicines and questions to ask, ready to forward to Mom yourself.
- **Stop-check:** when Mom stops a medicine, the app shows the stopping rule the doctor gave, or, if none was recorded, makes a to-do with a drafted question for a doctor or pharmacist.
- **Emergency warning:** a note that mentions a possible warning sign shows a warning first, before anything is filed.

## Does not diagnose

The product rules, which the code and prompts follow:

1. No medical advice. The app records, organizes and prepares questions. It never diagnoses, never judges what a doctor should have done, never decides whether to stop or change a medicine.
2. Real data never enters git. Real notes live in `private/`, which is gitignored from the first commit.
3. Names are replaced with "Mom" before any text is sent to the model.
4. Public material (demo data, README, video) uses invented data, generic product names and generic drug names.
5. The app never contacts Mom directly. You forward the doctor card yourself.

## Emergency warning

A note triggers the warning if it mentions any of these signs (condensed):

- chest pain, pressure, heaviness or tightness
- sudden confusion (unsure of own name or age)
- severe difficulty breathing, gasping, choking
- heavy bleeding or severe injury
- seizure
- sudden rapid swelling of lips, mouth, throat or tongue
- suicide attempt or self-harm (different message: crisis support, not only 120)
- stroke signs: face uneven or mouth drooping, one arm or leg suddenly weak or numb, speech suddenly slurred or hard to understand, sudden loss of balance, sudden vision problems, sudden dizziness

Two rules:

- **Any one sign is enough.** The app does not wait for several.
- **Resolved episodes still count.** "She felt dizzy for 5 minutes, she's fine now" still triggers the warning, because the guidance says not to wait for symptoms to go away.

The wording is always "possible warning sign", never a diagnosis. The message tells the family member (who may be abroad, where 120 will not reach Mom) to call Mom now, and Mom or someone near her to call 120.

English:
> This note describes a possible warning sign: [sign]. [Source] advises calling emergency services (120 in China) immediately, even if symptoms have passed. Call Mom now. If signs are present, she or someone near her should call 120.

Chinese:
> 这条记录提到了可能的预警信号：[信号]。[来源]建议：即使症状已经消失，也应立即拨打120。请现在给妈妈打电话；如果症状仍在，请她或身边的人拨打120。

Sources:

- General emergencies: NHS guidance on when to call an ambulance / go to A&E. <https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/>
- Stroke: NHS stroke symptoms. <https://www.nhs.uk/conditions/stroke/symptoms/>
- Stroke: "中风120" (promoted by China's National Health Commission for World Stroke Day).
- Stroke: "BEFAST" (Chinese Stroke Association).

The sign list is our own wording based on these sources. "Sudden dizziness on its own" was added per the NHS stroke symptoms list.

## How Nemotron and Nebius Token Factory are used

The app calls Nebius Token Factory through its OpenAI-compatible endpoint, `https://api.tokenfactory.nebius.com/v1`.

- **Shipping model:** `nvidia/Nemotron-3_5-Lightning` (EU-hosted), with reasoning off via `chat_template_kwargs: {enable_thinking: false}`. With thinking on, Lightning spent about 10k tokens and 44 s per note and scored no better. With it off, a note takes about 4 s.
- **Comparison model in evaluation:** `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- **No US-hosted models** are used for health data.

The model makes two calls:

1. **Extraction**, with prompt variant `C3_dateguard`: a two-step prompt that handles questions and emergencies first, plus a rule for one timeline entry per medicine change and a date guard (durations and months never become exact days).
2. **Chinese doctor-card rendering**, which translates the card text and adds nothing.

Everything else is code, not the model: the stop-check, the emergency message, doctor-card assembly and date ordering.

## Evaluation

Before building the app we ran a test set through the models and scored the output. The test set has 21 notes: 18 invented, and 3 real ones that stay private. The first round was 4 prompt variants (including one with thinking on) × 2 models × 21 notes, followed by prompt iterations on Lightning. A human reviewed the judgment dimensions (invented facts, advice wording) on a results page.

| Finding | Result |
|---|---|
| Emergency recall | 100% on every thinking-off combination |
| False alarms | One variant on the comparison model over-fired (4 false alarms) |
| Thinking on, Lightning | about 219 s per note on average, impractical |
| Medicine events found | 0.33 to 0.47 in the first round, the weak spot everywhere |
| Medicine events after the C-family iterations | 0.44 → 0.64 (shipping variant) |
| Rough dates stay rough (shipping variant) | 0.90 |
| Advice-lexicon score (shipping variant) | 0.95 |

Emergency detection must catch every positive; a few false alarms are acceptable, a missed emergency is not.

## Run it locally

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```
NEBIUS_API_KEY=...
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
```

(or run `tools/set_key.sh`). Then:

```
.venv/bin/uvicorn app.main:app --port 8000
```

Open <http://127.0.0.1:8000>. To load the demo story (invented notes), visit `GET /api/demo/load`.

Optional environment variables:

- `PRIVATE_NAMES`: names that are replaced by "Mom" before any text reaches the model.
- `NTFY_TOPIC`: push each new to-do to an ntfy topic.
- `FR_DB`: path to the SQLite file (default `data/firstrounds.sqlite`).
- `FR_DEMO_ON_START=1`: load the demo story on first start when the database is empty.

## Live demo

<https://first-rounds-production.up.railway.app> — invented demo data (the tooth story), loaded on first start. Runs on Railway from the Dockerfile; the key lives only in the service environment.

## Deploy

```
docker build -t first-rounds .
docker run -p 8000:8000 -e NEBIUS_API_KEY=... -e NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1 -e FR_DEMO_ON_START=1 first-rounds
```

The key lives only in the server environment, never in browser code.

## Privacy

- Open source: each family runs its own copy, so no company holds everyone's health data.
- The app never contacts Mom directly. You forward the card yourself.
- Names are replaced with "Mom" before anything is sent to the AI.
- The AI is Nemotron on Nebius Token Factory, an EU-hosted model.
- Real notes live in `private/`, gitignored from the first commit.

The demo data is invented and uses generic names (toothpaste X, brand A, antibiotic Y).

## Repo layout

- `docs/`: specs and the idea description
- `tools/`: evaluation runner, scorer, prompts
- `tests/`: test set and results (the private part is gitignored)
- `private/`: real notes, gitignored
- `design/`: look variants, then `design.md`
- `app/`: the FastAPI backend, SQLite storage and static front end

## Built with

This was built with the variants method (`docs/Guideline_build-with-variants.md`). Instead of reading many chat turns, the author reviewed comparison pages: one for model and prompt output quality, one for the look of the app. Each decision was made once and then locked. The design is locked in `design/design.md` (minimal mood, rounded type, spacious density, indigo accent).

## Roadmap (v2)

- Record the doctor visit, with the doctor's permission (consent card in Chinese).
- Speech-to-text, then extract diagnosis, medicines, stopping rules and follow-ups.
- Check a prescription photo against the recording for drug names and doses.
- Delete the audio, keep notes and quoted lines.
- After the visit, check whether the doctor saw what was on the card (for example crowns not mentioned, so ask next time).

## License

MIT. See `LICENSE`.
