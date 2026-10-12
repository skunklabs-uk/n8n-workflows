# Issue tracker: GitHub

**Status:** Active

Issues and specs for this repository live in `skunklabs-uk/n8n-workflows` GitHub Issues.

Use `gh issue` and `gh api` in a checked-out repository when available. A connected GitHub tool providing equivalent read/write semantics is acceptable; do not infer that a particular local CLI is installed.

## Conventions

- Create: `gh issue create --title "..." --body "..."`.
- Read: `gh issue view <number> --comments`.
- List: `gh issue list --state open --json number,title,body,labels`.
- Comment: `gh issue comment <number> --body "..."`.
- Label: `gh issue edit <number> --add-label "..."`.
- Close: `gh issue close <number> --comment "..."`.
- Use GitHub native sub-issues/dependencies when available; otherwise declare blockers as `Blocked by: #<number>` in the issue.
- PRs as a triage/request surface: **no**.

When a skill says "publish to the issue tracker", create a GitHub issue.
When a skill says "fetch the relevant ticket", read the issue and its comments.
