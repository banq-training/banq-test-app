---
name: stop-website
description: 'Close the workshop Website preview panel without deleting files or affecting other editors. There is no server to stop. Use /stop-website; /start-website reopens the saved website.'
user-invocable: true
disable-model-invocation: true
---

# Stop My Website

Close only the workshop's **Website preview** panel. Do not edit, delete, reset, commit, or
recreate website files. Do not close other editors or stop the Codespace; closing the preview
does not stop Codespaces billing.

Run this yourself from the repository root:

```bash
python3 scripts/website_preview.py stop
```

Require `previewOpen: false` in the result before saying it closed. An already closed preview
stays closed. There is no server, so nothing else needs stopping. Do not use `pkill`, `killall`,
port-wide kill commands, or Close All Editors.

Then say **"Preview closed. Your files are unchanged. Use /start-website to open them again."**
Saved entries stay in this browser. Saving, reviewing, and pushing remain separate learner actions.

Related workflow: [Start Website](../start-website/SKILL.md).
