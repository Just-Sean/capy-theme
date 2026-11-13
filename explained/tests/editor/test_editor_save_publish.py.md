# tests/editor/test_editor_save_publish.py

**What it tests:** Tests for saving and publishing from the editor (issue #98).

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 13 tests** (each name says what must hold):

- save stores the draft and keeps other settings
- saving doesnt publish
- save refuses invalid values and changes nothing
- save needs change permission
- publish needs the publish permission
- publish makes a revision with the note
- publish with nothing new says so
- publish button only for publishers
- mount passes save and publish urls
- bad json is refused and nothing changes
- publish refuses an invalid saved draft
- a real collision leaves the database clean
- publishing at the same moment as someone else

Run just this file with `uv run pytest tests/editor/test_editor_save_publish.py`.
