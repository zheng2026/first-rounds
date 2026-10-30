Guideline_build-with-variants

# First Rounds: building with variants

Based on Thorsten Ball's rule: don't iterate with the agent, have it build the iteration tool.
I review one comparison page instead of reading twenty chat turns.

## Principles
- **Name the dimensions first; the count follows.** "20 variants" with no dimensions = 20 near-duplicates. 3 dimensions × 2 options = 8 variants that are actually different, and I learn which dimension matters.
- **Vary only where my judgment is the bottleneck.** For me that's design/UI and AI output quality.
- **Don't vary:** plumbing, deployment, data format, API setup. Decide those once.
- **Max variants = what I can compare on one page in ~5 minutes.** ~20 for small visual things judged at a glance; 4–6 for anything I have to read carefully.
- **One page per decision**, with toggles or side-by-side views. I decide once, then move on.

## Order and time boxes
1. Notes → timeline (AI quality). Correctness matters most.
2. Look of the app (vary once, then lock). Max 30 minutes including my decision.
3. Doctor card layout.
4. Timeline layout.

## 1. Notes → timeline (start here)
**My job (only I can do this):** write ~5 realistic test notes, including tricky cases:
- relative dates ("10 days ago", "next week")
- a stopped medicine ("she feels better, stopped the pills")
- something unclear ("one of her teeth hurts")
- the appointment-next-week case
- a note with nothing medical in it

**Ask Claude Code for:**
> 3 prompt variants × 2 models (nvidia/Nemotron-3_5-Lightning, nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B, both EU-hosted on Token Factory) = 6 combinations. A runner that sends all 10 test notes through all 6, and one results page: a score table (dates calculated correctly, no invented facts, medicine start/stop events captured, unclear things turned into questions) plus a side-by-side view of the outputs for any note I click.

The winner decides the model. Default: Nemotron-3.5-Lightning.
If Nemotron's Chinese is weak, test an EU-hosted Chinese-strong model (e.g. Qwen3-235B) for the Chinese wording only. Nemotron stays the core.

## 2. Look of the app: vary once, then lock
**Ask Claude Code for:**
> One page showing the timeline screen with my tooth example as real data. Independent toggles per dimension so I can mix and match:
> - Mood: warm and family-like / calm and clinical / plain and minimal
> - Type: rounded sans-serif / classic serif / large and high-contrast for older eyes
> - Density: spacious / compact
> - Accent color: 3–4 options

**Then lock it:**
> Write my choices into design.md: colors, fonts, sizes, spacing, corner roundness, plus example components (timeline entry, button, card).

**Add to CLAUDE.md:**
> All UI follows design.md. Don't invent new colors, fonts or spacing.

After this, I only vary layout, never the look.

## 3. Doctor card (~8 layout variants)
**Ask Claude Code for:**
> 8 doctor card variants on one page with toggles, following design.md:
> - grouped by problem / one long timeline
> - dense / spacious
> - normal text / extra-large text for older eyes
>
> Plus 3–4 Chinese wordings of the stopping-rule question (症状好转后，这个药还要继续吃吗？吃多久？). I pick the one that sounds most like how my mom would say it.

## 4. Timeline screen (4–6 layouts)
Only after 1–3 are settled, since by then I know what the timeline needs to show.

## Result
Four review sessions instead of fifty chat turns.