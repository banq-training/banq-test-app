# Workshop Website Kit

Original workshop CSS, small helper scripts, original animated artwork, six tested category
blueprints plus three tested own-idea patterns (a Request Tracker, a Team Dashboard and a Lab
Chase game), fictional sample data, and three owner-approved additions: the Apache ECharts chart
library, three.js for the Lab Chase game, and a public-domain base map of Princeton. No Novo name, logo, proprietary imagery,
corporate stylesheet, or corporate font is included. The skill copies the chosen blueprint and
kit into `site/` only after the learner picks a category; the source template never ships a
finished site.

## File Contract

| Kit file | Learner destination | Purpose |
| --- | --- | --- |
| [css/workshop.css](css/workshop.css) | `site/css/workshop.css` | Themes, header, board, cards, calendar, sticky notes, weather, tabs, progress, charts, toast, motion |
| [js/workshop.js](js/workshop.js) | `site/js/workshop.js` | `store`, `getJSON`, `loadJSON`, `useColumns`, safe `el`, `addButton`, `enableBoard`, `toast`, `flash`, `newId`, and `preview` (the Website preview's one message channel) |
| [js/workshop-charts.js](js/workshop-charts.js) | `site/js/workshop-charts.js` | `Workshop.chart(box, option)`: ECharts in the page's colors and font, resizing, calm motion, a note instead of a broken 3D chart; `chartColors`, `can3D`, `stage3D` |
| [js/workshop-chat.js](js/workshop-chat.js) | `site/js/workshop-chat.js` | `Workshop.addChat()`: an "Ask my page" bubble that asks the Website preview, never the network |
| [js/workshop-photo.js](js/workshop-photo.js) | `site/js/workshop-photo.js` | `Workshop.photo`: repaint a photo and save it to the gallery through the Website preview |
| [js/vendor/](js/vendor/) | `site/js/vendor/` | Apache ECharts 6.1.0 and ECharts GL 2.1.0, minified, with [their licences](js/vendor/CHART-LICENSES.md) copied to `site/CHART-LICENSES.md` |
| [art/](art/) | `site/art/` | Original animated SVGs: nine header illustrations and one icon per weekday |
| `blueprints/<category>/index.html` | `site/index.html` | Tested self-contained page for the chosen category |
| `blueprints/tracker/`, `blueprints/dashboard/`, `blueprints/game/` | `site/index.html` or `site/ideas/<name>/` | Tested own-idea patterns; never offered in the first question |
| [game/](game/) | `site/js/vendor/three.module.js`, `site/js/vendor/three.core.js`, `site/THREE-LICENSE.md` | three.js 0.186.1 (MIT), copied only for the Lab Chase game |
| `blueprints/<category>/data/*.json` | `site/data/*.json` | Sample entries; the page's pretend API |
| `blueprints/photo/gallery/` | `site/gallery/` | Six fictional sample photos for the Photo Studio |
| [fonts/source-sans-3-latin.woff2](fonts/source-sans-3-latin.woff2) | `site/fonts/source-sans-3-latin.woff2` | Local, open-source variable font, Latin subset (28,740 bytes) |
| [fonts/OFL.txt](fonts/OFL.txt) | `site/FONT-LICENSE.md` | Retained font license; Markdown is not published by the static app |
| [starters.json](starters.json) | Summaries, checks, and idea menus | The category list, each starter's `try_it` line and manual check, per-category `later_ideas`, the shared `any_page_ideas`, the `own_idea` summary, and the `idea_patterns` for own ideas |

Neither the CSS, the scripts, nor the art makes external requests; the chat bubble and the photo
studio only post messages to the Website preview, which signs in as the workshop identity. The
only internet access is the Weather blueprint's calls to Open-Meteo (forecast, city search, and
the past year's daily temperatures for the 3D chart), which the owner approved; its free tier is
for non-commercial use, and the page falls back to local sample weather and climate when blocked.
All palettes are light: Fresh mint (`green`, default), Sky blue (`blue`), or Soft coral (`coral`)
via the body's `data-theme`. The editor's dark theme does not change the website.

The artwork is original to this workshop: hand-written SVG shapes with CSS animation inside
each file, no scripts or external links, and no third-party license. Every file stops moving
when the visitor asks for reduced motion. Together they stay below 24 KiB.

The font is [Source Sans 3 from Google Fonts](https://github.com/google/fonts/tree/main/ofl/sourcesans3),
downloaded unchanged on 2026-09-22 as [the official Latin WOFF2 subset](https://fonts.gstatic.com/s/sourcesans3/v19/nwpStKy2OAdR1K-IwhWudF-R3w8aZQ.woff2)
and distributed under the included SIL Open Font License. SHA-256:
`7a19a7027e125257d310c6dbd78ae3a30b5ea1e3794d60b12bb28227a003bfda`.
Retain its license when copying it. Do not silently download more fonts during a session.

## Chart Library

The owner approved [Apache ECharts](https://echarts.apache.org) for the workshop on
19 October 2026, with [ECharts GL](https://github.com/ecomfe/echarts-gl) for 3D. Both came from
the npm packages `echarts@6.1.0` and `echarts-gl@2.1.0` through the approved package feed on that
day; their licences, and those of the parts they bundle (ZRender, d3.js, ClayGL), are in
[CHART-LICENSES.md](js/vendor/CHART-LICENSES.md).

- `echarts.min.js` is unchanged. SHA-256:
  `b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0`.
- `echarts-gl.min.js` has one patched function. ClayGL turned short size expressions such as
  `expr(width * 1.0 / 4)` into code with `new Function`, which the Website preview's
  Content-Security-Policy rightly blocks, so 3D failed with "Invalid expression". The function
  `cl` now reads those expressions with a small parser and no eval, marked
  `workshop patch: no eval`. Original SHA-256:
  `d6d60f2165ce3eb1ea360ef62e8490835e0ae2c1e0c1788a772fff918e350842`; patched:
  `8bf79e1be5543678c986fbb43f61662df46c4494b6c1ee8c6cc2a79217a35f53`. Reapply the patch when
  updating the library, and keep the preview's policy strict rather than adding `unsafe-eval`.

Charts are added with `/add-chart`, whose [tested recipes](../../add-chart/recipes/) draw from a
page's own data. Browsers without 3D get a short note in place of a 3D chart.

## 3D Game Library

The owner approved [three.js](https://threejs.org) for the Lab Chase game on 20 October 2026.
`three.module.js` and `three.core.js` came unchanged from the npm package `three@0.186.1` through
the approved package feed on that day, with the MIT licence in [game/THREE-LICENSE.md](game/THREE-LICENSE.md).
Neither file uses `eval` or `new Function`, so the page runs under the Website preview's strict
Content-Security-Policy; the page loads them with a relative `import`. They stay out of `js/`
so the other pages do not carry two megabytes they never use.

- `three.module.js` SHA-256: `9052042d676cb0fdc1ddfefe193053f34b7ac0513a616fdac4535d49987812ea`
- `three.core.js` SHA-256: `9edde002b066a9a05676a6127f67735b62baf399bdea529f2f7e31657da769e6`

## Map and Picture Sources

- The Princeton base map (`blueprints/map/data/map.json`) was built on 19 October 2026 from the
  U.S. Census Bureau's TIGER/Line data through TIGERweb, a public-domain U.S. Government work:
  town boundaries, the university campus, lakes and streams, roads, and railways, clipped to the
  area around the places, simplified, and rounded. It is not for navigation.
- Each of the 18 places in `blueprints/map/data/places.json` has a short original description
  and a `source` link to the official page (or an archived copy of it) that supports it, checked
  on 19 October 2026. Private homes are left out.
- The six Photo Studio samples are fictional pictures made with the workshop picture model
  (FLUX 1.1 pro) on 19 October 2026, with no people, text, logos, or brands, and shrunk to
  800 pixels.

The shared CSS stays below 16 KiB and the font below 40 KiB. Apart from the approved chart
library, no third-party JavaScript library, framework, CDN, tracking script, image service, or
animation service is bundled. The learner-written page has a suggested 100 KiB budget before
these assets. Keep the kit's own code readable, not minified. The Website preview panel reads the
files directly; no build or server is needed.

## Presenter Check

Run `/create-website` in a fresh Codespace. Verify it asks only which website to make (six
starters and My own idea), then builds immediately with the repository name, opens the preview,
and hands over with the starter's `try_it` line. Press + to add, drag, and remove in each
category; switch the calendar views; add a city on the Weather page and see it rise in the 3D
chart; filter the Princeton Map and switch to 3D; repaint a sample in the Photo Studio and save
it. Ask for a changed heading and verify the panel updates by itself with added entries kept.
Rename a Project Planner column and verify the board follows without losing saved cards.
Remove every entry and reload: each starter's examples must come back by themselves and
reproduce its `manual_check`. Check narrow and desktop widths. Recorded observations must not be
invented.
