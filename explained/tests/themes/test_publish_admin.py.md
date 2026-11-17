# tests/themes/test_publish_admin.py

**What it tests:** Tests for publishing from the admin (issue #12): the theme page's Save draft, Save and publish, and Save, publish and activate buttons, the theme list's row buttons (#273), and the revision list.

**Code it covers:** `src/capy_theme/themes/`

**Its 74 tests** (each name says what must hold):

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
- the buttons keep the lists filters like save and continue
- save draft on add keeps the lists filters
- the delete link keeps the filters after save draft
- the status after a form error describes the saved draft
- an add only user gets one success message
- a popup save leaves no message for the next page
- a publisher who cant view themes lands somewhere they can open
- the list doesnt query the default theme for every row
- the delete link honors show delete
- the delete and close links get djangos button look
- qa odd filters survive each button and the next page
- qa add page buttons keep odd filters
- qa popup add answers as a popup and leaves no message
- qa popup change answers as a popup and leaves no message
- qa popup with filters still answers as a popup
- qa popup for a non publisher keeps the refusal
- qa add only publisher gets a page they can open
- qa publisher without view sees the message where they land
- qa status after a failed post for the default theme
- qa failed post keeps what was typed in the form
- qa post for a theme deleted after the page was opened
- qa theme deleted while a failed post is checked
- qa list search filter order and count with the annotation
- qa list pagination marks the default on every page
- qa delete action works with the annotated list
- qa delete and history pages work with the annotation
- qa import and export pages still work
- qa close link for a viewer keeps odd filters
- qa show delete false from extra context hides delete
- qa no delete or close link in a popup
- qa the annotation as a url filter isnt a server error
- qa a failed publish in a popup still closes the popup

Run just this file with `uv run pytest tests/themes/test_publish_admin.py`.
