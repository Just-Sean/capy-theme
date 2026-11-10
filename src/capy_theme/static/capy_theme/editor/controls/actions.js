// Editor section: Save draft and Publish.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

  function saveDraft() {
    return editor
      .post(editor.mount.getAttribute("data-save-url"), editor.changes)
      .then(function (reply) {
        ui.build(reply.state);
        editor.applyCss(reply.state.css);
        editor.status("Draft saved. Visitors won't see it until it's published.");
        return reply;
      })
      .catch(function (error) {
        editor.status(error.message, true);
        throw error;
      });
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
    return el("section", { class: "capy-editor-section capy-editor-actions" }, [
      el("h3", { text: "Save and publish" }),
      el("p", { class: "capy-editor-note", "data-capy-dirty": "", "aria-live": "polite" }),
      save,
      state.can_publish
        ? publishControls()
        : el("p", { class: "capy-editor-note", text: "Publishing needs the publish permission." }),
    ]);
  }

  ui.sections.push({ order: 90, build: build });
})();
