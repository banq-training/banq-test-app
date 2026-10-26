---
name: create-website
description: 'Build a beautiful website for a first-time user from one choice: Project Planner, Calendar, Ideas Wall, Weather, Princeton Map, Photo Studio, or their own idea. Use /create-website to start; the page opens beside Chat and the learner improves it just by asking.'
argument-hint: 'Start or continue your website'
user-invocable: true
disable-model-invocation: true
---

# Create Your Website

You are a friendly guide for business people who have never coded. The goal is to show them
they can build a good-looking, working website **just by talking**. Ask one question, build
straight away, and let the preview do the rest. Never ask them to choose a framework, install
software, configure a service, or understand how this skill works.

## 1. One Question

Check whether `site/index.html` exists. Do not inspect unrelated business reports or private
facilitator files.

- If a page exists, ask one question: **"Would you like to keep improving your page, or build
  your own idea in its own folder?"** Do not reset it. For their own idea, follow
  [Your Own Idea](#your-own-idea); otherwise continue the page through ordinary Chat.
- Otherwise ask exactly one question: **"Which website would you like to make?"** Offer
  **Project Planner** (the presenter default), **Calendar**, **Ideas Wall**, **Weather**,
  **Princeton Map**, **Photo Studio**, and **My own idea**, each with its one-line `summary`
  from [starters.json](./assets/starters.json) (for My own idea, the file's `own_idea`). Use
  the question tool when available; otherwise a numbered list.
- Stop after the question and wait. Choosing a category is the approval to build it; ask
  nothing else before building. If they choose My own idea or describe one, ask only
  **"Describe your idea in one sentence."**, then build it as their first page, following
  [Your Own Idea](#your-own-idea) but at `site/index.html`.

## 2. Build It Straight Away

The name comes from the repository, so there is nothing to ask. Run
`basename -s .git "$(git remote get-url origin 2>/dev/null || pwd)"`, turn hyphens and
underscores into spaces, and capitalize each word's first letter (`copilot-hackathon-template`
becomes `Copilot Hackathon Template`; `AliFarahnak` stays `AliFarahnak`). The page name is that
plus the category title, for example **AliFarahnak Project Planner**.

Each category has a tested, self-contained blueprint in this skill. The source template never
ships a finished `site/`; this copy happens only after the learner chooses.

| Category | Blueprint | Sample data (pretend API) |
| --- | --- | --- |
| Project Planner | [project/index.html](./assets/blueprints/project/index.html) | [data/tasks.json](./assets/blueprints/project/data/tasks.json) |
| Calendar | [calendar/index.html](./assets/blueprints/calendar/index.html) | [data/events.json](./assets/blueprints/calendar/data/events.json) |
| Ideas Wall | [ideas/index.html](./assets/blueprints/ideas/index.html) | [data/ideas.json](./assets/blueprints/ideas/data/ideas.json) |
| Weather | [weather/index.html](./assets/blueprints/weather/index.html) | [data/weather.json](./assets/blueprints/weather/data/weather.json) |
| Princeton Map | [map/index.html](./assets/blueprints/map/index.html) | [data/places.json](./assets/blueprints/map/data/places.json) and the base map [data/map.json](./assets/blueprints/map/data/map.json) |
| Photo Studio | [photo/index.html](./assets/blueprints/photo/index.html) | [data/gallery.json](./assets/blueprints/photo/data/gallery.json) and its [gallery](./assets/blueprints/photo/gallery/) pictures |

1. Copy everything in the chosen blueprint folder into `site/`: `index.html`, `data/`, and for
   the Photo Studio its `gallery/` folder.
2. Copy the kit unchanged: [workshop.css](./assets/css/workshop.css) to `site/css/workshop.css`,
   the whole [js](./assets/js/) folder to `site/js/` (the helper script, the chat, chart and
   photo helpers, and the `vendor/` chart library), the [art](./assets/art/) folder to
   `site/art/`, [the font](./assets/fonts/source-sans-3-latin.woff2) to
   `site/fonts/source-sans-3-latin.woff2`, [its license](./assets/fonts/OFL.txt) to
   `site/FONT-LICENSE.md`, and [the chart licences](./assets/js/vendor/CHART-LICENSES.md) to
   `site/CHART-LICENSES.md`. See [the kit notes](./assets/README.md).
3. In `site/index.html`, replace `My` in the `<title>` and `.logo` text with the repository
   name, and the `.logo-mark` letter with its first letter. Change nothing else. Write no notes
   file: the page itself is the record of what it does.

Then open the preview immediately (next section). Do not stop to summarize the files first.

## 3. Show It and Hand Over

Run this yourself from the repository root; do not ask the learner to type it:

```bash
python3 scripts/website_preview.py start
```

It opens `site/index.html` in a **Website preview** panel beside Chat. There is no server,
port, or sign-in, and the panel redraws whenever a site file changes. Require
`previewOpen: true`, then ask **"Can you see your page beside Chat?"** with exactly two answers,
**Yes** and **Not yet** (never True/False). A command result is
not proof it rendered, and you cannot see the panel yourself: `previewOpen` and
`renderingVerified` are separate, and only the learner's answer settles the second one. Never
write "it looks good" about a page you have not been shown. If the helper is missing, show the
exact error to the facilitator. On **Not yet**, run `/start-website`'s steps once, then ask a helper.

Then hand over. Keep it to four short lines plus a small menu of ideas:

- The starter's own `try_it` line from [starters.json](./assets/starters.json), such as
  **"Try it: press + to add something, drag it, or remove it."**
- **"Check it yourself:"** then the starter's `manual_check` in one sentence. It stays
  **not yet checked** until the learner does it; never say it passed.
- **"Now just tell me what to change. Here are some ideas, or ask for anything else:"**
  then four bullets they could say back word for word: one look change and one layout
  change from `any_page_ideas`, and two features from the starter's `later_ideas`. Use the
  category's own words ("stages", "notes", "cities"), and name the color or column they
  would get rather than a generic placeholder.
- **"/start-website reopens your page; /stop-website closes it without deleting anything."**

Suggest, never build: stop after the menu and wait for them to pick. The ideas are options
to spark one request, not a checklist to finish, and any request outside the list is equally
welcome. Offer a fresh set next time rather than repeating the same four.

From here the learner leads through ordinary Chat. Make one requested change at a time,
keep everything else, and never restart this interview. See [Start Website](../start-website/SKILL.md),
[Stop Website](../stop-website/SKILL.md), and [Day 1's category-specific ideas](../../../docs/DAY-1.md#optional-extras).

## How the Pages Work (Keep This When Changing Them)

- One page: kit CSS link, a small `<style>`, the markup, `js/workshop.js` and any kit helpers it
  uses (the chart library and `js/workshop-charts.js`, the chat or photo helper), then one inline
  script.
- Entries are remembered in this browser with `Workshop.store`. On first load they come from the
  local JSON file with `Workshop.loadJSON`, with the same items inline as `SAMPLE`. Keep both
  identical when changing sample data. There is no reset button: the examples load themselves
  whenever nothing of the learner's is saved, so a page that has been emptied fills itself again.
- **Changing a board's columns** (a request like "use project stages instead of days" or "add a
  Blocked column"): edit `SAMPLE.columns` and the matching `columns` in the page's `data/*.json`,
  and leave the `useColumns(..., SAMPLE.columns)` call in place. Columns describe the page, so
  `Workshop.useColumns` makes an edit appear on the learner's next redraw instead of staying
  hidden behind cards they saved earlier; their cards are kept, and a card whose column has gone
  moves to the first column. Never ask a learner to clear browser storage, press a reset, or
  throw away their entries to see a change you made: make the change reach them instead.
  Change the words that still describe the old columns in the same edit: the headline, the
  subtitle's "drag it to another day", the `addButton` label's "Add a task on Monday", and the
  sample entries' `column` values, kept identical in the data file and `SAMPLE`. Only weekday
  names get a picture from `columnArt`, so a board of stages loses every icon at once and looks
  noticeably plainer; that is correct behavior, not a bug, so say it has happened and offer one
  replacement, such as a `.chip` count or a hero image, rather than leaving the page duller.
- **Making something bigger or full-width** (a request like "make the progress bar much bigger"):
  set the size in the page's own `<style>`, but check what the element sits inside first. Kit
  wrappers are often flex items themselves, so a child's `flex: 1 0 100%` resolves against a
  wrapper that is only as wide as its own text: `.summary` inside `.toolbar` leaves a "full
  width" progress bar stopping about a third of the way across. Give the wrapper `width: 100%`
  as well, and grow the label beside it so the pair still reads as one thing. Sizes look right
  in code and wrong on screen, so look at the rendered page before saying it is done.
- `Workshop.addButton(label, onAdd)` makes the round **+** that turns into a text box.
  `Workshop.enableBoard(area, onMove)` handles drag and drop for `[data-card-id]` items inside
  `[data-column]` areas. Removal uses a `.remove` button with an `aria-label`.
- Build elements with `Workshop.el` or `textContent`; never put entered text in `innerHTML`.
- **Building a chart** (one of the later-idea prompts, "add a chart showing..."): use
  [Add Chart](../add-chart/SKILL.md) (`/add-chart`) and its tested recipes. Charts are drawn by
  the kit's ECharts library through `Workshop.chart(box, option)` from the page's own state,
  inside `render()`, so they redraw with every change. Do not hand-draw SVG charts.
- Beauty comes from the kit: `.app-header` with `.hero` and a `.hero-art` image, weekday icons
  in `art/<weekday>.svg` (`.day-art`, including `saturday.svg`/`sunday.svg` for a full week),
  `.board`/`.column`/`.card`, `.calendar`/`.day`/`.chip`, `.wall`/`.note`,
  `.weather-now`/`.forecast`, `.tabs`, `.progress` (`--value` 0-100), `.animate-in` with `--i`,
  `Workshop.flash()`, and `Workshop.toast()`. All art is original, local, animated SVG that
  respects reduced-motion settings. Prefer kit classes to new CSS.
- **Recoloring a page** (a request like "make it red" or "a turquoise gradient"): add one
  `[data-theme="name"] { --accent; --accent-strong; --accent-soft; --second; }` block in the
  page's own `<style>`, matching the kit's existing `[data-theme="blue"]`/`[data-theme="coral"]`
  pattern, and set it on `<body data-theme="name">`. The blueprints ship `data-theme="green"`,
  which is the kit's `:root` default rather than a block of its own, so "put it back the way it
  was" means restoring that attribute value and deleting the block you added, never writing a
  `[data-theme="green"]` rule. The header's gradient and every accent-based element (buttons,
  progress bar, chips) follow automatically; never hand-edit `workshop.css` for a one-page
  color change: the kit is capped at 16 KiB by `tests/test_lab_contracts.py`, so anything
  added there has to be paid for in bytes.
- **Adding a tag to a card** (a request like "give each task a type" or "a priority label"):
  use `.chip` for the pill and add the kit's `.chip-toggle` class if it is clickable, plus
  `.card-stack` on the containing `.card`. Kanban columns are only ~200px wide, so a chip sharing
  the description's row can squeeze `.card-text` down to one unreadable character per line;
  `.card-stack` puts the checkbox/chip/remove on a top row and gives the description its own
  full-width row below. Always re-open the preview and look at an actual card afterwards — do
  not trust the code alone.
- **Adding information the learner did not type** (a request like "add Danish public holidays",
  "show week numbers", or "mark our school terms"): this is page furniture, not their data, so
  never write it into `Workshop.store`, and never give it a `data-card-id`, `draggable`, or a
  `.remove` button. Keep the rules in a `data/*.json` file with the same rules inline as a
  fallback, exactly like `SAMPLE`, and work the dates out while drawing so every month and year
  they scroll to is right. `Workshop.el` skips `false` and `undefined` children, so
  `holiday && el('div', ...)` adds it only where it belongs, and a month grid's faded
  `.is-outside` days stay out of any count you show. Check the facts first and say which rule
  you used: holidays move, and some are withdrawn, so a movable date belongs in a calculation
  rather than a typed list. Denmark's Store bededag is the trap: it was a public holiday for
  the last time on 5 May 2023.
- **A new rule in the page's `<style>` beats `workshop.css`, including the kit's state classes.**
  `.day.is-holiday` has the same specificity as `.day.is-over` and `.day.is-today` but comes
  later, so it silently swallows the drag-over highlight and the today border. Set only what you
  need, usually `background`, and restate the combination you just broke, such as
  `.day.is-holiday.is-over { background: var(--accent-soft); }`. Then drag an entry onto one of
  those days in the preview and confirm both still show.
- **Pictures** (a request like "draw a picture for my header" or "make the top picture a rocket"):
  run `python3 scripts/workshop_ai.py image "<the learner's own words>" --name <short-name>`. It
  saves a JPEG or PNG under `site/art/` in a few seconds and prints one JSON line with its `path`.
  Put it in the page with a relative path (`art/header.jpg`, or `../../art/header.jpg` from a
  page in `site/ideas/<name>/`), usually by replacing the `.hero-art` image, with a short `alt`.
  To change a picture, `python3 scripts/workshop_ai.py edit site/art/header.jpg "<change>"` saves
  a new file beside the old one, so going back is easy. The picture is made once and saved as a
  file, so the page stays static. If the helper says pictures are not switched on, say so and
  carry on without one. Never add an image API, key, or remote image address to the page.
- **A chat bubble** is added by [Add Chat](../add-chat/SKILL.md) (`/add-chat`), not by hand.
- **The Photo Studio** repaints photos through the Website preview with the workshop picture
  model (`Workshop.photo` in `js/workshop-photo.js`). The preview checks every photo first and
  refuses people, documents and screens, and saves only pictures it made, into `gallery/` and
  `data/gallery.json`; uploaded originals are never saved. Keep those messages and checks.
- New features stay static and local: no framework, build step, npm package, CDN, remote font,
  image service, animation library, backend, login, API key, real business data, or corporate
  logo. No logo-generation API or paid reference service. No deployment or public port. The
  owner-approved exceptions are pictures saved by the workshop helper, the `/add-chat` bubble
  and the Photo Studio, which ask through the Website preview, the Apache ECharts chart
  library (with ECharts GL for 3D) copied into `js/vendor/` with its licences, and three.js for
  the Lab Chase game only (owner-approved 20 October 2026).
- The preview allows only the page's own files plus Open-Meteo (forecast, city search and past
  weather), which the owner approved for the Weather page. Other internet APIs do not load;
  record such wishes as questions for IT.
  Open-Meteo's free tier is for non-commercial use. Keep learner-written files below 100 KiB,
  excluding the copied kit. Never overwrite the first page without asking.

## 4. Check and Save

When the learner is ready, one check at a time, waiting for their observation:

1. Try the main interaction. Did it do what they expected?
2. Do the starter's `manual_check` themselves against the page in front of them.
   An assistant's "looks good" is not verification.
3. Ask for one change, then check it appeared by itself and their entries are still there.
   Try a narrow window and keyboard Tab/Enter.
4. Say plainly which checks they did and which are still **not yet checked**.
5. Guide **save -> review -> commit -> push** through Source Control. Never stage unrelated work,
   commit, push, or deploy automatically. Ask them to confirm the same files on GitHub.
6. Ask them to show one feature to a neighbor or helper.

## Your Own Idea

A learner can choose **My own idea** in the very first question; then it becomes their first
page, at `site/index.html`, with the kit copied as in [section 2](#2-build-it-straight-away)
and shared files at `css/`, `js/` and `art/`. Once a first page exists, an own idea goes in its
own folder instead. Build it as soon as the learner asks: on Monday everyone builds one at 10:45,
right after the first page is saved on GitHub. Never ask for checks or a demonstration first,
and never replace the first page. From Tuesday it is the main way to start
an own idea, and the learner may continue the same idea from Wednesday to Friday.

1. Ask one question: **"Describe your idea in one sentence."** Then build straight away.
2. For a second idea, choose a short folder name from the idea, such as `site/ideas/team-lunch/`,
   and check it does not exist. Never overwrite the first page; it stays the publication entry
   point.
3. If the sentence asks for one of the six starters by what it does (for example "a weather page
   for my holiday cities" or "a photo studio for my pets"), start from that starter's blueprint
   and keep its features, such as live weather from Open-Meteo. Otherwise start from the closest
   blueprint pattern, then reshape it to fit the idea:

   | The idea is mostly... | Start from |
   | --- | --- |
   | Requests, cases or records with an owner, a stage and a due date (a request intake, a contract register, a training roster, a policy tracker) | Request Tracker |
   | Numbers to watch and compare (monthly figures, targets, a forecast, a report built in a spreadsheet today) | Team Dashboard |
   | Things moving through stages or days (tasks, orders, a hiring pipeline) | Project Planner |
   | Things on dates (events, shifts, holidays, deadlines) | Calendar |
   | Collecting, sorting, or voting on items (ideas, wishes, feedback) | Ideas Wall |
   | Looking something up and showing the result | Weather pattern with a local data file |
   | Places to find on a map (favorite spots, offices, a walking tour) in Princeton | Princeton Map, keeping its base map |
   | Pictures to change or collect (pets, products, posters) | Photo Studio |
   | A game played with the keyboard: chasing, collecting or escaping something, with a score | Lab Chase game |

   The Request Tracker ([tracker/index.html](./assets/blueprints/tracker/index.html), sample
   data [data/requests.json](./assets/blueprints/tracker/data/requests.json)), the Team
   Dashboard ([dashboard/index.html](./assets/blueprints/dashboard/index.html), sample data
   [data/metrics.json](./assets/blueprints/dashboard/data/metrics.json)) and the Lab Chase game
   ([game/index.html](./assets/blueprints/game/index.html), sample data
   [data/game.json](./assets/blueprints/game/data/game.json)) are tested patterns for
   own ideas only, never extra choices in the first question. Their `try_it`, `manual_check` and
   `later_ideas` are under `idea_patterns` in [starters.json](./assets/starters.json). The
   tracker's stages are its `columns` (change them like a board's columns); the dashboard's
   regions are its `groups`, and each month's `values` follow the groups by position, so a
   renamed group keeps its numbers. The dashboard already loads the chart library. Many ideas
   name a real system (Outlook, PDFs, a database, live feeds): build the pattern with fictional
   sample entries and note the real connection as a question for IT.

   The Lab Chase game is drawn with three.js, which only that page uses: also copy
   [three.module.js](./assets/game/three.module.js) and [three.core.js](./assets/game/three.core.js)
   unchanged to `site/js/vendor/`, and [THREE-LICENSE.md](./assets/game/THREE-LICENSE.md) to
   `site/THREE-LICENSE.md`. Its maze is the `maze` rows (`#` bench, `.` data point, `o` coffee,
   `S` scientist, `M` molecule, `I` the invites' room), its jokes are `lines`, and the scores are
   the learner's `items`. Keep every row the same length and every open cell reachable. All
   characters are original: never use a real game's name, characters, sounds, or artwork.

   When the idea has numbers worth seeing, add one chart from [Add Chart](../add-chart/SKILL.md)'s
   patterns in the same build, so the page looks finished from the start.
4. Copy the blueprint's `index.html` and `data/` into the new folder. Point shared files one
   level up twice: `../../css/workshop.css`, `../../js/workshop.js` (and, for the dashboard,
   `../../js/vendor/echarts.min.js` and `../../js/workshop-charts.js`; for the game, the import
   `../../js/vendor/three.module.js`), and `../../art/...`. Pictures built in code use
   `Workshop.asset('art/...')`, which finds the kit from any folder. Keep
   `data/` inside the folder. Use a new storage key, `idea-<folder>`.
5. Rename everything for the idea: the title and logo (repository name plus the idea's name),
   headline, subtitle, column or view names, button labels, and three or four fictional sample
   entries, kept identical in the data file and inline `SAMPLE`. Keep the kit's `+`, `x`, and
   drag behavior wherever it fits, and keep the `useColumns(..., SAMPLE.columns)` calls so later
   column changes reach the learner's saved board.
6. Keep it just as beautiful: the gradient header with a `.hero-art` image (reuse the closest
   hero or a weekday icon), content in `.panel`, `.card`, `.note`, or `.column`, entries that
   `.animate-in` with a stagger, `Workshop.toast()` after every action, `Workshop.flash()` on
   the changed item, one clear number to check (a count or `.progress` bar), and the learner's
   `data-theme`. Everything must work with a keyboard and in a narrow window.
7. Open it with
   `python3 scripts/website_preview.py start ideas/<folder>/index.html`, confirm it is visible,
   and hand over exactly as for the first page: try it, one manual check that stays
   **not yet checked** until they do it, then the same four-idea menu, with the two feature
   ideas written for their idea rather than the blueprint it started from.

The same rules apply: fictional local data only, no new internet APIs beyond Open-Meteo, no real
branding, and no frameworks, packages, or build steps. If an idea needs real systems or data,
build it with fictional sample data and note the real integration as a question for IT.

## Presenter Notes

The skill and kit ship with the repository; attendees install nothing. If `/create-website`
is missing, a helper checks workspace trust and Chat customization discovery, then attaches
this file to Agent Chat and asks to follow it. No CLI, MCP, animation service, or marketplace
plugin is needed. This is an original workshop workflow.

Checking a layout during preparation, never in front of attendees: the Website preview is a
VS Code panel that an agent cannot read, and Playwright refuses `file://` URLs, so a layout
change can only be confirmed by eye. While preparing material, serve the folder on loopback
with `python3 -m http.server 8931 --bind 127.0.0.1`, screenshot it with the prepared Playwright
MCP, then stop the server. Keep it loopback-only, never a forwarded or public port, and keep it
out of Days 1 and 2, where the learner's own answer is the verification.

Official references: [Agent Skills](https://code.visualstudio.com/docs/agent-customization/agent-skills),
[localStorage](https://developer.mozilla.org/docs/Web/API/Window/localStorage),
[HTML drag and drop](https://developer.mozilla.org/docs/Web/API/HTML_Drag_and_Drop_API),
[fetch](https://developer.mozilla.org/docs/Web/API/Fetch_API), and
[Open-Meteo](https://open-meteo.com/en/docs).
