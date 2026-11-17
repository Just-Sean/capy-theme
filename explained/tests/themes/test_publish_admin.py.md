# tests/themes/test_publish_admin.py

**What it tests:** Tests for publishing from the admin (issue #12): the theme page's Save draft, Save and publish, and Save, publish and activate buttons, the theme list's row buttons (#273), and the revision list.

**Code it covers:** `src/capy_theme/themes/`

**Its 42 tests** (each name says what must hold):

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
- a non numeric id on the theme page isnt a server error
- a non numeric id on a row button is not found
- a row button for a missing theme is not found
- save draft in a popup closes the popup
- an add only user isnt sent to a page they cant open
- the publish note survives a form error
- activate during a running schedule doesnt claim success
- the default theme isnt offered activate during a schedule
- a scheduled theme can still be made the default
- without a capy button django buttons still work
- several buttons at once do the first one
- a very long note is cut to 2000 characters
- a form error publishes and activates nothing
- view only users have no buttons and cant post them
- row buttons need login
- activating the site theme again keeps one assignment
- the status line and active column agree after activating
- the status says when a schedule shows another theme
- publishing buttons ask first and save draft doesnt
- the buttons look like admin buttons
- the note is above the buttons and a draft save says its not kept
- a popup has no activate button
- view only users get a close link
- the delete link keeps the lists filters
- row buttons go back to the filtered list

Run just this file with `uv run pytest tests/themes/test_publish_admin.py`.
