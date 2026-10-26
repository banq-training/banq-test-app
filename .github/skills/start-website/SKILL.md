---
name: start-website
description: 'Open or reopen the saved workshop website in the Website preview panel beside Chat. No server or port; the panel redraws on every change. Use /start-website after creation or when the preview is closed. Never recreates files.'
argument-hint: 'Optional HTML entry relative to site/'
user-invocable: true
disable-model-invocation: true
---

# Start My Website

Open the saved website beside Chat. Do not repeat the interview, generate or change files,
install anything, or start a server. This also runs right after a build in
[Create Website](../create-website/SKILL.md).

1. Default to `site/index.html`, or the learner's requested HTML file under site/. If they give
   only an idea's folder name, such as `team-lunch`, use `ideas/team-lunch/index.html`. If it does
   not exist, say **"Let's create your website first with /create-website."** Do not create a placeholder.
2. Run this yourself from the repository root; do not ask the learner to type it:

   ```bash
   python3 scripts/website_preview.py start
   ```

   For a separate agreed page pass its path relative to site/, for example
   `python3 scripts/website_preview.py start ideas/my-list/index.html`.
3. Require `previewOpen: true` in the result, then ask **"Can you see your page beside Chat?"**
   A command result alone does not prove the page rendered, and you cannot see the panel
   yourself, so wait for their answer instead of describing the page back to them.

The **Website preview** panel reads the file directly: no server, no port, no sign-in, and no
separate browser tab. It redraws when any file in site/ changes. Entries the learner added stay,
because the page remembers them in this browser. The learner can also open it from the
**Open Preview** button at the top right of any HTML file under site/.

If the command reports that the helper is not active, stop and show the exact message to the
facilitator. Do not install tools, change port settings, or loop through retries. If the panel
shows "Preview needs attention", read the message and fix only the named file problem.

Once visible, say **"Tell me one change and watch it appear here. Use /stop-website to close
the preview; your files stay saved."** Do not commit or push.

Official reference: [VS Code webviews](https://code.visualstudio.com/api/extension-guides/webview).
