Hackathon-Nebius_idea-description

# Task Description
i am making this for the hackathon:https://nebiusglobalaihackathon.devpost.com/?_gl=1*zdsyzo*_ga_0YHJK3Y10M*czE3OTMyODc4MjgkbzEkZzEkdDE3OTMyODc4ODgkajYwJGwwJGgw

Requirement
"Best Apps and Agents Track 
Build any app or agent someone would actually use, from a productivity tool or copilot to a workflow that runs itself. Power it with Nemotron models on Nebius through Token Factory. Reach for Nemotron 3 Ultra when you need serious reasoning, and let Nano or Super handle the fast, everyday calls, so your app stays responsive and your credits stretch further. We encourage you to deploy your application with Nebius Serverless Endpoints, or use Nebius Serverless Jobs for background processing and asynchronous workflows, though neither is required."



# Idea: First Rounds
*Family does the first rounds.*

## Idea
my mother never remembers anything about her medical history. she doesn't remember when and where she did what for her hospital visits. she doesn't have the ability to keep track of all of her physical or electronic records. she just knows to do one thing: get an appointment (挂号), go to the hospital, talk to the hospital doctor. and she is not even able to describe everything in time, so she gets kind of rushed out, unless I am there.

last year, she went to a dentist. she forgot about all the treatments she had done — she forgot that there was crowning of her teeth, and the dentist did not bother to find out or investigate. the dentist redid the crowning on teeth that already had crowns, which led to some pain.

HOWEVER, she DOES tell me almost everything.

most of her health happens outside the hospital, before the doctor writes the first line. First Rounds captures it.

## How it works
after a call with her, I get a reminder on my phone ("After the call") to note whatever discomfort / medicine stuff she told me (typed or speech-to-text). the app turns it into different representations.

screens: **After the call → Timeline → Doctor card**

### Example
on 10/29 I say: "her teeth started hurting 10 days ago, she tried X, but it didn't work, she heard A is better, wants me to buy it. she is trying to get an appointment next week"

the AI turns it into a timeline:
- 10/19: teeth started hurting, tried toothpaste X, didn't work
- 10/29: wants to know if I can buy brand A for her

rules for the timeline:
- relative dates ("10 days ago") are calculated from the date of my note and shown as approximate
- every entry links back to the note it came from
- anything unclear becomes a question for me ("which tooth?") instead of a guess

the AI also tracks medicine events separately:
- started / stopped / skipped, with date
- any stopping rule mentioned ("doctor said finish all 7 days", "stop when swelling goes down")
- if no stopping rule was ever mentioned for a medicine, it's marked: "no stopping instruction recorded"

### Reminders
1) buy brand A for mom
2) follow up on how she felt with brand A
3) mom will have an appointment next week: has the date been confirmed?

### Doctor card
before she goes to the doctor, the app makes a one-page card in Chinese (English version for me). I send it to her via WeChat (could be email, WhatsApp, etc. for other families). she reads it or shows it to the doctor. it aggregates past history:

    2024: crowns on __, __, __
    10/19: teeth started hurting, tried toothpaste X, didn't work
    10/31: tried brand A, {results}
    ask doctor: what could be the reasons for the tooth pain? what are the options, pros and cons?
    for every new medicine: 症状好转后，这个药还要继续吃吗？吃多久？
    (if symptoms improve, should she keep taking this, and for how long?)

## Medicine stop-check
my mom stops taking medicine once she feels better ("it did its job").
the doctor often has a plan with conditions, but she only gets the first step.

example (continuing the tooth story):
- 11/3: dentist prescribes antibiotic Y, 3x a day
- 11/6: after the call I note: "teeth feel better, she stopped Y"

the app checks the timeline for a stopping rule:
- if the doctor said one (e.g. "finish all 7 days") → reminder: "tell mom: the doctor said to finish all 7 days"
- if none was recorded → to-do: "mom stopped Y on 11/6, no stopping instruction recorded. ask doctor or pharmacist."
  + drafts the question with details filled in: medicine, start date, what improved, when she stopped

rule: the app never decides whether stopping is ok. it only shows what the doctor said, or makes sure someone qualified gets asked. no medical advice anywhere in the app.

## Privacy
- open source: each family runs its own copy, no company holding everyone's health data
- the app never contacts mom directly; I forward the card myself
- names replaced with "Mom" before sending to the AI
- AI: Nemotron on Nebius Token Factory, EU-hosted model

## v1 (hackathon)
1. After the call → timeline (with medicine events)
2. doctor card (with the stopping-rule question)
3. stop-check to-do
4. reminders / "Today" panel (ntfy notifications as fallback)

## v2
- record the doctor visit (with the doctor's permission, consent card in Chinese)
- speech-to-text → extract diagnosis, meds, stopping rules, follow-ups
- check prescription photo against the recording for drug names and doses
- delete audio, keep notes + quoted lines
- check after the visit: did the doctor see what was on the card? (e.g. crowns not mentioned → ask next time) 