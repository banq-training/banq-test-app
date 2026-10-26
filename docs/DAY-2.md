# Day 2: Build Your Own Idea

Today you build your own idea, with help at your table. Three short talks set the scene: David
and Jackie in the morning, and Bill Leeson just before lunch. The rest of the day,
helpers work with you at the tables. Use the same habits as Monday: ask in Chat, watch the
preview, check it yourself, and save. Use made-up content only, never real work data.

## Today's Route

| When        | What happens                                                                         |
| ----------- | ------------------------------------------------------------------------------------ |
| 09:00-09:30 | David: how business and IT work together, and which tools are approved.              |
| 09:30-10:30 | Jackie: how shared data and the Power Platform work, through examples.               |
| 10:30-10:45 | Break. Reopen Monday's Codespace: green **Code** button, **Codespaces**, then its name. |
| 10:45-11:45 | [Morning build](#morning-build-1045-1145), with help at your table.                  |
| 11:45-12:15 | Bill Leeson: Building a Project Brain. Save your work before it starts.              |
| 12:15-13:00 | Lunch.                                                                               |
| 13:00-14:00 | [Improve one interaction](#improve-one-interaction-1300-1400) and check it.          |
| 14:00-14:45 | [Fixes and optional publishing](#fixes-and-optional-publishing-1400-1445).           |
| 14:45-15:00 | [Show a neighbor and plan your next step](#show-and-plan-the-next-step-1445-1500).   |

You do not set up anything from the talks today. Never create a second Codespace.

**Lost?** Find the row for the time now, open its link, and start there. Raise your hand: a
helper catches you up on what you skipped.

## Choose One Useful Outcome

Pick the idea you sent in, or keep going with the idea you started on Monday. If you do not have
one yet, keep improving Monday's page; that is fine. You never need a real spreadsheet or
customer list to show an idea.

Before building, tell your helper:

| Question                            | Example                                                  |
| ----------------------------------- | -------------------------------------------------------- |
| Who is this for?                    | Someone organizing a made-up team event.                 |
| What should they be able to do?     | Add an event and filter by day.                          |
| What is the smallest first version? | One page with a list, a form, and a filter.              |
| How will I check it?                | Add a made-up event, filter, and see the right entries.  |

Everything stays in your own repository. Your idea gets its own folder under `site/ideas/`, so
Monday's page is never replaced. From Wednesday to Friday you can keep building this same idea.

## Morning Build: 10:45-11:45

1. **Agree the first version (10 minutes).** Tell your helper your four answers and agree the
   smallest first version. Do not create any files yet.
2. **Build or continue one page (35 minutes).** Keeping Monday's idea? Open it with
   `/start-website` and its folder's name, such as `/start-website team-lunch`. A new idea?
   Run `/create-website` once, choose your own idea, and describe it in one sentence. Copilot
   builds it in its own folder, such as `site/ideas/team-lunch/`, and opens it beside Chat. To
   open it again later, type `/start-website` with your folder's name.
3. **Save (15 minutes).** Save, review, commit, and push, then find your folder on GitHub. Tell
   your helper one thing that works, one thing that does not work yet, and your next step.

Save before 11:45: then Bill Leeson's talk, Building a Project Brain, runs until lunch.

If you are not sure what to ask, try:

> My idea: [your idea in one sentence]. Suggest the smallest first version of this page using
> made-up sample data in the page. No database, login, API keys, integrations, or publishing.
> Ask before replacing a file. After I say yes, build one feature and tell me how to check it myself.

## Improve One Interaction: 13:00-14:00

Add one useful thing: ask for a form, a filter, or a choice. Keep everything else the same, and
compare what you expected with what you see. Then pick one improvement at a time and check it:

- **Clearer words:** ask a neighbor to try the page without your help.
- **Empty entries:** an empty box should not add an empty item.
- **A filter, sort, or count:** compare the result with your made-up entries.
- **Keyboard and narrow window:** buttons are still easy to read and to reach.

Expect -> try -> compare -> improve -> repeat. After each change, check that the older features
still work, and save before you try something big. Copilot in the terminal (CLI) and MCP come on
Wednesday, not today.

## Fixes and Optional Publishing: 14:00-14:45

Fix what you found, one thing at a time, and check it again. Then save, commit, and push. You can
publish your page if you want to, with `/publish-website` and
[Day 1's optional route](DAY-1.md#publish-your-page); a helper can
help. Your preview is enough to finish.

## Show and Plan the Next Step: 14:45-15:00

Show a neighbor one feature, how you checked it, and how it might help your work. A few
volunteers show the room.

Then write down your questions for IT: what real data it would need, who should have access,
which systems it would connect to, and what approval it needs to become a real app.

Last, open **Explorer > site > README.md**, your website's own notes. At the end, under a heading
called **Next**, write two or three things you want your page to do next, one sentence each.
Save, commit, and push. On Wednesday they become your first tickets.

**Done when:** you have a checked first version of your idea (or a better Monday page), your work
is on GitHub, and `site/README.md` lists what you want next. Database connections, automated browser
checks, and public deployment are not completion gates. On Wednesday you will learn a few more
ways to use Copilot on this same work: see the [Day 3 guide](DAY-3.md).

Keep working in this Codespace. Moving an idea to company tools later needs your technical
owner's approval, so save your work and ask first. Never remove training access or delete an
account yourself.

## Optional extras

1. Ask for two other versions of one confusing button, pick one, and check it again.
2. Write a short, plain note for IT that keeps "works today" and "ideas for later" apart.
3. Put your wishes under **Next** in order, the one you want most first.

## Official References

- [Copilot prompting](https://docs.github.com/en/copilot/get-started/best-practices).
- [Review AI-generated edits](https://code.visualstudio.com/docs/agents/run/review-code-edits).
- [Source control in Codespaces](https://docs.github.com/en/codespaces/developing-in-a-codespace/using-source-control-in-your-codespace).
