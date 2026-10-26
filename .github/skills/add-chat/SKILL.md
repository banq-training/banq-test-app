---
name: add-chat
description: 'Add an "Ask my page" chat bubble to a learner''s workshop website. It answers questions from what the page shows, the page''s own code, and a knowledge.md file of extra facts next to the page, using the workshop AI. Use /add-chat once a page exists.'
argument-hint: 'Optional idea page, such as team-lunch'
user-invocable: true
disable-model-invocation: true
---

# Add a Chat Bubble

Give the learner's page a small "Ask my page" assistant that answers in plain words. With every
question it reads three things, and nothing else:

1. **What the page shows:** its text, ticked boxes, values typed into fields, the numbers behind
   every chart (3D charts too), and the descriptions of its pictures.
2. **The page's own code:** its HTML, CSS and JavaScript, so it can explain how a button works.
3. **`knowledge.md` next to the page:** any extra facts the learner writes there, such as names,
   opening hours or answers to common questions. It may also give the chat a name or a tone.

The page holds no key or secret: the Website preview signs in as the workshop identity, and a
published website signs in with its own Azure identity. Never add a server, package, API key, or
network call to the page, and do not edit the preview helper.

1. Find the page. Default to `site/index.html`; an idea name such as `team-lunch` means
   `site/ideas/team-lunch/index.html`. If it does not exist, say **"Let's create your website
   first with /create-website."** and stop.
2. If the page already contains `Workshop.addChat`, only do step 5 (when `knowledge.md` is
   missing), then hand over with step 8.
3. Before touching the page, copy
   [workshop-chat.js](../create-website/assets/js/workshop-chat.js) unchanged to
   `site/js/workshop-chat.js`. The preview redraws as soon as the page changes, so the file must
   already be there. If an older copy exists, replace it so the chat also reads `knowledge.md`.
4. Right after the page's `js/workshop.js` script tag, add
   `<script src="js/workshop-chat.js"></script>`. From a page in `site/ideas/<name>/` the path is
   `../../js/workshop-chat.js`.
5. Create `knowledge.md` in the page's own folder (`site/knowledge.md`, or
   `site/ideas/<name>/knowledge.md`) unless it exists, with exactly this placeholder:

   ```markdown
   # What my page's chat should also know

   <!-- Write extra facts below in plain sentences: names, places, times, answers to common
        questions. The chat reads this file with every question, here and on your published
        website. Text inside these comment marks is not read. Keep everything fictional. -->
   ```

6. At the very end of the page's own inline script, add one line that names the bubble after the
   page, for example `Workshop.addChat({ title: 'Ask my planner' })`. Change nothing else.
7. Run `python3 scripts/website_preview.py start` yourself (for an idea page add its path relative
   to `site/`, such as `ideas/team-lunch/index.html`) and require `previewOpen: true`.
8. Hand over in this order, short:
   - **"Select Ask at the bottom right and ask: What is on this page?"**
   - **"Your chat knows three things: what the page shows (text, ticks, typed values, chart
     numbers, picture descriptions), the page's own code, and the file `knowledge.md` I made next
     to your page."** Give the file's path as a link.
   - **"Teach it something new: write a fact in `knowledge.md` (or ask me: Add to knowledge.md
     that our team lunch is every Friday at 12:00), save, then ask the chat about it."**
   - **"Check every answer against the page yourself. The assistant can be wrong."**
   - **"It works here and on your published website too."**

When the learner asks you to add facts later, write them in that page's `knowledge.md` below the
comment, in plain sentences, and leave the page itself unchanged.

If the bubble replies that the assistant is not switched on, this Codespace lacks the workshop
secrets or needs a restart: show the exact message to a helper. Do not install anything, add keys,
or change settings. Everything on the page stays fictional.

Official references: [VS Code webviews](https://code.visualstudio.com/api/extension-guides/webview)
and [Agent Skills](https://code.visualstudio.com/docs/agent-customization/agent-skills).
