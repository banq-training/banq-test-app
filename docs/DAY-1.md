# Day 1: Your First Website

Today you build a small website just by describing it, check that it works, and save it on
GitHub. You do not need to know how to code. Everything happens in your web browser; nothing is
installed on your laptop. Use made-up examples only, never real work information.

This is your only guide today. The presenter shows each step on their own repository, and you do
the same on yours, alongside them or straight after. You do not need to read ahead, and you
cannot break anything by looking. Keep the [Quick Reference](QUICK-REFERENCE.md) beside you.

## Today's Route

| When        | Section                                                                    | You are finished when                                    |
| ----------- | -------------------------------------------------------------------------- | -------------------------------------------------------- |
| 09:00-09:30 | [1. This is GitHub](#1-this-is-github)                                     | You know what a repository, a commit, and a push are.    |
| 09:30-10:00 | [2. Your copy, your Codespace, and Chat](#2-your-copy-your-codespace-and-chat) | Your own copy and its Codespace are open, you compared Copilot's table name with someone else's, and you asked Chat a question. |
| 10:00-10:30 | [3. Your first website](#3-your-first-website)                             | Your page opens beside Chat and is saved on GitHub.      |
| 10:30-10:45 | Break                                                                      |                                                          |
| 10:45-11:45 | [4. Build another website](#4-build-another-website)                     | Your second website opens in its own folder and is on GitHub. |
| 11:45-12:15 | [5. Check it yourself](#5-check-it-yourself)                               | You checked a button and a number yourself.              |
| 12:15-13:00 | Lunch                                                                      |                                                          |
| 13:00-14:00 | [6. Make it useful](#6-make-it-useful)                                     | Your page has a chart or a chat you checked, and your own look. |
| 14:00-14:45 | [7. Save, share, and keep building](#7-save-share-and-keep-building)       | Your work is on GitHub and you found its history there.  |
| 14:45-15:00 | Pair sharing                                                               | You showed one feature and how you checked it.           |

**Lost?** Find the row for the time now, open its link, and start there. Raise your hand: a
helper catches you up on what you skipped.

**The habit to keep: expect -> try -> compare -> improve -> repeat.** Say what you expect, try it
yourself, compare what you see, and ask for one fix if needed. "Copilot says it works" is not a
check. If Copilot changes more than you asked, select **Stop** in Chat and ask for something
smaller. Never approve a command you do not understand.

## 1. This Is GitHub

**09:00-09:30, after the welcome, the SEFR video, and the ASTER Overview teaser.** Concepts
only: no commands. Just watch; you make your own copy at 09:30.

1. **This is GitHub:** a website that keeps projects and every saved version of them.
2. **This is a repository:** a project's folder on GitHub. The workshop **template** link your
   facilitator sent you opens the starting copy everyone uses: a list of files and, under them,
   the **README**, its front page. The README's **Day 1** link opens this guide.
3. **Look around** while the presenter shows each part:
   - **Read any file:** select a file name. Pages ending in `.md`, like this one, show nicely.
   - **See every snapshot:** **Commits**, next to the clock icon.
   - **Look back in time:** open a file and select **History** to see how it changed.

| Word       | Think of it as...                                                           |
| ---------- | --------------------------------------------------------------------------- |
| Repository | Your project folder on GitHub, with its whole history.                      |
| Codespace  | A computer in the cloud that opens in your browser.                         |
| Copilot    | A helper you talk to. It is clever but can be wrong, so you check its work. |
| Commit     | A snapshot of your work, with a short label saying what changed.            |
| Push       | Sending your snapshots up to GitHub, where they are safe.                   |

The order is always **save -> review -> commit -> push**. Saving does not send anything to
GitHub; pushing does.

**Done when:** you know the five words above. Nothing to do on your laptop yet.

## 2. Your Copy, Your Codespace, and Chat

**09:30-10:00.** Do each step with the presenter, or straight after.

1. **Make your own repository.** On the template, select
   **Use this template > Create a new repository**, then:
   - **Owner:** choose **agentic-dev-labs**, not your own name.
   - **Repository name:** your GitHub username, for example `AliFarahnak`. Your website uses it.
   - **Visibility:** choose **Private**. It may start on **Internal**.
   - Leave everything else as it is, including the optional **Jumpstart** box, and select
     **Create repository**.

   **Check:** the top of the page shows **agentic-dev-labs /** your name and a **Private** label.
   If it shows anything else, or **agentic-dev-labs** is not in the list, raise your hand.
   Make only one. Working in a pair? Only the person at the keyboard makes one, and a helper
   adds the partner.
2. **This is your repository.** The presenter shows it: the same files as the template, the
   README under them, and your first snapshot under **Commits**. Everything you make this week
   lives here.
3. **Open your Codespace.** Select the green **Code** button, then **Codespaces**, then
   **Create codespace on main**. It opens in a new tab in about a minute. If it asks
   **Do you trust the authors of the files in this folder?**, choose **Trust Folder & Continue**:
   it is your own copy of the workshop, and your website preview needs it. Never create a
   second Codespace. If it shows an error, tell a helper. Nothing goes on your laptop.

   **A message pops up in a corner?** For example "workspace customizations need an update", or
   a message about **Python**. Close it with its **X**. Never select **Migrate**:
   the workshop files are fine as they are.
4. In the **Explorer**, the file list on the left, open the **docs** folder, right-click
   **DAY-1.md** and choose **Open Preview**. It is this guide, now inside your Codespace. To see
   the plain text, select its other tab.
5. Open the menu with three lines at the top left and choose **View > Chat**. **Sign in first:**
   if **Sign In** shows at the bottom right, select it once and follow the GitHub prompts, or
   Chat cannot answer. **Check it is a Local chat:** the button under the chat box says
   **Local**. If it says **Copilot**, select it and choose **Local**. Only a Local chat keeps each
   helper inside its limits, so **Ask** cannot change files and a helper without the right tools
   cannot go online. Then, in the list at the bottom of the chat box,
   choose **Ask**: it only answers and never changes your files.
6. **Same question, different answers.** Everyone asks Copilot the same thing. Type
   "Invent a fun name for my workshop table. Reply with the name only." and press Enter.
   **Check:** compare it with your neighbor's, or the presenter's on screen. Did you get the same
   name? Raise your hand when the presenter asks. Copilot does not look the name up: it writes a
   new answer each time, so the same question can give different answers. That is why you check
   its work.
7. Stay in this chat all day; you do not need a new one. Ask: "What is in the docs folder?"
   **Check:** open the **docs** folder in the **Explorer**. Does Copilot's list match the files
   you see?
8. Now ask it precisely: "Reply with exactly 5 bullet points, Monday to Friday, one per day,
   each 5 words or fewer. No other text."
   **Check:** 5 bullets, one per day, and count the words: 5 or fewer each? Compare with your
   neighbor: the same shape, much closer than the table names. A precise question gets you what
   you asked for. You did not start over: you told Copilot what you wanted. You can always ask
   again, or say that something is wrong.

Then just watch: the presenter shows that **Ask** cannot change a file, then shows that
**GenericAgent**, a blank helper in every copy, cannot go online until it is given one more
tool. You make your own helpers on Wednesday.

**Done when:** you have your own private repository in agentic-dev-labs, its Codespace is open,
you compared Copilot's table name with someone else's, and you asked Copilot a question and a
follow-up. If sign-in or Copilot is missing, ask a helper. Never install anything on your laptop.

## 3. Your First Website

**10:00-10:30.** First the presenter shows nine websites that people built just by describing
them; they click through by themselves, about 5 minutes. Then the presenter shows
`/create-website` on their repository; you do the same on yours.

1. In Chat, choose **Agent** instead of **Ask**: **Agent** can change your files. Type
   **`/create-website`**, pick it from the list, and press Enter.
2. Copilot asks one question: which website would you like to make? Choose **Project Planner**,
   **Calendar**, **Ideas Wall**, **Weather**, **Princeton Map**, **Photo Studio**, or
   **My own idea**. The presenter builds the Project Planner; pick it if you are unsure.
3. Copilot builds it and opens it in the **Website preview** beside Chat, named after your
   repository, for example **AliFarahnak Project Planner**. On the way it asks two or three
   times to run a command that lists, copies or renames your website's files, or
   `python3 scripts/website_preview.py start`, the helper that opens your preview: select
   **Allow** each time. If it asks to delete or install something, raise your hand.
4. Press **+** and add a made-up entry.
   **Check:** a new **index.html** appears in **Explorer > site**. Seeing the file is the
   proof, not Copilot saying "done". Then select **Keep** under the chat box: it accepts the
   change. Do this whenever you like a change, because **Undo** takes back every change you
   have not kept.
5. **Save it on GitHub.** Choose **File > Save All**; if it is grey, everything is already
   saved. Then open **Source Control**, the icon that looks like branching lines. This first
   time it lists many files: your page plus the pictures, fonts and styles it needs. That is
   expected. Hover over **Changes** and select its **+** to include them all, type
   `Add my first website`, select **Commit**, then **... > Push**.
   **Check:** open your repository on GitHub in a new browser tab, open **site**, then
   **index.html**. It is there.

Work only in your own repository. If anything asks you to create another repository, says a push
was rejected, or mentions a conflict, stop and ask a helper. Never force a push. Working in a
pair? Take turns at the keyboard. If `/create-website` is not in the list or the preview does not
open, show a helper.

**Done when:** your page opens beside Chat and it is on GitHub. After the break, at 10:45, you
build a second website.

## 4. Build Another Website

**10:45-11:45.** Build a second website, any of the others or your own idea, just by describing
it. Your first page stays exactly as it is. Everything you add stays made up.

### Pick What to Build (5 minutes)

You saw these at 10:00, all made the same way as yours, just by describing them:

| Website         | What it does                                                            |
| --------------- | ----------------------------------------------------------------------- |
| Weather         | Your cities' forecast, and a 3D chart of their year that you can turn. |
| Princeton Map   | Sights you can filter, add to, and see in 3D.                          |
| Photo Studio    | The workshop AI repaints photos of things, places and pets.            |
| Lab Chase       | A funny 3D maze game: a scientist chases escaped molecules.            |
| Request Tracker | Requests with stages, owners and overdue flags.                        |
| Team Dashboard  | Monthly numbers with a what-if forecast.                               |

Pick one you would like to try, or think of your own.

### Build It (40 minutes)

1. In Chat, with **Agent** chosen, type **`/create-website`** again. Copilot sees that you
   already have a page and asks what you would like: answer **build my own idea**.
2. Describe it in one sentence, for example one from the table below. Something from your own
   work is welcome too, as long as every entry is made up.
3. Copilot builds it in its own folder, such as `site/ideas/lunch-map/`, and opens it beside
   Chat. Your first page stays exactly as it is.
4. Try it, then ask for one change in ordinary words and add "Leave the rest alone." For
   example: "Make the headline friendlier. Leave the rest alone." Watch the change appear by
   itself. Like it? Select **Keep**.

| You would like... | Say                                                                  |
| ----------------- | -------------------------------------------------------------------- |
| A weather page    | "A weather page for my three favorite holiday cities."              |
| A map             | "A map of my favorite lunch spots in Princeton."                    |
| A photo studio    | "A photo studio that repaints pictures of my pets."                 |
| A calendar        | "A calendar for my team's made-up birthdays."                       |
| An ideas wall     | "An ideas wall for our next team outing."                            |
| A game            | "A funny 3D game where a scientist chases escaped molecules."        |
| A tracker         | "A tracker for team requests with stages Submitted, Doing and Done." |
| A dashboard       | "A dashboard of made-up monthly sales by region."                    |

**Check:** a new folder appears in **Explorer > site > ideas**. `/start-website` still opens
your first page; add the folder's name to open the new one, for example `/start-website lunch-map`.
If Copilot changed too much, select **Stop**, then **Undo** in Chat, and ask for something smaller.

### Save and Show (15 minutes)

Show a neighbor your pages and let them try one. Then save, review, commit, and push, just like
this morning: **File > Save All**, then **Source Control**. This time it lists only what
changed: your new website's folder. Type a short message, select **Commit**, then
**... > Push**, and find the folder on GitHub.

**Done when:** your second website opens beside Chat in its own folder, your first page still
works, and both are on GitHub.

## 5. Check It Yourself

**11:45-12:15.** Trust, but verify: Copilot can be wrong, so you check. Use your first page:
type `/start-website` to open it beside Chat.

1. **Check a button (10 minutes).** Ask for one new button, such as "hide finished tasks",
   "show only this week", or "shuffle the ideas". Say what you expect, click it twice, and
   compare. If it is wrong, tell Copilot: "I expected ..., but I saw ...". Check again after the fix.
2. **Check a number (10 minutes).** On your first page, count it yourself, using the table
   below. The table counts the example entries, so add the ones you made: with the task you
   added at 10:00, the planner shows **1 of 5 done**. If your first page is your own idea, use
   the check Copilot gave you when it built the page. Do not trust a number you have not checked.
3. **Save it (10 minutes).** Tell a neighbor what you checked and what happened, including
   anything that does not work yet. Then save, review, commit, and push.

| Your website    | Check it yourself                                                                    |
| --------------- | ------------------------------------------------------------------------------------ |
| Project Planner | 4 tasks and 1 ticked, so the bar reads **1 of 4 done**. Tick one more: 2 of 4. With the task you added this morning: 1 of 5, then 2 of 5. |
| Calendar        | **3 notes planned**: today, tomorrow, and in three days. Add one on Friday: 4. Drag it to Monday: still 4. |
| Ideas Wall      | **3 ideas**. Add one: 4. Remove one: back to 3.                                      |
| Weather         | Select **the raw forecast data** link and compare today's temperature with the page. |
| Princeton Map   | **18 places**. Choose History: 6. Press **+**, name a place and click the map: 19.   |
| Photo Studio    | **6 pictures**. Make the sleepy cat into a watercolor and save it: the gallery shows 7. |

Weather is the only page with live data. If the internet is blocked, it says it is showing sample weather.

**Done when:** you checked one button and one number yourself and your work is on GitHub.

## 6. Make It Useful

**13:00-14:00.** Add **one feature**, a chart or a chat, and make **one appearance change**,
then check it yourself. The presenter shows one change, then you try it on your own page. Keep
talking to Copilot in normal Chat. This is not a new creation interview, so do not run
`/create-website` again.

### Choose Your Feature (5 minutes)

Pick one. It goes on your first page; for your idea's page, add its folder name, for example
`/add-chart lunch-map`. If a feature already works on your page, pick another one.

| Feature   | How to start                                                        | What you get                                                                   |
| --------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| A chart   | Type **`/add-chart`**                                               | A chart drawn from your own entries, even a 3D one, that follows every change. |
| A chat    | Type **`/add-chat`**                                                | An **Ask** button that knows your page, its code, and the facts you write in `knowledge.md`. |
| A picture | Ask: "Draw a friendly rocket for the top of my page, in my colors." | A new picture for your page, drawn by the workshop AI in a few seconds.        |

### Add It (15 minutes)

1. In Chat, with **Agent** chosen, start your feature. For a chart, Copilot asks one question:
   which chart? Choose one, such as the Project Planner's **Progress gauge** or its 3D
   **Week skyline**.
2. Watch it appear on your page by itself. Drag a 3D chart to turn it. When it looks right,
   select **Keep** in Chat.
3. For a chat, select **Ask** at the bottom right of your page and ask: "What is on this page?"

Not right? Ask again, or select **Undo** in Chat. Pictures stay made up: no real people, logos,
or company names.

### Check Your Feature (15 minutes)

Start from the example entries and use the table in [section 5](#5-check-it-yourself). For your
other pages, use the check Copilot gave you when it built them.

- **A chart:** do the check and watch the chart follow. Does it agree with your own count?
- **A chat:** ask something you can count yourself, such as "How many tasks are done?", and
  compare. The chat can be wrong too.
- **A picture:** is it what you asked for, and is everything in it made up?

Also try the keyboard (Tab and Enter) and a narrow window. Do the older features still work?

If something is wrong, say: "I expected [this]. I saw [that]. Fix only that, and keep [the part
that works] unchanged." Then check again. Copilot saying it works is not a check.

### Make the Design Yours (15 minutes)

Describe what you want in ordinary words. For example:

> Keep the page light. Try a sky blue look. Keep the text easy to read and leave the content
> and features unchanged.

> Give the cards more space and make the + buttons easier to see. Keep my colors.

Look at the change in **Source Control**, save, and watch the preview update. Like it? Select
**Keep**. You do not need any design words or codes. If the preview is closed, type
`/start-website`.

**Be brave once, then undo it.** Ask for something wild, such as "Make the whole page bright
purple with giant text." Look at the preview. Then, in Chat, select **Undo** and then **Yes**:
Copilot shows **Keep** and **Undo** after each change it makes, and **Undo** takes back every
change you have not kept. That is why you kept your chart and your look first: your page returns
to them. Now you know you can always go back.

**Optional: show Copilot a sketch.** Drag **docs > images > sketch-example.png** from the
Explorer into the chat box and ask: "Make my page look more like this sketch. Keep all my
entries and features."

![A hand-drawn page sketch: a wide header with a sun doodle, a big centered title, a short welcome line, and a small "3 of 5 done" badge; three rounded cards with an orange stripe on top; a big round + button at the bottom right. Orange notes say warm sunset colors, rounded cards with lots of space, and big round + button.](images/sketch-example.png)

If Copilot says it cannot see pictures, skip the sketch. A photo of your own sketch works too,
but never a picture with real work information in it.

### Show a Neighbor (10 minutes)

Show a neighbor your new feature and your new look, and tell them how you checked it. Save. The
next section saves it to GitHub.

**Done when:** your page has a chart or a chat (or a new picture) that you checked yourself,
and one design change. Entries that stay after a refresh are a bonus, not a requirement.

## 7. Save, Share, and Keep Building

**14:00-14:45.** Save your work on GitHub, find its history there, and keep improving it. At
14:45 everyone moves to pair sharing.

### Let Copilot Write the Message (10 minutes)

1. Save your files. Open **Source Control** and read what actually changed, not only what Chat
   said. You should see only your website files and your note, with no real or private information.
2. Select **+** next to each file you checked.
3. In the message box, select the **sparkle icon**. Copilot reads your changes and writes the
   message for you. Read it and fix anything that is not true. No sparkle? Type a short message yourself.
4. Select **Commit**, then **... > Push**. If a push is rejected or mentions a conflict, ask a
   helper. Never force a push.

### Explore Your Work on GitHub (10 minutes)

GitHub keeps every snapshot you pushed today, like a time machine for your work.

5. Open your repository on GitHub and select **Commits** (next to the clock icon; a narrow window
   shows only the clock). These are the snapshots of your project, newest first. Yours from
   today are at the top: how many did you make?
6. Select one of your own snapshots, for example **Add my first website**. GitHub shows exactly
   what changed: green lines were added, red lines were removed.
7. Go back to your repository, open **site > index.html**, and select **History**. Each entry is
   one version of your page. Find the change you made after lunch by its message.

**Check:** you found your first commit and your page's history on GitHub.

### Take a Challenge (15 minutes)

Pick one level, ask Copilot, and check the result yourself:

| Level      | Challenge                                                                                                          |
| ---------- | ------------------------------------------------------------------------------------------------------------------ |
| **Bronze** | Ask Copilot: "Suggest three small ideas for my page." Pick one and ask for it.                                     |
| **Silver** | Make your page phone-friendly: drag the preview narrower, tell Copilot what looks wrong, and check again.          |
| **Gold**   | Give your idea's page a chart or a chat too: `/add-chart lunch-map` or `/add-chat lunch-map`, with your own folder's name. |
| **Bonus**  | Add the feature you did not pick after lunch: a chart, a chat, or a picture. Check it against your page.           |

Done, and time left? Take the next level. Then save, commit, and push again.

### Show It (10 minutes)

8. Show one feature to a neighbor. Explain what you expected, what you saw, and anything that
   does not work yet. Tell them your next idea instead of starting something big.

**Done when:** your work is on GitHub, you found your own history there, your page still works
in the preview, and you can explain one real check. A deployment or saved browser state is not required.

When you finish for the day, stop your Codespace at [github.com/codespaces](https://github.com/codespaces)
(**...** > **Stop codespace**). Closing the browser tab does not stop it. Tomorrow the green
**Code** button reopens the same Codespace, and your guide is [Day 2](DAY-2.md).

## When It Does Not Work

| What you see                                   | What to do                                                                 |
| ---------------------------------------------- | -------------------------------------------------------------------------- |
| A blank page or no preview                     | Type `/start-website`. Still blank? Show a helper the exact message; a helper can run `python3 scripts/website_preview.py status`. |
| Copilot changed your first page instead of making a new folder | Select **Stop**, then **Undo** in Chat, and say "Build my own idea in its own folder." |
| Copilot changed other files                    | Select **Stop**, then **Undo** in Chat, and ask for less.                  |
| A button or a number is wrong                  | Tell Copilot what you expected and what you saw, then check again.         |
| The chat says the assistant is not switched on | Show a helper the exact message, and add a chart meanwhile.                |
| Entries disappear after a refresh              | Show a helper; the page should remember them in this browser.              |
| Something asks you to install                  | Say no and ask a helper.                                                   |

## More Words

| Word            | What it means                                                            |
| --------------- | ------------------------------------------------------------------------ |
| VS Code         | The program you see inside the Codespace.                                |
| Ask             | In Chat: Copilot only answers. It never changes your files.              |
| Agent           | In Chat: Copilot can change your files. You check each change.           |
| Skill           | A recipe Copilot follows when you type its name, like `/create-website`. |
| Keep and Undo   | Accept Copilot's change, or take back every change you have not kept.    |
| Website preview | Your page beside Chat while you build it. Only you can see it.           |
| Open Preview    | Shows a guide like this one nicely. It is not your website.              |

## Optional extras

1. **Peek inside the code.** Your page is made of code: plain text that tells the browser what
   to show. You do not need to learn it; just take a look, with Copilot as your guide.
   - In the **Explorer**, open **site > index.html** and scroll through it. It is only text.
   - Select about five lines near the top: click at the start of the first line, then hold
     **Shift** and click at the end of the fifth. In Chat, ask: "Explain the lines I selected in
     plain English, one short sentence per line. I have never seen code before."
   - Find your page's big headline: click inside index.html, press **Ctrl+F** (**Cmd+F** on a
     Mac), type `<h1>`, and press Enter. The words between `<h1>` and `</h1>` are the headline
     on your page, for example *Plan the week, one card at a time*.
   - Change one or two of those words yourself, leaving `<h1>` and `</h1>` as they are. Choose
     **File > Save** and watch the preview update by itself. Looks broken? Press **Ctrl+Z**
     (**Cmd+Z** on a Mac) until your typing is undone, and save again.
2. **One more idea.** Run `/create-website` again and describe another idea in one sentence. It
   gets its own folder too. If time runs out, stop; Tuesday has more time for your ideas.
3. **One more feature.** Ask for one of these category-specific ideas, changed to fit your page.
   Ask for a short plan first, say yes, then check it.

   | Category | Ask Copilot |
   | --- | --- |
   | Project Planner | "Add an owner name to each task card, shown small under the title, and let me type it when I add a task. Keep the design unchanged." |
   | Calendar | "Let me give each note a type: meeting, personal, or deadline, each with its own color. Keep the design unchanged." |
   | Ideas Wall | "Add a thumbs-up button with a count to each idea, and a button to sort by most votes. Keep the design unchanged." |
   | Weather | "Add a switch between Fahrenheit and Celsius that remembers my choice. Keep the design unchanged." |
   | Princeton Map | "Add a search box above the list that shows only the places whose name matches. Keep the design unchanged." |
   | Photo Studio | "Add a title box so I can name a picture before I save it to the gallery. Keep the design unchanged." |

4. Add sorting, a theme switch, or favorites, or ask for a smaller or clearer version of one
   button. Then repeat your checks.
5. Your entries are remembered with localStorage, in this browser only. It is not a shared
   database: another browser, or a published page, starts with the examples again.

### Publish Your Page

If your page is ready, you can put it on the internet so others can open it with a link, even
on a phone. This is optional, and you can also do it on Tuesday or Thursday.

1. In Chat, type `/publish-website`. Accept the suggested name or type your own; Copilot writes it
   into `config.json` and tells you your address.
2. Save, commit and push as usual. Publishing starts by itself.
3. Wait about two minutes. On GitHub, **Actions > Publish my website** shows progress; when it
   is green, select the link under **Deployments** on your repository page.
4. Try your main feature on the published page. It starts with the example entries, because your
   preview entries stay in your preview. **Ask** answers on the published page too; photo editing works only in the preview.
5. From now on, every push updates your published page by itself.

Published pages stay online until the workshop owner removes them after the workshop. Stopping
your Codespace does not take down a published page.

## Official References

- [Codespaces overview](https://docs.github.com/en/codespaces/about-codespaces/what-are-codespaces)
  and [source control in Codespaces](https://docs.github.com/en/codespaces/developing-in-a-codespace/using-source-control-in-your-codespace).
- [Copilot prompting](https://docs.github.com/en/copilot/get-started/best-practices).
- [Review and undo AI changes](https://code.visualstudio.com/docs/agents/run/review-code-edits).
- [Chat context](https://code.visualstudio.com/docs/agents/concepts/context): how Copilot reads your selected lines,
  and [adding a picture to Chat](https://code.visualstudio.com/docs/chat/copilot-chat-context).
- [Agent Skills](https://code.visualstudio.com/docs/agent-customization/agent-skills): how `/create-website` works.
- [Commit messages with Copilot](https://code.visualstudio.com/docs/editing/copilot-smart-actions): the sparkle icon.
- [Commit history on GitHub](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/viewing-and-comparing-commits/differences-between-commit-views).
- [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow) and the
  [GitHub Actions quickstart](https://docs.github.com/en/actions/get-started/quickstart): what runs when you publish.
- [Apache ECharts](https://echarts.apache.org/en/index.html): the chart library behind `/add-chart`.
