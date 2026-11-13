# src/capy_theme/templates/capy_theme/mode_toggle.html

**What it is:** the HTML for `{% theme_mode_toggle %}`: three daisyUI buttons in a row, **Light / Dark / Auto**.

- Each is a real **link** to `/theme/mode/<mode>/?next=<this page>`, so it works without JavaScript.
- With JavaScript, the head script intercepts the click and switches instantly.
- The current mode has `aria-current="true"`, which screen readers announce. It replaced `aria-pressed`, which isn't allowed on links.
