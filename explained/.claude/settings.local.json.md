# .claude/settings.local.json

**What it is:** this project's local permission settings for Claude Code. Git-ignored, so it stays on this machine.

**What it says:**

- **Allowed without asking:** pushing `issue-*` branches and `v*` tags, deleting pushed `issue-*` branches, the `gh pr`, `gh issue`, `gh release` and `gh api` commands, and one `awk` command.
- **Always refused:** pushing to `main`, and every kind of force-push.

These sit on top of your global `~/.claude/settings.json`. The allows were added during the "autonomous up to v1.0" work so pushing, PRs and merging didn't need a click each time. Your restore-the-ask-rules note says to tighten them again after the release.

**When you'd touch it:** to change what Claude may do here without asking.
