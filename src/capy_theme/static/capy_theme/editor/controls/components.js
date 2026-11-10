// The Components view: every daisyUI component in the draft theme, beside the
// editor panel. It's an iframe (the editor_components page), so its daisyUI
// stylesheet can't change the page being edited. The draft's CSS is put into the
// iframe each time the preview changes, so the components update as you edit.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;
  var view = null;
  var frame = null;
  var toggle = null;

  // Give the iframe's page the draft's CSS: a stylesheet made in the iframe's own
  // window and kept on its document (the window outlives the blank page an
  // iframe starts with, so the document is what tells pages apart).
  function pushCss() {
    var doc = frame && frame.contentDocument;
    if (!doc || !ui.latest || doc.URL === "about:blank") return;
    if (!doc.capyDraftSheet) {
      doc.capyDraftSheet = new frame.contentWindow.CSSStyleSheet();
      doc.adoptedStyleSheets = [doc.capyDraftSheet];
    }
    doc.capyDraftSheet.replaceSync(editor.viewCss || ui.latest.css);
  }

  function build() {
    if (view) return view;
    frame = el("iframe", { title: "Theme components in the draft theme", src: editor.mount.getAttribute("data-components-url") });
    frame.addEventListener("load", pushCss);
    var close = el("button", { type: "button", text: "Close components" });
    close.addEventListener("click", hide);
    view = el("div", { class: "capy-editor-components", role: "region", "aria-label": "Theme components" }, [
      el("div", { class: "capy-editor-components-bar" }, [
        el("strong", { text: "Components in the draft theme" }),
        close,
      ]),
      frame,
    ]);
    view.hidden = true;
    document.body.appendChild(view);
    return view;
  }

  function show() {
    build().hidden = false;
    pushCss();
    if (toggle) toggle.setAttribute("aria-expanded", "true");
  }

  function hide() {
    if (view) view.hidden = true;
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      toggle.focus();
    }
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && view && !view.hidden) hide();
  });
  document.addEventListener("capy-editor:preview", pushCss);
  document.addEventListener("capy-editor:loaded", pushCss);
  document.addEventListener("capy-editor:view", pushCss);
  // After Save draft or Publish, reload it so its images section is up to date.
  document.addEventListener("capy-editor:saved", function () {
    if (frame && frame.contentWindow) frame.contentWindow.location.reload();
  });

  // Closing the editor closes the view too.
  var close = editor.close;
  editor.close = function () {
    close();
    if (editor.panel && editor.panel.hidden) hide();
  };

  ui.sections.push({
    order: 5,
    build: function () {
      toggle = el("button", { type: "button", "data-capy-components": "", "aria-expanded": view && !view.hidden ? "true" : "false", text: "Show all components" });
      toggle.addEventListener("click", function () {
        if (view && !view.hidden) hide();
        else show();
      });
      return el("section", { class: "capy-editor-section", "data-capy-keep": "" }, [
        toggle,
        el("p", { class: "capy-editor-note", text: "Every daisyUI component in the draft theme, light and dark, updating as you edit." }),
      ]);
    },
  });
})();
