// The editor panel's controls: shared state and helpers, and building the panel.
// Each section (bases, colors, fonts, images, shape, save) is its own file that
// adds itself to ui.sections with build() and, if it shows values, fill().
// Every change is previewed straight away through capyEditor.schedulePreview();
// nothing is saved until Save draft. Loaded after editor.js by editor/mount.html.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor) return;

  var ui = (editor.ui = {
    changes: null, // the unsaved values: what the preview and Save receive
    baseline: "", // the values as last loaded or saved, to tell if anything changed
    spec: null, // what the panel offers (from the server)
    scheme: "light", // the color tab being edited
    latest: null, // the latest values, CSS and contrast from the server
    saved: null, // the state as last loaded or saved, which Revert goes back to
    assets: [], // the theme's uploaded images (image-slot.js adds new uploads)
    sections: [], // {order, build(state) -> element, fill()} from each section file
  });

  ui.el = function (tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "text") node.textContent = attrs[key];
      else node.setAttribute(key, attrs[key]);
    });
    (children || []).forEach(function (child) {
      if (child) node.appendChild(child);
    });
    return node;
  };

  // A panel section that folds: its title is a heading inside <summary>. Starts folded.
  ui.section = function (title, children) {
    var fold = ui.el("details", { class: "capy-editor-fold", "data-capy-fold": title }, [
      ui.el("summary", {}, [ui.el("h3", { text: title })]),
    ].concat(children));
    return ui.el("section", { class: "capy-editor-section" }, [fold]);
  };

  // The color overrides for one mode, created if missing.
  ui.colors = function (mode) {
    var settings = ui.changes.settings;
    settings.colors = settings.colors || {};
    settings.colors[mode] = settings.colors[mode] || {};
    return settings.colors[mode];
  };

  // The values without empty groups, so "nothing changed" compares equal.
  function normalized() {
    var copy = JSON.parse(JSON.stringify(ui.changes));
    var c = copy.settings.colors || {};
    Object.keys(c).forEach(function (mode) {
      if (!Object.keys(c[mode]).length) delete c[mode];
    });
    if (!Object.keys(c).length) copy.settings.colors = {};
    var images = copy.settings.images || {};
    Object.keys(images).forEach(function (slot) {
      if (!Object.keys(images[slot]).length) delete images[slot];
    });
    return copy;
  }

  ui.update = function () {
    editor.changes = normalized();
    editor.schedulePreview(editor.changes);
    ui.showDirty();
  };

  editor.isDirty = function () {
    return !!ui.changes && JSON.stringify(normalized()) !== ui.baseline;
  };

  ui.showDirty = function () {
    var note = editor.panel && editor.panel.querySelector("[data-capy-dirty]");
    if (note) note.textContent = editor.isDirty() ? "Unsaved changes." : "No unsaved changes.";
  };

  // Show the latest values in every section.
  ui.fill = function () {
    if (!ui.latest) return;
    ui.sections.forEach(function (section) {
      if (section.fill) section.fill();
    });
  };

  // (Re)build the panel from the server's state.
  ui.build = function (state) {
    var copy = function (value) {
      return JSON.parse(JSON.stringify(value || {}));
    };
    ui.spec = state.controls;
    ui.changes = {
      light_base: state.light_base,
      dark_base: state.dark_base,
      settings: {},
      alts: {}, // edited alt text: {image id: text}, saved with the draft (#271)
    };
    ["colors", "shape", "fonts", "type", "images", "logo", "icon"].forEach(function (key) {
      ui.changes.settings[key] = copy(state.settings[key]);
    });
    editor.changes = normalized();
    ui.baseline = JSON.stringify(editor.changes);
    ui.latest = state;
    ui.saved = state;
    ui.assets = state.assets || [];
    var container = editor.panel.querySelector(".capy-editor-controls");
    // Every fold keeps how you left it, open or folded, when the panel is rebuilt
    // (Save draft, Publish, Revert).
    var wasOpen = {};
    container.querySelectorAll("[data-capy-fold]").forEach(function (fold) {
      wasOpen[fold.getAttribute("data-capy-fold")] = fold.open;
    });
    container.textContent = "";
    ui.sections
      .slice()
      .sort(function (a, b) { return a.order - b.order; })
      .forEach(function (section) {
        container.appendChild(section.build(state));
      });
    container.querySelectorAll("[data-capy-fold]").forEach(function (fold) {
      var name = fold.getAttribute("data-capy-fold");
      if (name in wasOpen) fold.open = wasOpen[name];
    });
    ui.fill();
    ui.showDirty();
  };

  document.addEventListener("capy-editor:loaded", function (event) {
    ui.build(event.detail);
  });
  document.addEventListener("capy-editor:preview", function (event) {
    ui.latest = event.detail;
    ui.fill();
  });
})();
