# tests/themes/test_publish_admin.py

**What it tests:** Tests for publishing from the admin (issue #12): the theme page's Save draft, Save and publish, and Save, publish and activate buttons, the theme list's row buttons (#273), and the revision list.

**Code it covers:** `src/capy_theme/themes/`

**Its 17 tests** (each name says what must hold):

- edit page has the three buttons with descriptions and status
- save draft stays on the page and doesnt publish
- save and publish publishes the saved draft with the note
- save publish and activate
- publishing with no changes says so
- publish and activate with no changes still activates
- a new theme can be saved and published at once
- edit page lists revisions read only
- saving the edit form doesnt publish
- list shows live revision and unpublished changes
- a simultaneous publish is explained
- staff without change permission cant publish
- publishing explains an invalid draft
- the list has publish buttons on each row
- the row buttons publish and activate
- activating an unpublished theme is refused
- the row buttons only accept post

Run just this file with `uv run pytest tests/themes/test_publish_admin.py`.
