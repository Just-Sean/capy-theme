// Editor section: Save draft, Revert, Save and publish, and Save, publish and
// activate, each with what it does, as on the admin's theme page (#273).
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

  // The controls are rebuilt after Save and Publish, which removes the button
  // that was pressed; focus moves to its replacement so it isn't lost (#245).
  function refocus(selector) {
    var button = editor.panel && editor.panel.querySelector(selector);
    if (button) button.focus();
  }

  function saveDraft() {
    return editor
      .post(editor.mount.getAttribute("data-save-url"), editor.changes)
      .then(function (reply) {
        ui.build(reply.state);
        editor.applyCss(reply.state.css);
        editor.status("Draft saved. Visitors won't see it until it's published.");
        refocus("[data-capy-save]");
        document.dispatchEvent(new CustomEvent("capy-editor:saved"));
        return reply;
      })
      .catch(function (error) {
        editor.status(error.message, true);
        throw error;
      });
  }

  // Throw away the unsaved changes and go back to the last saved draft (#261).
  function revert() {
    if (!editor.isDirty()) {
      editor.status("Nothing to revert: there are no unsaved changes.");
      return;
    }
    if (!window.confirm("Discard your unsaved changes and go back to the saved draft?")) return;
    editor.cancelPreview();
    ui.build(ui.saved);
    editor.applyCss(ui.saved.css);
    document.dispatchEvent(new CustomEvent("capy-editor:preview", { detail: ui.saved }));
    editor.status("Unsaved changes discarded. Showing the saved draft.");
    refocus("[data-capy-revert]");
  }

  // Save and publish, and Save, publish and activate (#273): any unsaved changes are
  // saved first, then the draft is published (and the theme made the default theme).
  function publishTo(note, activate) {
    var question = activate
      ? "Save, publish and make this the default theme? Visitors will see it."
      : "Save and publish this theme? Visitors will see it wherever it's used.";
    if (!window.confirm(question)) return;
    (editor.isDirty() ? saveDraft() : Promise.resolve())
      .then(function () {
        var data = { note: note.value };
        if (activate) data.activate = true;
        return editor.post(editor.mount.getAttribute("data-publish-url"), data);
      })
      .then(function (reply) {
        note.value = "";
        ui.build(reply.state);
        editor.applyCss(reply.state.css);
        var done = reply.published ? "Published as revision " + reply.published + "." : "Nothing new to publish.";
        var after = " Visitors see it wherever this theme is used.";
        if (reply.activated) {
          after = reply.showing
            ? " It's now the default theme, but a theme schedule is showing “" + reply.showing + "” right now."
            : " It's now the default theme.";
        }
        editor.status(done + after);
        refocus(activate && !reply.state.is_site_theme ? "[data-capy-publish-activate]" : "[data-capy-publish]");
        document.dispatchEvent(new CustomEvent("capy-editor:saved"));
      })
      .catch(function (error) {
        editor.status(error.message, true);
      });
  }

  // A button with its one-line description, as on the admin's theme page.
  function described(button, id, text) {
    button.setAttribute("aria-describedby", id);
    return el("div", { class: "capy-editor-described" }, [button, el("p", { class: "capy-editor-note", id: id, text: text })]);
  }

  function publishControls(state) {
    var note = el("input", { type: "text", id: "capy-editor-publish-note", "data-capy-note": "", maxlength: "2000" });
    var publish = el("button", { type: "button", "data-capy-publish": "", text: "Save and publish" });
    publish.addEventListener("click", function () {
      publishTo(note, false);
    });
    var parts = [
      // Above the buttons, so it's filled in before publishing (#273).
      el("label", { class: "capy-editor-stack", for: "capy-editor-publish-note" }, [el("span", { text: "Note for the history (optional, kept when you publish)" }), note]),
      described(publish, "capy-editor-publish-help", "Saves, then makes this version of the theme live. Visitors see it wherever this theme is used."),
    ];
    if (state.is_site_theme) {
      parts.push(el("p", { class: "capy-editor-note", text: "This is already the default theme, so Save and publish updates what the site shows." }));
    } else {
      var both = el("button", { type: "button", "data-capy-publish-activate": "", text: "Save, publish and activate" });
      both.addEventListener("click", function () {
        publishTo(note, true);
      });
      parts.push(described(both, "capy-editor-activate-help", "Saves, publishes, then makes this the default theme: the one the site shows."));
    }
    return el("div", { class: "capy-editor-publish" }, parts);
  }

  function build(state) {
    var save = el("button", { type: "button", class: "capy-editor-primary", "data-capy-save": "", text: "Save draft" });
    save.addEventListener("click", function () {
      saveDraft().catch(function () {});
    });
    var undo = el("button", { type: "button", "data-capy-revert": "", "aria-describedby": "capy-editor-revert-note", text: "Revert" });
    undo.addEventListener("click", revert);
    return el("section", { class: "capy-editor-section capy-editor-actions" }, [
      el("h3", { text: "Save and publish" }),
      el("p", { class: "capy-editor-note", "data-capy-dirty": "", "aria-live": "polite" }),
      described(save, "capy-editor-save-help", "Saves your changes. Visitors see nothing until you publish."),
      el("div", { class: "capy-editor-buttons" }, [undo]),
      el("p", { class: "capy-editor-note", id: "capy-editor-revert-note", text: "Revert discards unsaved changes and goes back to the saved draft." }),
      state.can_publish
        ? publishControls(state)
        : el("p", { class: "capy-editor-note", text: "You can save drafts. To publish, ask someone who can publish themes (permission “Can publish, activate and restore themes”)." }),
    ]);
  }

  ui.sections.push({ order: 90, build: build });
})();
