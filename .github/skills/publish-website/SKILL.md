---
name: publish-website
description: 'Put the learner''s workshop website on the internet at its own address. Chooses a website name, saves it in config.json, and explains the push that publishes it. Use /publish-website once the page works in the preview.'
argument-hint: 'Optional website name, such as ali-planner'
user-invocable: true
disable-model-invocation: true
---

# Publish My Website

Publishing copies the learner's `site/` folder to the workshop's hosting, where anyone with the
link can open it. GitHub Actions publishes after every push to `main`: nobody signs in to Azure
and no key or secret exists. Never add credentials, edit workflows, run Azure commands, commit,
or push for the learner.

1. Check that `site/index.html` exists. If not, say **"Let's create your website first with
   /create-website."** and stop.
2. Check that `.github/workflows/publish-website.yml` exists. If not, say this copy cannot publish
   and a helper can add it, then stop.
3. Choose the name. If the learner gave one, use it. If `config.json` already has a `websiteName`,
   suggest keeping it, because a new name moves the website to a new address. Otherwise suggest
   the learner's GitHub user name (`echo $GITHUB_USER`) plus one word for the page, such as
   `ali-planner`. Ask one question: use it, or type another.
   - A name has 2-32 lowercase letters, digits and single hyphens, starts with a letter, and ends
     with a letter or digit. Turn capitals into lowercase, and spaces or other characters into
     hyphens.
   - A nickname is fine. No customer, patient or other real business names.
4. In `config.json`, set `"websiteName": "<name>"`. Change nothing else in the file.
5. Hand over in three short lines:
   - **"Your address will be https://<name>.thankfulrock-bf005377.eastus.azurecontainerapps.io"**
   - **"Now save it as usual: Source Control, sparkle message, Commit, then ... > Push. Publishing
     starts by itself and takes about two minutes."**
   - **"On GitHub, Actions > Publish my website shows progress; the link also appears under
     Deployments on your repository page."**

   From Day 4 the learner's `main` is protected by a ruleset that requires a pull request. If a
   push is refused for that reason, or the learner is already on a branch, guide this instead:
   commit on a new branch, **Publish Branch**, create the pull request, and merge it on GitHub.
   Publishing starts after the merge.

   If `site/ideas/` holds idea pages, add one line per idea: its address is the same address
   followed by `/ideas/<folder>/`, such as `.../ideas/team-lunch/`.

When the learner asks whether it is live, first check `git status -sb`: if it says **ahead**, the
change is not on GitHub yet, so guide the push, or the pull request when `main` is protected. Then run
`curl -s https://<name>.thankfulrock-bf005377.eastus.azurecontainerapps.io/healthz`, take its
`commit`, and run `git merge-base --is-ancestor "$(git log -1 --format=%H -- site config.json)" <commit>`.
Success means the newest change to `site/` is live, even when later commits changed only other
files, which do not republish. Anything else means wait a minute and ask again. After that, every
push of `site/` updates the website by itself.

If the run says **That name is taken**, choose another name and repeat from step 4. For any other
red run, show the run's message to a helper; do not change the workflow. The published copy
starts with the page's own example entries. Its **Ask** chat answers there too, about what the
page shows, including chart numbers; photo editing works only in the Website preview. Everything
on the page stays fictional.

Official references: [GitHub Actions](https://docs.github.com/en/actions/get-started/quickstart),
[OpenID Connect in Azure](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure)
and [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/overview).
