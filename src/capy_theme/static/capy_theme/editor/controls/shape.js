// Editor section: shape and effects (radii, sizes, border, depth, noise).
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

  function sizeRow(size) {
    var input = el("input", {
      type: "number",
      step: "any",
      min: String(size.min),
      max: String(size.max),
      "data-capy-shape": size.name,
      "aria-label": size.label + " (" + size.unit + ")",
    });
    input.addEventListener("input", function () {
      var shape = (ui.changes.settings.shape = ui.changes.settings.shape || {});
      if (input.value === "") delete shape[size.name];
      else shape[size.name] = Number(input.value);
      ui.update();
    });
    return el("label", { class: "capy-editor-field" }, [el("span", { text: size.label + " (" + size.unit + ")" }), input]);
  }

  function effectRow(effect) {
    var select = el("select", { "data-capy-effect": effect.name, "aria-label": effect.label });
    [["", "From the base theme"], ["on", "On"], ["off", "Off"]].forEach(function (pair) {
      select.appendChild(el("option", { value: pair[0], text: pair[1] }));
    });
    select.addEventListener("change", function () {
      var shape = (ui.changes.settings.shape = ui.changes.settings.shape || {});
      if (select.value === "") delete shape[effect.name];
      else shape[effect.name] = select.value === "on";
      ui.update();
    });
    return el("label", { class: "capy-editor-field" }, [el("span", { text: effect.label }), select]);
  }

  function build() {
    var rows = ui.spec.sizes.map(sizeRow).concat(ui.spec.effects.map(effectRow));
    return el("section", { class: "capy-editor-section" }, [
      el("details", {}, [el("summary", { text: "Shape and effects" })].concat(rows)),
    ]);
  }

  function fill() {
    var panel = editor.panel;
    var shape = ui.changes.settings.shape || {};
    panel.querySelectorAll("[data-capy-shape]").forEach(function (input) {
      var name = input.getAttribute("data-capy-shape");
      var size = ui.spec.sizes.find(function (s) { return s.name === name; });
      if (document.activeElement !== input) input.value = name in shape ? shape[name] : "";
      input.placeholder = (ui.latest.values.light[size.variable] || "").replace(size.unit, "");
    });
    panel.querySelectorAll("[data-capy-effect]").forEach(function (select) {
      var name = select.getAttribute("data-capy-effect");
      select.value = name in shape ? (shape[name] ? "on" : "off") : "";
    });
  }

  ui.sections.push({ order: 50, build: build, fill: fill });
})();
