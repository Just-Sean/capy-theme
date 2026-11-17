# src/capy_theme/templates/capy_theme/admin/theme_change_form.html

Extends the admin's edit page to add buttons at the top right: **Edit live** (opens the theme in the live editor), **Revisions** and **Export**. They sit beside Django's own History.

At the bottom, Django's save buttons are replaced by the **Save and publish** area (`save_publish.html`, #273): a status line, Save draft, Save and publish, and Save, publish and activate. It loads `save_publish.css` for it.

It also groups the page's sections and its Images and Published revisions lists into tab panels (`capy_theme.admin.tabs`), and loads `tabs.js` and `tabs.css` to turn them into tabs. Without JavaScript, the panels follow each other and the page reads top to bottom.
