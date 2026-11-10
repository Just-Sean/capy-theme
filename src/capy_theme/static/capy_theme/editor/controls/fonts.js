// Editor section: fonts for each role, and the type scale.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

  // A sample line under each font dropdown, in the chosen font (the preview's
  // CSS loads its files). Set through the CSSOM, so a strict CSP allows it.
  function showSample(role) {
    var sample = editor.panel.querySelector('[data-capy-font-sample="' + role + '"]');
    if (!sample) return;
    var id = (ui.changes.settings.fonts || {})[role];
    var font = ui.spec.fonts.find(function (f) { return f.id === id; });
    sample.style.fontFamily = font ? font.stack : "";
    sample.hidden = !font;
  }

  function fontRow(role) {
    var select = el("select", { "data-capy-font": role.name, "aria-label": role.label + " font" });
    select.appendChild(el("option", { value: "", text: "Default" }));
    ui.spec.fonts.forEach(function (font) {
      select.appendChild(el("option", { value: String(font.id), text: font.family + " (" + font.source + ")" }));
    });
    var sample = el("div", { class: "capy-editor-font-sample", "data-capy-font-sample": role.name, text: "The quick brown fox jumps over the lazy dog" });
    select.addEventListener("change", function () {
      var fonts = (ui.changes.settings.fonts = ui.changes.settings.fonts || {});
      if (select.value === "") delete fonts[role.name];
      else fonts[role.name] = Number(select.value);
      showSample(role.name);
      ui.update();
    });
    return el("div", {}, [el("label", { class: "capy-editor-field" }, [el("span", { text: role.label }), select]), sample]);
  }

  function typeRow(item) {
    var input = el("input", {
      type: "number",
      step: String(item.step),
      min: String(item.min),
      max: String(item.max),
      "data-capy-type": item.name,
      "aria-label": item.label,
    });
    input.addEventListener("input", function () {
      var type = (ui.changes.settings.type = ui.changes.settings.type || {});
      if (input.value === "") delete type[item.name];
      else type[item.name] = Number(input.value);
      ui.update();
    });
    return el("label", { class: "capy-editor-field" }, [el("span", { text: item.label + (item.unit ? " (" + item.unit + ")" : "") }), input]);
  }

  function build() {
    var rows = ui.spec.font_roles.map(fontRow).concat(ui.spec.type.map(typeRow));
    var note = ui.spec.fonts.length
      ? null
      : el("p", { class: "capy-editor-note", text: "The font library is empty. Add fonts in the admin under Capy Theme → Fonts." });
    return el("section", { class: "capy-editor-section" }, [el("h3", { text: "Fonts and type" }), note].concat(rows));
  }

  function fill() {
    var panel = editor.panel;
    var typeSettings = ui.changes.settings.type || {};
    panel.querySelectorAll("[data-capy-type]").forEach(function (input) {
      var name = input.getAttribute("data-capy-type");
      if (document.activeElement !== input) input.value = name in typeSettings ? typeSettings[name] : "";
    });
    var fonts = ui.changes.settings.fonts || {};
    panel.querySelectorAll("[data-capy-font]").forEach(function (select) {
      var role = select.getAttribute("data-capy-font");
      select.value = role in fonts ? String(fonts[role]) : "";
      showSample(role);
    });
  }

  ui.sections.push({ order: 30, build: build, fill: fill });
})();
