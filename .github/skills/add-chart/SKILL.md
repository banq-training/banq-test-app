---
name: add-chart
description: 'Add a beautiful chart, flat or 3D, to a learner''s workshop website, drawn from what the page already holds and redrawn whenever it changes. Uses the ECharts library in the website kit. Use /add-chart once a page exists.'
argument-hint: 'Optional idea page, such as team-lunch'
user-invocable: true
disable-model-invocation: true
---

# Add a Chart

Give the learner's page a chart drawn from its own entries, so it changes by itself when they
add, tick, move or remove something. Charts use Apache ECharts, and ECharts GL for 3D: local
files in the website kit that the owner approved for the workshop. Never add a CDN, package,
build step, API key, or a new internet address, and do not edit the preview helper.

1. Find the page. Default to `site/index.html`; an idea name such as `team-lunch` means
   `site/ideas/team-lunch/index.html`. If it does not exist, say **"Let's create your website
   first with /create-website."** and stop.
2. Work out which starter it came from: the page's title and headline name it.
3. Ask exactly one question: **"Which chart would you like?"** Offer that starter's ideas from
   the table, each with its one-line description, using the question tool when available. For
   an own idea, offer three that fit its data from [Patterns for Own Ideas](#patterns-for-own-ideas),
   at least one of them 3D. Stop and wait: choosing is the approval to build.
4. Before touching the page, copy any kit file it lacks, unchanged:
   [echarts.min.js](../create-website/assets/js/vendor/echarts.min.js) and, for 3D,
   [echarts-gl.min.js](../create-website/assets/js/vendor/echarts-gl.min.js) to `site/js/vendor/`,
   [workshop-charts.js](../create-website/assets/js/workshop-charts.js) to `site/js/`, and
   [CHART-LICENSES.md](../create-website/assets/js/vendor/CHART-LICENSES.md) to
   `site/CHART-LICENSES.md`. The preview redraws as soon as the page changes, so the files must
   already be there.
5. Right after the page's `js/workshop.js` script tag, add whichever is missing, in this order:
   `js/vendor/echarts.min.js`, `js/vendor/echarts-gl.min.js` (3D only), `js/workshop-charts.js`.
   From `site/ideas/<name>/` the paths start with `../../`.
6. Open the chosen recipe. Add its markup where it says, add its function at the end of the
   page's own inline script, and call it where it says. Rename only what the page names
   differently, such as a renamed column list. Change nothing else on the page.
7. Run `python3 scripts/website_preview.py start` yourself (for an idea page add its path
   relative to `site/`) and require `previewOpen: true`.
8. Hand over in three short lines:
   - **"Scroll down: your <chart name> is drawn from your own <entries>."**
   - The recipe's **Check**, written as something to try with the page's numbers right now.
     Count its entries first: the learner may have added, ticked or removed some since it was
     made.
   - For 3D: **"Drag the chart to turn it."** Otherwise: **"Point at the chart to see the numbers."**

| Starter | Flat ideas | 3D idea |
| --- | --- | --- |
| Project Planner | **Tasks per day**: done and to-do bars for every column ([recipe](recipes/project-days.js)); **Progress gauge**: a big dial that fills as tasks are ticked ([recipe](recipes/project-gauge.js)) | **Week skyline**: a tower of tasks for each column, amber to do and green done ([recipe](recipes/project-skyline-3d.js)) |
| Calendar | **Busy days**: the month as tiles, darker when a day holds more notes ([recipe](recipes/calendar-busy-days.js)) | **Month in 3D**: a column for every day, as tall as its notes ([recipe](recipes/calendar-month-3d.js)) |
| Ideas Wall | **Idea bubbles**: every idea floats as a bubble you can drag ([recipe](recipes/ideas-bubbles.js)) | **Idea galaxy**: the ideas shine as named stars in a turning spiral ([recipe](recipes/ideas-galaxy-3d.js)) |
| Weather | **Next days**: highs and lows as warm and cool lines with a soft band ([recipe](recipes/weather-next-days.js)) | Already on the page: **Your cities through the year** |
| Princeton Map | **Places by type**: a flower whose petals grow with each type ([recipe](recipes/map-types-rose.js)); **How far from Palmer Square**: every place, nearest first ([recipe](recipes/map-distances.js)) | Already on the page: the **3D** map view |
| Photo Studio | Suggest the color cloud | **Color cloud**: the chosen photo's colors as dots in a red-green-blue cube ([recipe](recipes/photo-colours-3d.js)) |

## Patterns for Own Ideas

Draw from the page's own state, inside its `render()`, with `Workshop.chart(box, option)` and
the colors from `Workshop.chartColors()`; never fetch new data for a chart.

- A number for each group (tasks per stage, votes per idea): rounded bars, or a rose like
  [Places by type](recipes/map-types-rose.js).
- A share of a whole (done, budget used): a gauge like [Progress gauge](recipes/project-gauge.js).
- Something over days or dates: a smooth line with a soft area like [Next days](recipes/weather-next-days.js),
  or calendar tiles like [Busy days](recipes/calendar-busy-days.js).
- Two kinds of group and a number (stage and person, day and type): 3D bars on a dark stage
  like [Week skyline](recipes/project-skyline-3d.js), using `Workshop.stage3D()`.
- Names without numbers: bubbles like [Idea bubbles](recipes/ideas-bubbles.js) or a galaxy like
  [Idea galaxy](recipes/ideas-galaxy-3d.js).

## Rules That Keep Charts Working

- One `<div class="chart">` per chart, with a unique id and a height; add `chart-stage` for 3D.
- `Workshop.chart` redraws in place, follows the box's size, and calms motion for learners who
  ask for less. A 3D chart in a browser without 3D shows a short note: offer the flat idea then.
- Tooltips: a string template is safe; in a function formatter wrap typed text in
  `echarts.format.encodeHTML(...)`. Never use `innerHTML` for entered text.
- 3D charts set `zoomSensitivity: 0` through `Workshop.stage3D()`, so scrolling the page still
  scrolls. Keep that.
- Look at the result in the preview before saying it is done; a chart can be correct in code and
  cramped on screen. Prefer a taller box over smaller text.

Official references: [ECharts examples](https://echarts.apache.org/examples/en/index.html),
[ECharts option reference](https://echarts.apache.org/en/option.html),
[ECharts GL](https://github.com/ecomfe/echarts-gl), and
[Agent Skills](https://code.visualstudio.com/docs/agent-customization/agent-skills).
