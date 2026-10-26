# Workshop Quick Reference

Keep this short sheet beside you. The presenter shows each step first, so wait for the current
step instead of racing ahead. Use made-up information only.

| I want to... | Where to go |
| --- | --- |
| Find today's guide | In the Explorer, **docs > DAY-1.md** on Monday, **DAY-2.md** on Tuesday, and so on. On GitHub, your repository's **README** links to each day. |
| Get back on track when I am lost | Find the row the room is on in **Today's Route** at the top of today's guide, open its link, and start there. Raise your hand: a helper catches you up. |
| Read a guide nicely | Right-click the `.md` file in the Explorer and choose **Open Preview**. It is the same file. |
| Find a file | The **Explorer** is the files icon on the left. Select a folder to open it. |
| Ask Copilot | **View > Chat**. Choose **Ask** for questions, or **Agent** when Copilot should change files. Start with a question, then ask for one small change. |
| Stop Copilot | Select **Stop** in Chat, then look at what already changed. Stopping does not undo it. |
| Keep Copilot's change | Select **Keep** in Chat when you like it. Selecting **+** for the file in Source Control keeps it too. |
| Undo Copilot's change | Select **Undo** in Chat, then **Yes**. It takes back every change you have not kept. To go back further, hover over an earlier question and select **Restore Checkpoint**. |
| Start a new chat | Rarely needed: your first chat keeps working all week. If you do, select **+**, then, before typing, check the button under the chat box: if it says **Copilot**, select it and choose **Local**. |
| Ask what code means | Select a few lines in a file, then ask Chat: "Explain the lines I selected in plain English." |
| See what changed | **Source Control**, the branching-lines icon. Select a file to compare before and after. |
| Save | **File > Save**. This keeps the change in the file, not on GitHub yet. |
| Take a snapshot | In Source Control, select **+** next to the files you checked, type a short message, then **Commit**. |
| Let Copilot write the message | Select the **sparkle icon** in the Source Control message box. Read it and fix anything untrue. |
| See my history on GitHub | On your repository page select **Commits**, beside the clock icon (a narrow window shows only the clock). On a file, select **History**. |
| Send it to GitHub | **Source Control > ... > Push**. Then open your repository on GitHub to see it. |
| Build my first website | In Chat choose **Agent**, then type **`/create-website`** and pick one of the six websites, or **My own idea**. |
| Build my own idea | Run **`/create-website`** again and choose your own idea. It gets its own folder under `site/ideas/`. |
| See my website | **`/start-website`** opens it beside Chat. For an idea, add its folder name: `/start-website team-lunch`. |
| Close my website | **`/stop-website`**. Your files and entries stay. |
| Change how it looks | Just ask, for example: "Try a sky blue look. Keep everything else the same." |
| Show Copilot a picture | Drag the picture from the Explorer into the chat box, then ask, for example: "Make my page look like this sketch." |
| Draw a picture for my page | Ask: "Draw a picture for my header: a friendly rocket, in my colors." It appears in a few seconds. |
| Change a picture | Ask: "Change my header picture: make it a night scene." The old picture stays, so you can go back. |
| Add a chat to my page | Type **`/add-chat`**, then select **Ask** at the bottom right of your page. Check its answers yourself. |
| Teach my chat more | Write facts in `knowledge.md` next to your page, or ask: "Add to my page's knowledge.md: lunch is every Friday at 12:00." |
| Add a chart | Type **`/add-chart`** and pick one. For an idea's page, add its folder name: `/add-chart team-lunch`. |
| Publish my website (optional) | Type **`/publish-website`**, then save, commit, and push. When **Actions** is green, open the link under **Deployments**. |
| Paste into the terminal | **Ctrl+V** (Windows) or **Cmd+V** (Mac). Allow clipboard access if the browser asks. |
| Use Copilot in the terminal (Day 3) | Type `copilot` and press Enter. Type `/exit` to leave. |
| Use my own agent (Days 3-4) | In Copilot CLI type `/agent` and choose it. After creating a new agent or skill, type `/exit` and `copilot` once so it appears. |
| Use my skill (Day 3) | Name it in your request, for example "Use the user-stories skill on issue #1". |
| Write a ticket (Days 3-5) | On GitHub: **Issues > New issue > Requirement**. Write what you want in plain words; your agent adds the story and the criteria. |
| Make my board (Day 3) | Select the organization's name above your repository, then **Projects > New project > Board**, name it `<your username> website`, keep **Import items from repository** and choose your own repository. Then **Workflows > Item added to project > Off**, so new tickets wait under **No Status**. Later, open it from your repository's **Projects** tab. |
| Approve a ticket (Days 3-5) | On your board, drag its card into **Todo**. |
| Close a ticket with a commit (Day 3) | End the commit message with `Closes #1`, using the ticket's number. When it reaches `main`, the card moves to **Done**. |
| Run my tests (Days 3-5) | In the terminal type `pytest checks`. Green means pass; red shows what failed. |
| Start a branch (Days 4-5) | Select the branch name at the bottom left, then **Create new branch...**. Go back by choosing `main`, then **Pull**. |
| Save a change from Day 4 on | `main` takes only pull requests: a branch, commit, **Publish Branch**, create the pull request, merge it on GitHub, then `main` and **Pull**. |
| Protect `main` (Day 4) | On GitHub: **Settings > Rules > Rulesets > New ruleset > New branch ruleset**, as in the Day 4 guide. |
| Hand a ticket to Copilot (Days 4-5) | Open an approved ticket from **Todo**, then **Assign to Agent** (or **Assignees > Copilot**), keep `main` and **Copilot**, and select **Assign**. The board moves it to **In Progress** by itself. |
| See my screenshots (Day 5) | On GitHub: **Actions**, open the run, then **Summary > Artifacts > home-phone.png** or **home-desktop.png**. |
| Let Copilot's work run (Day 5) | On Copilot's pull request, read **Files changed**, then select **Approve workflows to run** in the merge box. |
| Approve a build for the feature slot (Day 5) | **Actions > Deploy feature slot**, open the newest run that says **Action required**, then **Approve and run**. Only Copilot's pull requests ask. |
| Open my feature slot (Day 5) | On the pull request, next to "deployed to feature-slot", select **View deployment**. Its address is your website's name plus `-feature`. |
| Approve a release (Day 5) | On GitHub: **Actions**, open the waiting run, **Review deployments**, tick **production**, then **Approve and deploy**. |
| Roll back a release (Day 5) | On GitHub: open the merged pull request, select **Revert**, then merge the new pull request. |
| Smoke-test my website (Day 5) | `python3 scripts/smoke_test.py https://<my website address>` |
| Something looks broken | Show a helper the exact message. Do not install anything. |
| My Codespace says "Codespace is stopped" | Select **Restart codespace** and wait a minute. Your files are kept: it stops by itself when nobody types for a while, for example over lunch. |
| Copilot CLI asks to "curate this memory" | It wants to remember a fact about your repository for next time. Read it: either answer is fine. |
| A pop-up in a corner: "workspace customizations need an update", or about Python | Select the **X** beside it. The workshop files are fine as they are; never select **Migrate**. |
| I chose not to trust the folder | Open the menu with three lines, **View > Command Palette**, type `Reload Window`, press Enter, then choose **Trust Folder & Continue**. |
| A tab called `COMMIT_EDITMSG` opened | Your commit message was empty. Close that tab, type a message in the Source Control box, then **Commit**. |
| No **New project** button, or my board is empty (Day 3) | On your board select **+ Add item**, type `#`, and pick each ticket. Still nothing? Show a helper. |
| I pushed without `Closes #1` (Day 3) | Open the ticket on GitHub and select **Close issue**. The board moves it to **Done**. |
| My typing lands in a file, not in Copilot CLI | Click in the terminal first, then type. This happens after Copilot shows a change beside the terminal. |
| My live footer still says **Preview** (Day 4) | The `#` is still in front of `version:` in publish-website.yml, or the merge changed nothing in `site/`. Show a helper. |
| No Copilot review on my pull request (Days 4-5) | Expected: Copilot code review is off. You and your own Code Review agent review. |

