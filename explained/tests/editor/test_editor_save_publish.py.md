# tests/editor/test_editor_save_publish.py

**What it tests:** Tests for saving and publishing from the editor (issue #98).

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 23 tests** (each name says what must hold):

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
- editor publish can also activate
- editor publish without activate doesnt activate
- the editor has the three buttons with descriptions
- editor publish and activate says when a schedule shows another theme
- the editor save area is only pinned on tall screens
- only a JSON true activates
- activate needs the publish permission
- activate an invalid draft activates nothing
- activate the site theme with nothing new
- publish for a missing theme is not found

Run just this file with `uv run pytest tests/editor/test_editor_save_publish.py`.
