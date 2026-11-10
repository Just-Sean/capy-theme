// The editor panel's controls: shared state and helpers, and building the panel.
// Each section (bases, colours, fonts, images, shape, save) is its own file that
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
    scheme: "light", // the colour tab being edited
    latest: null, // the latest values, CSS and contrast from the server
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

  // The colour overrides for one mode, created if missing.
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
    };
    ["colors", "shape", "fonts", "type", "images", "logo", "icon"].forEach(function (key) {
      ui.changes.settings[key] = copy(state.settings[key]);
    });
    editor.changes = normalized();
    ui.baseline = JSON.stringify(editor.changes);
    ui.latest = state;
    var container = editor.panel.querySelector(".capy-editor-controls");
    container.textContent = "";
    ui.sections
      .slice()
      .sort(function (a, b) { return a.order - b.order; })
      .forEach(function (section) {
        container.appendChild(section.build(state));
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
