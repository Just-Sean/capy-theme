// Editor section: Save draft and Publish.
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

  function publishControls() {
    var note = el("input", { type: "text", "data-capy-note": "", placeholder: "Note for the history (optional)", "aria-label": "Publish note" });
    var publish = el("button", { type: "button", "data-capy-publish": "", text: "Publish" });
    publish.addEventListener("click", function () {
      if (!window.confirm("Publish this theme? Visitors will see it.")) return;
      (editor.isDirty() ? saveDraft() : Promise.resolve())
        .then(function () {
          return editor.post(editor.mount.getAttribute("data-publish-url"), { note: note.value });
        })
        .then(function (reply) {
          note.value = "";
          ui.build(reply.state);
          editor.applyCss(reply.state.css);
          editor.status("Published as revision " + reply.published + ". Visitors now see it.");
          refocus("[data-capy-publish]");
          document.dispatchEvent(new CustomEvent("capy-editor:saved"));
        })
        .catch(function (error) {
          editor.status(error.message, true);
        });
    });
    return el("div", { class: "capy-editor-publish" }, [note, publish]);
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
      el("div", { class: "capy-editor-buttons" }, [save, undo]),
      el("p", { class: "capy-editor-note", id: "capy-editor-revert-note", text: "Revert discards unsaved changes and goes back to the saved draft." }),
      state.can_publish
        ? publishControls()
        : el("p", { class: "capy-editor-note", text: "Publishing needs the publish permission." }),
    ]);
  }

  ui.sections.push({ order: 90, build: build });
})();
