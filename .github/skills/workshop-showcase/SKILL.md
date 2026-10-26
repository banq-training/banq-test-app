---
name: workshop-showcase
description: 'Play the scripted showcase of all nine workshop starter websites in the VS Code browser, about 30 seconds each, with a red pointer, captions, and a live chat question. WHEN: "demo all the templates", "show the starters", "showcase tour", "play the website demo", "show what they can build", "show only Weather and Lab Chase".'
argument-hint: 'Optional: only some pages, such as Weather and Lab Chase'
user-invocable: true
---

# Workshop showcase

Plays a fixed, tested demo of each starter website on the published showcase site. Every page
drives itself (red pointer, caption at the top, progress bar, a real chat answer at the end), so
your only job is to start each page, wait, and say one short line. Never click, read, or
screenshot the page yourself, and never improvise extra steps.

Site: `https://showcase.thankfulrock-bf005377.eastus.azurecontainerapps.io/`

Nothing is deployed when this runs: it only opens the already-published site.

## Steps

1. Open the site in the VS Code browser with the browser tool that opens a page
   (`openBrowserPage` or `open_browser_page`, url above), or reuse a page already shared in this
   chat. Tell the presenter in one line: "Make the browser panel big; it starts in 3 seconds."
2. For each row of the table, in order (or only the rows the presenter named), call the browser
   tool that runs Playwright code on that page (`runPlaywrightCode` or `run_playwright_code`) with
   `timeoutMs: 75000` and exactly this code, with PATH from the table:

   ```js
   await page.goto('https://showcase.thankfulrock-bf005377.eastus.azurecontainerapps.io/PATH?demo=1'); await page.waitForFunction(() => window.ShowcaseTour && window.ShowcaseTour.done, null, { timeout: 70000 }); return await page.evaluate(() => window.ShowcaseTour.summary)
   ```

   If the call returns a `deferredResultId`, call the same tool again with it until it ends.
   If no Playwright-code tool exists, open
   `https://showcase.thankfulrock-bf005377.eastus.azurecontainerapps.io/?tour=1` instead (it plays
   all nine pages by itself), say "Watch: nine websites, about 5 minutes", and stop.
   If no browser tool exists at all (a Codespace opened in a web browser has none), reply only:
   "Open this in a new browser tab; it plays all nine websites by itself, about 5 minutes:" and
   that link, then stop.
3. After each page, write only the **Say** line in chat, then go straight to the next page.
4. If a page fails or times out, say "Skipping that one" and continue. Mention it once at the end.
5. Finish with: "Nine websites, each started from one sentence to Copilot. Now you build one."

| # | Page | PATH | Say |
| - | ---- | ---- | --- |
| 1 | Project Planner | (empty) | Planner: add, tick, drag, a 3D week, and a chat that explains its own code. |
| 2 | Calendar | `ideas/calendar/` | Calendar: months, views, notes, the month in 3D, and a chat that knows the facts you write in knowledge.md. |
| 3 | Ideas Wall | `ideas/ideas/` | Ideas Wall: sticky notes you can reorder, shining in a 3D galaxy. |
| 4 | Weather | `ideas/weather/` | Weather: live forecasts for any city in the world. |
| 5 | Princeton Map | `ideas/map/` | Map: your own places, filters, and a 3D town. |
| 6 | Photo Studio | `ideas/photo/` | Photo Studio: pick a photo and a style; AI repaints it while you build. |
| 7 | Request Tracker | `ideas/tracker/` | Tracker: a form, stages, filters, and search. |
| 8 | Team Dashboard | `ideas/dashboard/` | Dashboard: live charts, filters, and a forecast slider. |
| 9 | Lab Chase game | `ideas/game/` | And a 3D game, from one sentence. |

The whole tour takes about 5 minutes.

## Plan B (no Copilot needed)

Open `https://showcase.thankfulrock-bf005377.eastus.azurecontainerapps.io/?tour=1` in any
browser: it plays all nine pages by itself, one after another. `?demo=1` on any page plays that
page once.

## Good to know

- Each page clears the showcase site's saved data in that browser before it plays, so every run
  looks the same.
- The chat answers live through the published site's managed identity. If a chat answer is slow
  or missing, the rest of the demo still plays.
- Photo Studio's **Make it** works only in the Codespace preview; its caption says so.
- The site needs the `keep-warm` container app to keep hosting awake this week.
- Source: private repo `agentic-dev-labs/workshop-showcase`, file `site/tour/tour.js`. A push to
  `main` republishes it in about 2 minutes.
