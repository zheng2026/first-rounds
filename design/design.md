# First Rounds — design.md (locked 2026-10-30 03:10, Jade)

**Choice:** `mood=minimal  type=rounded  density=spacious  accent=indigo` (from design/look.html).
Every UI screen follows this file. Don't invent new colors, fonts, sizes or spacing. If something is missing here, add it here first.

Later, not for the hackathon: `mood=glass` with any accent — kept as a theme option in look.html, do not build it now.

## Color
| token | value | use |
|---|---|---|
| `--bg` | `#ffffff` | page background |
| `--surface` | `#fafafa` | cards, panels |
| `--line` | `rgba(0,0,0,.05)` | card borders (near-transparent) |
| `--line-strong` | `#cfcfcf` | timeline rail, dividers that must be seen |
| `--ink` | `#111111` | primary text |
| `--ink-2` | `#555555` | secondary text (dates, quotes) |
| `--ink-3` | `#888888` | tertiary (labels, meta, inactive tabs) |
| `--accent` | `#3b5bdb` | indigo: active tab underline, timeline dots, medicine chips, primary button, source-quote mark |
| `--accent-soft` | `#e3e8fb` | Today panel background, medicine chip background |
| `--accent-ink` | `#22378f` | text on accent-soft, active tab text |
| `--question` | `#8a6d00` on `#fff8dc` with border `#e3cf7a` | open-question chips |
| `--warn` | `#b4531f` with border `#e6c4b0` | "worse:" chips |
| `--ok` | `#2f7d4f` | confirmations |
| emergency | `#b3261e` text on `#fdecea`, border `#b3261e` | the warning block only; nowhere else |

No shadows (`--card-shadow: none`). Depth comes from surface vs bg, not from shadow.

## Type
- Family: **Nunito** (Google Fonts, weights 400/600/700), fallback `system-ui, sans-serif`. One family for everything; display = body family at weight 700.
- Sizes: body `16px`, small `13.5px` (dates, chips, meta, tab labels), large `20px` (screen titles, problem headings). Line-height `1.5`.
- Weights: headings 700, emphasis 600, body 400.
- Chinese text: same stack; let the system CJK fallback render it. Never shrink Chinese below body size.

## Space and shape
- Spacing scale: `--sp-xs 6px`, `--sp-sm 10px`, `--sp 16px`, `--sp-lg 24px`; gap between timeline entries `14px`.
- Screen padding: `16px` sides, `24px` bottom.
- Corner radius: cards and panels `20px`; buttons and chips pill (`999px`); inputs `12px`.
- Borders: 1px `--line` on cards; no border on chips except the semantic ones above.
- Phone-first: content width `min(420px, 100%)`, centered on wide screens.

## Components (as built in look.html)
**Top bar** — brand "First Rounds" 20px/700 + small grey "Mom"; tabs below with a 2px accent underline on the active one.

**Today panel** — `--accent-soft` background, 20px radius, 10px/16px padding; heading 13.5px/600 in `--accent-ink` ("Today · 3 to do"); bullet list in 13.5px `--ink-2`.

**Timeline entry** — rail 2px `--line-strong` at left; 12px dot: accent ring on white for normal, dashed grey ring for rough dates, filled accent for future/planned. Card: surface, 1px `--line`, 20px radius, 10px/16px padding. Inside: date line (13.5px, `--ink-2` bold + precision word in `--ink-3`), the "what" in body size, chips row, then the source link.

**Source link** — `❝ from note 10/29` in 13.5px `--ink-3`, quote mark in accent. Tap toggles the quoted sentence: 3px accent left bar, italic 13.5px `--ink-2`. Every entry has one. This is the trust rule made visible; never drop it.

**Chips** — pill, 13.5px, 2px/9px padding. Medicine: accent border + accent-soft bg + accent-ink text; stopped = dashed border. Question: yellow set. Worse: warn set. Neutral: `rgba(0,0,0,.08)` border.

**Stop-check card** — a timeline card with a 4px inset accent bar on the left, heading "Stop-check" 13.5px/600 accent-ink, the doctor's rule in body size, and one pill button "Tell Mom" (accent bg, white text, 13.5px/600).

**Primary button / FAB** — accent bg, white 600 text, pill, 10px/18px padding; one per screen ("+ After the call").

**Emergency block** — appears above everything else on the screen when flagged. `#fdecea` bg, 1px `#b3261e` border, 20px radius; title "Possible warning sign" 16px/700 `#b3261e`; the template message in body size; sources line in 13.5px. No icon, no animation.

## Motion and access
- Transitions ≤ 250ms on color/radius only; none under `prefers-reduced-motion`.
- Focus ring: 3px accent, 2px offset. Tap targets ≥ 44px.
- Contrast: all text pairs above are ≥ 4.5:1 on their backgrounds.

## Doctor card (locked 2026-10-30 05:20, Jade)
- Layout grouped (病史 / 已做的检查 / 现在在吃的药 / 有帮助·会加重 / 想问医生的问题), density spacious, Chinese by default with English toggle, text size toggle (normal / large for older eyes) kept as a user setting.
- Stopping-rule question, wording A: 症状好转后，这个药还要继续吃吗？吃多久？ — one per medicine still being taken; a stopped medicine with a recorded rule gets the stop-check question instead.
- Review toggles (layout, density, wording) are hidden; `?review=1` shows them.
