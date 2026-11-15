# src/capy_theme/templates/capy_theme/admin/theme_change_form.html

Extends the admin's edit page to add buttons at the top right: **Edit live** (opens the theme in the live editor), **Revisions**, **Export**, and **Publish** for users who may publish. They sit beside Django's own History.

It also groups the page's sections and its Images and Published revisions lists into tab panels (`capy_theme.admin.tabs`), and loads `tabs.js` and `tabs.css` to turn them into tabs. Without JavaScript, the panels follow each other and the page reads top to bottom.
