# Day 3: VS Code and a Requirements Agent

Today you turn your idea into **tickets** on a **project board**, the way teams plan their work
on GitHub. You write your own **User Requirements agent**, a helper that adds a user story and
**acceptance criteria** to each ticket, so anyone can check when it is done. Then Copilot builds
one approved ticket in your Codespace, you test it, and the ticket closes itself. On the way you
meet the building blocks that make Copilot work for you: **Copilot CLI**, **tools (MCP)**,
**instructions**, **skills**, and **custom agents**. The presenter shows every step on a demo
website first; then you do the same on your own idea. Nothing is installed on your laptop, and
everything stays made up.

**No website yet?** In Chat choose **Agent**, run `/create-website`, and pick the Project
Planner. A helper gets you started while the room continues.

## Today's Route

Times count from the start of the session.

| Elapsed     | What happens                                                          | You are finished when                                             |
| ----------- | --------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 00:00-00:20 | MUKQ: global and Microsoft perspectives on AI development             | You listened; no laptop needed.                                   |
| 00:20-00:50 | [Workspace setup, repository walkthrough, and agent roles and tools](#1-tickets-board-and-tools) | Your tickets are on your board, Copilot CLI is signed in, and a GitHub tool listed your tickets. |
| 00:50-01:30 | [Build a User Requirements agent: instructions and output format](#2-build-your-user-requirements-agent) | Your **user-stories** skill and your agent exist, and Copilot CLI lists the agent. |
| 01:30-01:45 | Break                                                                 |                                                                   |
| 01:45-02:30 | [Draft user stories and acceptance criteria, then validate](#3-draft-and-validate-the-criteria) | Every ticket has criteria you can check, and your approved tickets are in **Todo**. |
| 02:30-03:15 | [Implement the approved ticket, debug, and verify](#4-build-the-approved-ticket) | Every acceptance criterion passes your own check.                 |
| 03:15-03:45 | [Add tests and write down how to build and run](#5-add-tests-and-how-to-run) | `pytest checks` is green, and `site/README.md` lists your requirements and how to run it. |
| 03:45-04:00 | [Checkpoint](#6-checkpoint)                                           | Your ticket closed itself and moved to **Done**.                  |

**Lost?** Find the row the room is on (the presenter names it at the start of every block),
select its link, and start there. Raise your hand: a helper catches you up on what you skipped.

## New Words for Today

| Word                | Plain meaning                                                                          |
| ------------------- | -------------------------------------------------------------------------------------- |
| Ticket (issue)      | One thing you want, written on GitHub under **Issues**, with a number such as #1.       |
| Project board       | A page of cards, one per ticket, in columns: Todo, In Progress, and Done.               |
| Terminal            | The panel below the editor where you type commands.                                    |
| Copilot CLI         | Copilot inside the terminal. The same assistant as Chat, through a different door.      |
| Tool (MCP)          | A plug that lets Copilot do something, such as read your tickets on GitHub.             |
| Instructions        | Standing rules Copilot reads before every request, in a short file.                    |
| Skill               | A recipe in a folder: how to do one job, step by step, in a fixed format.              |
| Custom agent        | A helper with one job that you describe in a short file, like a role card.             |
| User story          | "As a ..., I want ..., so that ..." : who needs what, and why.                         |
| Acceptance criteria | Checks that say when a ticket is done: "Given ..., when ..., then ...".                |
| Test                | A short file that checks your page for you. Green means pass, red means fail.          |

## 1. Tickets, Board, and Tools

**00:20-00:50.** The presenter shows each step on the demo website, then you do it on yours.

1. **Make your board.** At the top of your repository's page, select the organization's name,
   the part before the slash. Open **Projects > New project**, choose **Board**, and name it after
   yourself, such as `<your username> website`: everyone's board lives in the same organization.
   Leave **Import items from repository** ticked, and under **Repository** choose your own
   repository: it may show the workshop template at first. Select **Create project**.
2. **Approving stays your decision.** On your board, select **Workflows** at the top right, then
   **Item added to project**, and switch it **Off**; otherwise GitHub puts every new ticket
   straight into **Todo**. From now on, open the board from your repository's **Projects** tab.
   **Todo** means approved and ready to build, **In Progress** means being built, and **Done**
   means finished. Only people who can open your repository can read your tickets.
3. **Write a ticket.** On GitHub open your repository, then **Issues > New issue**, and choose
   **Requirement**. Give it a short title in plain words, such as `Mark urgent tasks`. Under
   **What I want**, write one or two sentences: who it is for, what they want, and why. Under
   **Which page**, keep `site/index.html`, or name your idea's folder instead, such as
   `site/ideas/team-lunch/`. Leave the story and the criteria to your agent, and select
   **Create**. The ticket gets a number, such as **#1**, and joins your board by itself under
   **No Status**: written, not approved yet.
4. **Your own idea.** Write two or three tickets like this for the idea you started on Monday or
   Tuesday, each about one thing you want *next*: the wishes you wrote under **Next** in
   `site/README.md` on Tuesday are a good start. A ticket about something your page already does leaves
   nothing to build.
5. **Open your Codespace** with the green **Code** button on your repository's page. Never create
   a second one. Open the menu (the three lines at the top left), then **Terminal > New
   Terminal**. Make it tall enough to read Copilot's questions: drag the line above it upwards,
   or select **Maximize Panel Size** (the square at its top right). Type `copilot` and press
   Enter. If it asks whether you trust this folder, choose yes.
6. **Signed in?** The bottom line shows a model name when Copilot is
   ready. If it asks you to sign in instead, type `/login`, press Enter, and choose the first
   option. Copilot shows a short code. Open [github.com/login/device](https://github.com/login/device)
   in a new browser tab, type the code, and select **Authorize**. Never paste a password or token
   into Copilot.
7. **Use a tool.** Ask: "Use the GitHub tools to list the open issues in my repository, with
   their numbers. Do not change anything." Above the answer Copilot shows the tool it used,
   **List issues**, from the GitHub **MCP** server: a plug that lets Copilot act on GitHub. A tool
   that only reads may run straight away. **Check:** compare its list with your board.

When Copilot wants to change a file, change something on GitHub, or run a command that could
change something, it asks first.
Read what it wants to do, and say yes only to what you understand. **Agent roles:** Chat's
**Ask** only answers, **Agent** can change files, a custom agent is a helper you give one job and
clear rules, and tomorrow the **cloud agent** works by itself on GitHub.

**Stuck in the terminal?** Every step today also works in Chat: open Chat, choose **Agent**, and
paste the same sentence. Once your own agent exists, it is in Chat's agent picker too. A helper
can switch you over in a minute; the result is the same.

## 2. Build Your User Requirements Agent

**00:50-01:30.** First the building blocks, then you build two small files, after the presenter
builds the demo website's pair.

1. **Meet the building blocks.** The presenter opens each one in the Explorer:

   | Building block | What it does                                     | In your repository                             |
   | -------------- | ------------------------------------------------ | ---------------------------------------------- |
   | Instructions   | Standing rules Copilot reads before every request | `.github/copilot-instructions.md`             |
   | Skill          | A recipe Copilot loads when the job fits          | `.github/skills/create-website/`, used Monday |
   | Custom agent   | A helper with one job, its own rules and tools    | `.github/agents/`, where yours arrives next   |
   | Tools (MCP)    | Plugs that let Copilot act, like the GitHub tools | `.vscode/mcp.json` in Chat; built into the CLI |

2. Type `/agent` and press Enter to see the list of agents. It shows only **GenericAgent**, the
   blank helper from Monday's demo: your own agent joins this list next. Press **Esc** to close
   it.

A **skill** in `.github/skills/` says *how* the job is done: the steps and the exact output
format. An **agent** in `.github/agents/` says *who* does it: its role and its rules. You
describe both in plain words; Copilot writes them; you read them and make them yours.

3. **The skill: the output format.** In Copilot CLI, paste this:

   > Create a skill at .github/skills/user-stories/SKILL.md with `name: user-stories` and a
   > description that says it turns one ticket for my website into a user story with acceptance
   > criteria. Its steps: read the ticket's What I want and Which page; write one user story as
   > "As a ..., I want ..., so that ..."; under it write 2 or 3 acceptance criteria as "Given ...,
   > when ..., then ..." that a person can check by clicking or counting, each with a checkbox;
   > list open questions instead of guessing. Its output fills the ticket's User story and
   > Acceptance criteria sections, followed by Open questions. Made-up people and data only.

   It may ask to read **docs.github.com** pages: that is GitHub's own help, so choose **2**, which
   allows those pages for the rest of this session. Then it shows the new file beside the
   terminal and asks to create it: choose **Yes**.

4. Open **Explorer > .github > skills > user-stories > SKILL.md**. The **name** and
   **description** between the two `---` lines tell Copilot when to load it. Change one step
   into your own words and save.
5. **The agent: the role and its rules.** Paste this, and change the bracketed part:

   > Create a custom agent file at .github/agents/user-requirements.agent.md with
   > `name: user-requirements` and a one-line description. It is a User Requirements agent for
   > my small website about [my idea]. When I name a ticket by its number, it reads the ticket
   > with the GitHub tools and uses the user-stories skill to draft its user story and acceptance
   > criteria. It shows me the draft first. Only when I say yes does it update that ticket with
   > the `gh issue edit` command: it reads the ticket's exact text with
   > `gh issue view NUMBER --json body --jq .body`, changes only the User story and Acceptance
   > criteria sections, keeps every other line exactly as it is, and gives the new text to
   > `gh issue edit NUMBER --body-file -` through standard input, so quotes cannot break it. Then
   > it reads the ticket again and tells me whether my own words under What I want are
   > unchanged. When something is unclear it asks me one question at a time. It never writes
   > code, never changes files, and uses made-up people and data only.

   The long part about `gh` keeps your own words safe: in a rehearsal, a shorter prompt let
   Copilot rewrite a whole ticket and lose them. Paste it as it is.

6. Open **Explorer > .github > agents > user-requirements.agent.md**. Its **name** and
   **description** tell Copilot when to use it; below them are its rules. Change one rule into
   your own words and save.
7. Copilot CLI loads agents and skills when it starts, so type `/exit`, then `copilot` again.
   Type `/agent`: **user-requirements** is now in the list.

**Check:** your skill and your agent exist, and `/agent` lists the agent. The agent also appears
in Chat's agent picker in VS Code: one file, two doors.

## 3. Draft and Validate the Criteria

**01:45-02:30.** The presenter runs the agent on a demo ticket, then you run yours.

**Behind?** No ticket yet? Write one first, as in [section 1](#1-tickets-board-and-tools), step 3.
No agent yet? Ask Chat: "Write a user story and two Given/When/Then acceptance criteria for this
wish: [your ticket's What I want]." Paste the answer into the ticket (**...** > **Edit**), and a
helper adds your agent with you at the next break.

1. Type `/agent`, choose **user-requirements**, and ask: "Write the user story and acceptance
   criteria for issue #1." Use your own ticket's number; if a list of tickets pops up while you
   type `#1`, press **Esc** once, then Enter. It reads the ticket and shows you a draft. It may
   ask you a question first: answer in plain words.
2. **Validate** each acceptance criterion: can you check it yourself by clicking or counting? If
   not, ask for a new version of only that one: "Rewrite criterion 2 so that I can check it by
   counting. Change nothing else." Answer its open questions the same way, one at a time. Here
   *validate* means checking that every criterion can be checked. It is not GxP validation: your
   practice website is a prototype with made-up data, not a validated system.
3. When you agree, choose **Yes** when it asks, or say: "Yes, update issue #1." Copilot asks to
   run the command that saves it, `gh issue edit`, sometimes inside a short Python script that
   checks your words stay the same: allow it. Then open the ticket on GitHub: the story and the
   criteria are there, and **your own words under What I want are unchanged**.

   **If something goes wrong:** your own words changed? Tell a helper: the ticket's **edited**
   menu keeps every earlier version. If Copilot says it may not update the ticket, copy its
   draft, select **...** and **Edit** on the ticket, paste the draft under **User story** and
   **Acceptance criteria**, and save.
4. Do the same for your other tickets.
5. **Approve.** Choose one small ticket to build today. On your board, drag its card into
   **Todo**: approved, ready to build. Ask a neighbor: "Could you check this ticket's criteria?"
   Approve a second ticket the same way: tomorrow Copilot's cloud agent builds it for you.

**Check:** every ticket has a story and criteria you could check, and your approved tickets are
in **Todo**.

## 4. Build the Approved Ticket

**02:30-03:15.** Now leave the requirements agent: type `/exit`, then `copilot`, so you are back
to ordinary Copilot, which can change files.

1. On your board, drag the ticket you build today into **In Progress**.
2. Ask: "Read issue #1 with the GitHub tools and build it in site/ideas/team-lunch/index.html.
   Change only what it needs and keep everything else. Do not run tests or scripts: I check it
   myself. Then list how I can check each acceptance criterion." Use your own ticket's number
   and your own page.
3. Read what it wants to change before you allow it. In Chat, run `/start-website team-lunch`
   (your own folder's name) if the preview is closed, and watch the change appear.
4. Check every acceptance criterion yourself, by clicking and counting.
5. **Debug:** if one fails, say exactly what happened: "Criterion 2 of issue #1 fails. I
   expected [this]. I saw [that]. Fix only that." Then check that criterion again, and the
   others too.

**Check:** every criterion of your approved ticket passes your own check in the preview.

## 5. Add Tests and How to Run

**03:15-03:45.** Work with your table: compare tickets and help each other.

1. Ask Copilot CLI: "Write tests in checks/test_issue1.py for the acceptance criteria of issue #1
   that can be checked from the files, using `from website import Page` as shown in
   checks/README.md. Give every assert a short message saying what I expected. Tell me which
   criteria stay manual checks. Then run `pytest checks`."
2. Copilot asks before it runs anything, such as `pytest checks`: read each request and choose
   **Yes**. A request waits until you answer, so look at the terminal if nothing seems to happen.
   **Check:** the terminal says `passed` in green.
3. **Break it on purpose:** in your page change one word that a test looks for, save, and run
   `pytest checks` again. It turns red and says what it expected. Undo your change with
   **Ctrl+Z** (**Cmd+Z** on a Mac), save, and run it again: green.
4. Ask: "Add a section called How to build and run to the end of site/README.md, in plain
   words: how to open the page (/start-website), how to run the tests (pytest checks), how to run
   the build check (python -m app.site --check), and the manual checks for issue #1. Then add a
   section called Requirements: one line per ticket with its number, title, user story, and
   status today (Todo, In Progress, or Done)." Copilot cannot read your board, so it asks you each ticket's
   status: pick it from the list, or choose **Other** and type, for example, "Not approved yet".
   Read both sections and correct anything that is wrong. `site/README.md` is now your
   website's validated README: your checked requirements, each one traced to its ticket, and how
   to run it.

## 6. Checkpoint

**03:45-04:00.**

1. Save. Open **Source Control** and review the files: your skill, your agent, your page, your
   test, and `site/README.md`. Commit with a message that ends with `Closes` and your ticket's number,
   for example `Mark urgent tasks. Closes #1`, then **... > Push**.
2. Open your board: the ticket closed itself and moved to **Done**. `Closes #1` in a commit that
   reaches `main` closes the ticket, and the board moves closed tickets to **Done** by itself.
3. Show a neighbor or a helper four things: your agent and skill, your board, the finished
   ticket with its criteria, and the working feature with its green tests.

**Done when:** your own **user-stories** skill and User Requirements agent are on GitHub, your
tickets have user stories with checkable acceptance criteria, `site/README.md` lists them, one ticket
works in your preview with green `pytest checks` and is **Done** on your board, and another
approved ticket waits in **Todo** for tomorrow. If sign-in is blocked, follow the presenter's
screen and tell a helper; it is not a reason to install anything.

**What you just learned:** a ticket holds one thing you want, and the board shows where every
ticket stands. Tools (MCP) let Copilot read and act on GitHub, instructions are standing rules, a
skill is a recipe with a fixed format, and an agent is a role: all short files you write in plain
words. Acceptance criteria make "done" checkable, and tests keep checking it after every change.
Tomorrow Copilot's cloud agent builds your next ticket on GitHub: see the
[Day 4 guide](DAY-4.md).

## Optional extras

1. Choose your agent in VS Code Chat's agent picker and ask the same question there. Compare
   the two answers.
2. On your board, add a field called **Priority** with the options Must, Should, and Could, and
   set it on every ticket.
3. Add a chat to your page with `/add-chat`, then check one of its answers against your page.
4. In Copilot CLI, type `/help` and find one command you would like to try later.

## Official References

- [Copilot CLI quickstart](https://docs.github.com/en/copilot/get-started/cli-quickstart) and
  [using Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/overview).
- [About issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/about-issues),
  [about projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects),
  [creating a project](https://docs.github.com/en/issues/planning-and-tracking-with-projects/creating-projects/creating-a-project),
  and [the board's built-in automations](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations).
- [Closing a ticket with `Closes #1`](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).
- [Custom agents in Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli)
  and [custom agents in VS Code](https://code.visualstudio.com/docs/agent-customization/custom-agents).
- [Agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) and
  [adding skills for Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills).
- [MCP concepts](https://docs.github.com/en/copilot/concepts/context/mcp) and the
  [customization comparison](https://docs.github.com/en/copilot/reference/customization-cheat-sheet).
- [Testing in VS Code](https://code.visualstudio.com/docs/debugtest/testing).
