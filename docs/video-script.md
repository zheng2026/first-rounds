# First Rounds — 90-second demo (voice first, then click along)

If asked how memory works: raw notes + the model's extraction go into one SQLite file on the family's own server (on Railway, a mounted volume). Only the note text, with names replaced by "Mom", ever goes to the model. The timeline, Today and the doctor card are all read back from that file; nothing is re-extracted.

## Step 1 — record the narration on the iPhone (done by Jade)
Read the "you say" column top to bottom, one pause between rows. Send the file (.m4a is fine) to Claude.

## Step 2 — record the screen, clicking along to the narration
1. Chrome window about 600 px wide on https://first-rounds-production.up.railway.app, Timeline tab showing. Paste text ready in the clipboard (the note below).
2. Put the narration on the iPhone with earbuds in, finger on play.
3. Mac: Cmd+Shift+5 → Record Selected Portion → drag over the browser → Options → Microphone: **None** → Record.
4. Press play on the phone. Click on the cue words in the table. Being a second early or late is fine; Claude stretches the video to fit the voice.
5. Stop with the icon in the menu bar. Send the .mov to Claude. Claude merges voice + video with ffmpeg and returns the finished file for YouTube (Unlisted).

Cue table for Jade's recorded narration (2:43). Watch the phone's timer; click at these times. The bold words are what you hear there.

| time | you hear | you do |
|---|---|---|
| 0:00 | "My mother went to see a dentist…" | nothing; Timeline tab is showing. Scroll very slowly down and back up during the intro |
| 0:38 | "**After a call with mom**, I write down…" | click **+ After the call** |
| 0:44 | "…exactly how she said it" | paste the note into the box (Cmd+V) |
| 0:48 | "…**does that part**" | click **Turn into timeline** (it takes ~10 s; the result lands as you say "warning sign") |
| 0:58 | "this note mentions her hand going weak" | the red block is on screen; move the mouse over it slowly |
| 1:11 | "**call her now**" | leave it; nothing to click |
| 1:20 | "**Everything is organized** … into a timeline" | click **Done**; scroll the Timeline slowly |
| 1:25 | "links back to my **exact words**" | click one **❝ from note** link so the quote opens |
| 1:28 | "**about two weeks ago**" | point at an entry whose date says *about* or *rough* |
| 1:34 | "she **stopped her medicine**" | scroll to the **Stop-check** card; keep it on screen until 1:49 |
| 1:49 | "before her **next appointment**" | click **Doctor card**, select **Teeth**, click **Make card** (renders by ~2:00) |
| 2:02 | "One page currently in **Chinese or English**" | click **English**, then **中文** |
| 2:06 | "I **send it over**" | click **Copy text** |
| 2:18 | "My mother won't have to **install anything**" | click **Timeline** |
| 2:43 | end | stop the recording |

## Script (the "you say" column is what Jade reads)

| time | you click | you say |
|---|---|---|
| 0:00 | nothing, Timeline tab is showing | "This is First Rounds. Family does the first rounds. My mother never remembers her medical history. Last year a dentist re-crowned teeth that already had crowns, because nobody had the record. But she tells me everything on the phone. So after each call, I write one messy note, and the app does the rest." |
| 0:20 | click **+ After the call**, paste the note below, click **Turn into timeline** | "I type what she said, Chinese or English, exactly as messy as I talk. Nemotron on Nebius Token Factory reads it." (keep talking while it works, ~10 s) |
| 0:35 | result view appears: point at the red block | "This note mentions a hand that went weak for a minute. Any one stroke sign, even if it passed, shows a warning first, before anything is filed. The sources are NHS and 中风120. It never diagnoses. It tells me to call her now." |
| 0:50 | click **Done**, scroll the Timeline, click one **❝ from note** link, then scroll to the **Stop-check** card | "Every note is saved as I wrote it, on our own server, in one small database file. The model reads a note once and returns entries, questions and to-dos; each one is stored with a link to the note it came from, so I can always see the exact words. Rough dates stay rough. And here is the stop-check: she stopped the antibiotic when she felt better. The dentist said seven days. The app does not decide, it just makes sure she hears what the dentist said." |
| 1:10 | click **Doctor card**, select Teeth, click **Make card**, let it render, click **Copy text** | "Before her next visit I make the doctor card. It is built from everything stored so far: history, tests already done, current medicines, and questions to ask. The model only puts it into Chinese. One page. I send it to her on WeChat; she shows it to the doctor." |
| 1:25 | back to Timeline | "Open source, each family runs its own copy. Nemotron 3.5 Lightning, EU-hosted, reasoning off: four seconds a note. The model extracts; the rules are code. First Rounds." |

Note to paste at 0:20 (invented, generic names):

mom called. this morning she got dizzy out of nowhere getting up from the sofa and her right hand felt weak for about a minute, she dropped her cup. she says she's totally fine now and doesn't want to bother anyone. 还有她说牙不疼了，抗生素Y吃了两天就停了
