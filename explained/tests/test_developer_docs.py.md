# tests/test_developer_docs.py

**What it tests:** that `docs/developers.md` matches the code (issue #57).

- **The variables match the stylesheet exactly:** the CSS variables the doc lists are the ones the stylesheet really writes.
- **Every download address works:** each address the doc gives (API, tokens, daisyUI blocks) responds.

If code and docs drift apart, this fails.
