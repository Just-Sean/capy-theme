# src/capy_theme/static/capy_theme/editor/controls/images.js

The **Images** upload part. You choose a slot, light or dark, alt text and a file (the chooser is styled as a button, #223). It shows each slot's size limit.

The upload goes to `upload/`, where the server checks and cleans it, and it's stored at once as a new image of the theme. It isn't used until it's chosen for a slot and published.

Known issue: double-clicking Upload can upload twice (#222).