**Prompts to paste**, including the one that fetches updates from the main workshop repository,
are in [Quick Commands](QUICK-COMMANDS.md).

## Trust, but Verify

**Expect -> try -> compare -> improve -> repeat.** Click the button yourself. Try an empty entry.
Count a number yourself. Check again after a fix. "Copilot says it works" is not a check, and a
screenshot alone does not prove a button works. [Day 1, section 5](DAY-1.md#5-check-it-yourself)
has a check for each of the six websites.

## Your Finish Each Day

**Monday:** your first website with a chart or a chat you checked, a second website, all
saved on GitHub and shown to a neighbor.
**Tuesday:** a first version of your own idea (or a better Monday page), one check, questions for
IT, and two or three wishes under **Next** in `site/README.md`.
Nothing extra is required on Monday or Tuesday: no database, CLI, MCP, or setup. Publishing is
optional, with a helper.
**Wednesday:** your idea as tickets on your own board, your own user-stories skill and User
Requirements agent, acceptance criteria on every ticket, one ticket working on your page with
green `pytest checks` and **Done** on your board.
**Thursday:** `main` protected by your ruleset, your live website showing its version number, a
ticket built by Copilot's cloud agent, your own Code Review agent's report with every finding
checked by you, and a merge-or-not decision.
**Friday:** your tests and a browser UI check required on every pull request, Copilot's ticket
tried in your feature slot and released to production after you approved, a bad release rolled
back with **Revert**, your team demo, and a HANDOFF.md.

Ask a helper about sign-in, conflicts, permissions, or any command you do not understand. Never
paste passwords or real work records into Chat. Do not delete accounts or remove training access
yourself. In pairs, take turns at the keyboard. Before you leave, push your work, then stop your
Codespace at github.com/codespaces; closing the browser tab does not stop it.

[Day 1](DAY-1.md) | [Day 2](DAY-2.md) | [Day 3](DAY-3.md) | [Day 4](DAY-4.md) | [Day 5](DAY-5.md) |
[Quick Commands](QUICK-COMMANDS.md) | [Your week](../README.md#your-week)

Official help: [Codespaces](https://docs.github.com/en/codespaces/about-codespaces/what-are-codespaces),
[Markdown preview](https://code.visualstudio.com/docs/languages/markdown),
[Copilot prompting](https://docs.github.com/en/copilot/get-started/best-practices).
