# Day 4: GitHub Copilot Cloud Agents

Today you work the way software teams do. Every change goes through a **feature branch** and a
**pull request**, your pipeline stamps each release with a **version number**, and Copilot's
**cloud agent** builds a feature for you online. Your own **Code Review agent** checks each change
and writes a report, and you decide what is merged and deployed. You use
the same Codespace, your website, and your board, tickets, and agent from Day 3. Everything
stays made up. Stuck in the terminal? Paste the same sentence into Chat with **Agent** chosen; it
does the same job.

**Joining today?** You need your website on GitHub from Monday or Tuesday, and one ticket for
the delegation lab at 00:50. On GitHub open **Issues > New issue > Requirement** and write what
you want in plain words. Then ask Chat: "Write a user story and two Given/When/Then acceptance
criteria for this wish: [your wish]." Paste the answer under **User story** and **Acceptance
criteria**, and save. A board is optional today; the [Day 3 guide](DAY-3.md#1-tickets-board-and-tools)
shows how to make one.

## Today's Route

Times count from the start of the session.

| Elapsed     | What happens                                                           | You are finished when                                                 |
| ----------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 00:00-00:20 | [Cloud-agent overview: delegation, safeguards, and human review](#1-how-a-change-reaches-your-website) | You can say how a change reaches your live website.                   |
| 00:20-00:50 | [Practice branches and pull requests with a small change](#2-protect-main-and-version-your-releases) | `main` is protected, and your live website shows its version number.  |
| 00:50-01:30 | [Assign an approved requirement to Copilot](#3-delegate-an-approved-ticket) | Copilot is building your approved ticket in a pull request.           |
| 01:30-01:45 | Break                                                                  |                                                                       |
| 01:45-02:30 | [Build a Code Review agent: review rules and report format](#4-build-your-code-review-agent) | Your review rules and agent are merged, and Copilot CLI lists the agent. |
| 02:30-03:15 | [Run the agent on a diff and verify its findings](#5-review-copilots-pull-request) | Every finding in the report is marked Confirmed or Not a problem.     |
| 03:15-03:45 | [Request fixes with @copilot, retest, and peer-review](#6-ask-for-fixes-and-retest) | Copilot pushed a fix, your agent reviewed it again, and your checks pass. |
| 03:45-04:00 | [Checkpoint: review the report and decide whether to merge](#7-checkpoint-merge-or-not) | The feature is live with the next version number, or closed with a reason. |

**Lost?** Find the row the room is on (the presenter names it at the start of every block),
select its link, and start there. Raise your hand: a helper catches you up on what you skipped.

| Word           | Plain meaning                                                                         |
| -------------- | ------------------------------------------------------------------------------------- |
| Branch         | A separate line of work, so `main` stays safe while you try something.                |
| Pull request   | A proposed change from a branch. Nothing changes in `main` until a person merges it. |
| Merge          | Accept a pull request into `main`.                                                    |
| Ruleset        | Rules GitHub applies to a branch, such as "changes arrive only by pull request".      |
| Pipeline       | The workflow that runs by itself after a merge and publishes your website.            |
| Version number | The label of a release. Yours ends with the pipeline's run number, the build number.  |
| Cloud agent    | Copilot working by itself on GitHub, on its own branch, from a ticket you assign.     |
| Diff           | The list of lines a change adds (green) and removes (red).                            |
| Finding        | One thing a reviewer noticed, with where it is and why it matters.                    |

## 1. How a Change Reaches Your Website

**00:00-00:20.** The presenter explains, using a real pull request:

- **The road of every change:** feature branch, pull request, review, merge, pipeline, live
  website with a new version number. Nobody pushes straight to `main`, not even you.
- **Delegation:** you assign an approved ticket from your board to **Copilot**. Its user story
  and acceptance criteria say exactly what done means.
- **An agent that starts by itself:** the presenter opens a new **Requirement** ticket on the
  demo website. Nobody assigns it, yet an automation starts Copilot, which uses the user-stories
  skill to add the story and acceptance criteria to the ticket a few minutes later. You can set
  one up yourself in the optional extras.
- **Safeguards:** Copilot works on its own `copilot/...` branch. It cannot push to `main`, its
  pull request starts as a draft, and checks on its pull request wait until a person approves.
  It follows your instructions and skills, and your own Code Review agent checks its work.
- **Human review:** you read the change, check it yourself, and only you decide to merge.

## 2. Protect Main and Version Your Releases

**00:20-00:50.** Set the rules first, then send one small change down the road.

**Your website needs an address.** If you have not published it yet, type `/publish-website` in
Chat, then save, commit, and push as usual. Do it before step 1: after step 1, `main` takes
changes only through pull requests.

1. **Feature-branch policy.** On GitHub, open your repository's **Settings > Rules > Rulesets**,
   then **New ruleset > New branch ruleset**. Name it `Protect main`, set **Enforcement status**
   to **Active**, and under **Target branches** select **Add target > Include default branch**.
   Under **Branch rules**, keep **Restrict deletions** and **Block force pushes**, then tick
   **Require a pull request before merging**, with required approvals left at **0**: you are the
   only person in your repository, so you check each change yourself before you merge it.

   Leave the bypass list empty, so the rules apply to you too, and select **Create**. GitHub may
   ask you to **Confirm access** with your authentication app, GitHub Mobile, or password: that
   is normal for settings, so keep your phone at hand. Never share that code.
2. **A feature branch.** In your Codespace, select the branch name `main` at the bottom left.
   Choose **Create new branch...**, type `feature/version-number`, and press Enter.
3. **The pipeline change.** Open **.github > workflows > publish-website.yml** and find the line
   `# version: 1.0.${{ github.run_number }}`. Delete the `#` and the space after it, and keep the
   line's indentation. From now on every release writes `version.json` into your website, and
   `github.run_number` is the build number: it goes up by one with every run.
4. **Show it on the page.** Ask Copilot CLI: "In the footer of my first page, site/index.html,
   show the version from version.json, like Version 1.0.7. In my preview there is no
   version.json yet, so show Preview there. Change nothing else." Your website's address opens
   this first page. **Check:** your preview's footer says **Preview**.
5. Commit, select **Publish Branch**, then **Create Pull Request**. If VS Code asks you to sign in
   instead, open your repository on GitHub and select **Compare & pull request** in the yellow
   banner. If the push is refused
   because it changes a workflow file, show a helper: they make the same edit on GitHub with the
   pencil icon, on a new branch.
6. On GitHub, open the pull request and select **Files changed**: read the green and red lines
   yourself. Then select **Merge pull request**, **Confirm merge**, and **Delete branch**. GitHub
   may then offer **Delete codespace**: never select it. That is your own Codespace, with your
   work in it; it only still shows the old branch until step 8.
7. Open **Actions > Publish my website**: your merge started it. When it is green, open your
   website. Its footer shows **Version 1.0.** and the run's number from the Actions page.
8. Back in the Codespace, select the branch name again, choose `main`, then in **Source
   Control** select **... > Pull**.

**Check:** your ruleset is active, your change reached `main` through a pull request, and your
live website shows its version number.

## 3. Delegate an Approved Ticket

**00:50-01:30.** This is the delegation lab: Copilot's cloud agent builds your next ticket
online. The presenter delegates a demo ticket first; then you delegate yours. A helper confirms
that the cloud agent is switched on for your repository.

1. Open your board from your repository's **Projects** tab and pick a ticket in **Todo**:
   approved, with its user story and acceptance criteria, and small enough to check in a few
   minutes. None there? Run your User Requirements agent on a ticket first, as on Day 3, check
   that you could test every criterion by clicking or counting, and drag it into **Todo**.
2. Open the ticket and read it once more: could someone who has never seen your page tell when
   it is done? **Which page** must name the right page: `site/index.html`, or your idea's
   folder, such as `site/ideas/team-lunch/`. Keep **Only change** as it is. To change anything,
   select **...** and **Edit** on the ticket, then save.
3. Under **Assignees**, select **Assign to Agent** (or **Assignees > Copilot**). In the window,
   keep the base branch `main` and the agent **Copilot**, leave the prompt empty, and select
   **Assign**. If Copilot is not listed, tell a helper and follow the presenter's pull request
   instead. Never wait idle for it.
4. Within a minute your board moves the ticket to **In Progress** by itself; if it does not,
   drag the ticket into **In Progress**. Open the ticket again: it shows that
   Copilot started. Select the session link to watch its progress log.
5. **Follow the work.** It usually takes a few minutes. Find one step in the log where Copilot
   read your files and one where it checked its work. Then open **Pull requests**: its pull
   request starts as a **draft**, linked to your ticket. Open **Files changed**: does it change
   only your page, its sample data, and tests? Leave it open; you review it in section 5.
   Nothing changes until you merge.

**Check:** a draft pull request from Copilot appears under **Pull requests**, linked to your
ticket, and changes only what the ticket asked for.

| What you see                              | Next action                                                                   |
| ----------------------------------------- | ----------------------------------------------------------------------------- |
| Copilot is not in the Assignees list      | The feature is not switched on for this repository. Tell a helper.            |
| You chose Copilot, but nobody is assigned | The list closed without saving. Use **Assign to Agent** and its **Assign** button instead. |
| The pull request changed too much         | Comment with `@copilot` asking for the smaller change, or close it unmerged.  |
| GitHub asks you to approve workflows      | Ask a helper first. It is a safeguard: checks on Copilot's work wait for you. |
| Pull reports a conflict                   | Stop and show a helper. Never force a push.                                   |

## 4. Build Your Code Review Agent

**01:45-02:30.** Two small files again: **review rules** that every Copilot follows, and an
**agent** that writes a report.

1. **Review rules (15 minutes).** In Copilot CLI (type `copilot` in the terminal), paste this
   and change the bracketed part:

   > Create .github/instructions/review.instructions.md with `applyTo: "site/**"`. List my rules
   > for every change to my website: every acceptance criterion of the ticket is met; nothing
   > outside the ticket changed; typed text is shown safely (textContent, never innerHTML); no
   > new internet addresses, packages, keys, or real data; the page still works with a keyboard
   > and in a narrow window; [one rule of my own]. Keep it under 15 lines.

   Open **.github > instructions > review.instructions.md**. The `applyTo` line says which files
   the rules are for. **Your Code Review agent checks every change against this file**, and
   Copilot follows it when it builds, in your Codespace and as the cloud agent on GitHub: rules
   written once, used by every agent.
2. **The agent and its report format (20 minutes).** Paste this:

   > Create a custom agent file at .github/agents/code-review.agent.md with `name: code-review`
   > and a one-line description. It is a Code Review agent for my website. When I give it a pull
   > request number, it reads that pull request's changes and the ticket it is linked to, with its
   > user story and acceptance criteria, and checks them against the rules in
   > .github/instructions/review.instructions.md.
   > It writes a report to reviews/pr-NUMBER.md as a table with the columns #, Severity (Must fix,
   > Should fix, or Nice to have), File and line, What I found, Evidence (the exact line), and
   > Suggested fix. Each finding is one or two plain sentences for a beginner. Problems that were
   > already there before this pull request go in a separate table called "Already there before",
   > so they do not block this change. If it cannot check something itself, it lists at most
   > three short checks I can do by hand in the Website preview. It ends with "Verdict: Ready to
   > merge" or "Verdict: Not yet". It never changes other files, comments on GitHub, or merges.

3. Open **.github > agents > code-review.agent.md**, read its rules, and change one into your own
   words. Then type `/exit` and `copilot` again, and check that `/agent` lists **code-review**
   next to your **user-requirements** agent.
4. **Send both down the road.** `main` takes only pull requests now: create a branch named
   `review-tools`, commit both files, select **Publish Branch**, create the pull request, read
   its **Files changed**, and merge it. Then switch to `main` and **Pull**. From now on GitHub has
   your rules, and Copilot's cloud agent follows them in every pull request it builds.

## 5. Review Copilot's Pull Request

**02:30-03:15.** Two reviewers, your agent and you; one decision: yours.

**Behind?** No pull request from Copilot yet? Review your own pull request from section 2 instead,
and a helper checks why Copilot did not start.

1. Open Copilot's pull request for your ticket, for example **#5**: tickets and pull requests
   share one list of numbers. Select **Files changed** and read what it changed.
2. In Copilot CLI type `/agent`, choose **code-review**, and ask: "Review pull request #5."
   It asks before each command: read it and choose **Yes**. For the read-only `gh` and `git`
   commands, option 2 stops it asking again in your repository. If it offers to remember a fact
   about your repository, either answer is fine. A review takes about five minutes.
3. Open **reviews/pr-5.md**. For every finding, find the line on GitHub under **Files changed**.
   Add a column called **My check** and write **Confirmed** or **Not a problem**, with one reason.
   Did your agent miss anything you noticed yourself? **No findings?** That happens with a small,
   clean change. Then do the agent's checks by hand in step 4 and write what you saw under
   **My check**. **Verdict: Not yet** often only means the agent could not try the page itself.
4. Check the change yourself, too: type `/exit` and `copilot` to leave the review agent, then
   ask "Check out pull request #5 so I can try it". In Chat run `/start-website` and try each
   acceptance criterion. Run `pytest checks` in the terminal.

An agent's report can be wrong, just like any other answer. Your checks decide.

## 6. Ask for Fixes and Retest

**03:15-03:45.**

1. On the pull request on GitHub, write a comment that starts with `@copilot` and names one
   confirmed finding: "@copilot Fix finding 1 from my review: [what is wrong]. Change nothing
   else." No confirmed finding? Ask for one small thing you noticed when you tried it, for
   example "@copilot The Today label is small and easy to miss: make it a little bigger. Change
   nothing else." Copilot starts again and pushes a new commit to the same pull request. It
   takes a few minutes: do step 3 with your neighbor while you wait.
2. When it is done, ask Copilot CLI: "Pull the latest changes of this branch." Check the
   criterion again in the preview and run `pytest checks`. Then switch back to `main` (type
   `/exit`, select the branch name in the status bar, choose **main**, and type `copilot`) and ask
   **code-review** to review the pull request again: Copilot's branch started before you made
   your agent, so `/agent` lists it only on `main`. Then check that your **My check** notes are
   still in the report.
3. **Peer review:** show your neighbor the pull request and your report. Ask them to check one
   criterion on your screen and say whether they agree.

## 7. Checkpoint: Merge or Not

**03:45-04:00.**

1. Decide. **Merge** if every criterion passes and no **Must fix** is left: select **Ready for
   review**, then **Merge pull request**. Leave the **Reviewers** box as it is: your agent and you
   are the reviewers. If GitHub asks you to approve and run workflows, ask a helper first.
   Otherwise **Close pull request** with a comment saying why.
2. **Deployed.** A merge starts **Actions > Publish my website**. When it is green, open your
   website: the new feature is there, and the footer shows the next version number. On your
   board the ticket moved to **Done**: Copilot linked its pull request to the ticket, so the
   merge closed it. If it is still open, select **Close issue** on the ticket yourself.
3. In the Codespace switch to `main` and **Pull**. Save your report the same way as your rules:
   a new branch, commit `reviews/pr-5.md`, a pull request, and merge.

**Done when:** `main` takes changes only through reviewed pull requests, your live website shows
its version number, Copilot built an approved ticket online, your review rules and Code Review
agent produced a report whose findings you verified yourself, and you merged it, now live with
the next version number and **Done** on your board, or closed it with a reason.

**What you just learned:** feature branches and pull requests keep `main` safe, and the pipeline
labels every release with its build number. Agents build and review, but they follow what you
wrote: your ticket's acceptance criteria, your review rules, and your agent. A person still
checks and decides. Tomorrow GitHub checks every pull request for you, in a browser too: see the
[Day 5 guide](DAY-5.md).

## Optional extras

1. **An agent that starts by itself.** On GitHub open **Agents > Automations > Create new**. Name
   it `Criteria for new tickets`, choose the trigger **When an issue is created** with the filter
   `label:enhancement`, and use this prompt: "Read this new ticket. Use the user-stories skill to
   write its user story and acceptance criteria into the ticket's User story and Acceptance
   criteria sections, keeping the author's own words. Change nothing else." Select **Suggest
   tools** and keep only reading the ticket and updating it. Then open **Issues > New issue >
   Requirement**: nobody assigns it, yet a session starts, and the criteria arrive on the ticket
   or as a suggested change for you to approve. Turn the automation off afterwards under
   **Agents > Automations**, because each run uses your Copilot allowance.
2. Use the simpler **Website change for Copilot** template for a small change that is not a
   ticket from your board.
3. Ask Copilot on GitHub to write a ticket for you: open [github.com/copilot](https://github.com/copilot)
   and ask "In my repository, create a Requirement ticket: show which tasks are late." Read the
   draft before you select **Create**.
4. Ask your review agent to review your own pull request from section 2.

## Official References

- [About the cloud agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent),
  [start a task](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/kick-off-a-task),
  and [review its output](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/review-copilot-output).
- [The board's built-in automations](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations).
- [Rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets),
  and [the instructions each Copilot reads](https://docs.github.com/en/copilot/reference/custom-instructions-support).
- [The run number and other workflow values](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#github-context).
- [Custom agents](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-custom-agents),
  in [Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli)
  and [on GitHub](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/create-custom-agents).
- [Copilot automations](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-automations), an optional extra,
  and [Copilot writing tickets](https://docs.github.com/en/copilot/how-tos/copilot-on-github/copilot-for-github-tasks/use-copilot-to-create-or-update-issues) (public preview).
- [Branches and pull requests in VS Code](https://code.visualstudio.com/docs/sourcecontrol/overview)
  and [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow).
