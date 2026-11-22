// Editor section: the 20 colors, with contrast badges. A theme is a single scheme,
// so there is one set of colors (no light/dark tabs).
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

  function colorRow(color) {
    var text = el("input", {
      type: "text",
      "data-capy-color": color.name,
      "aria-label": color.label + " (any color format)",
      spellcheck: "false",
    });
    var picker = el("input", { type: "color", "data-capy-picker": color.name, "aria-label": "Pick " + color.label });
    var reset = el("button", { type: "button", "data-capy-reset": color.name, title: "Use the base theme's color", text: "Reset" });
    var badge = el("span", { class: "capy-editor-badge", "data-capy-badge": color.name });

    picker.addEventListener("input", function () {
      text.value = picker.value;
      ui.colors()[color.name] = picker.value;
      ui.update();
    });
    text.addEventListener("change", function () {
      if (text.value.trim()) ui.colors()[color.name] = text.value.trim();
      else delete ui.colors()[color.name];
      ui.update();
    });
    reset.addEventListener("click", function () {
      delete ui.colors()[color.name];
      text.value = "";
      ui.update();
    });
    return el("div", { class: "capy-editor-color" }, [
      el("span", { class: "capy-editor-color-label", text: color.label }),
      picker,
      text,
      reset,
      badge,
    ]);
  }

  function build() {
    var groups = ui.spec.color_groups.map(function (group) {
      var details = el("details", { "data-capy-fold": "Colors: " + group.name }, [el("summary", { text: group.name })]);
      group.colors.forEach(function (color) {
        details.appendChild(colorRow(color));
      });
      return details;
    });
    return ui.section("Colors", [ui.suggestionBox()].concat(groups));
  }

  // Each color's value (typed or worked out), its picker and its contrast badge.
  function fill() {
    var panel = editor.panel;
    var latest = ui.latest;
    var chosen = ui.changes.settings.colors || {};
    var ratings = {};
    (latest.contrast || []).forEach(function (entry) {
      ratings[entry.background] = ratings[entry.background] || entry;
      ratings[entry.text] = ratings[entry.text] || entry;
    });
    panel.querySelectorAll("[data-capy-color]").forEach(function (input) {
      var name = input.getAttribute("data-capy-color");
      var value = latest.values["--color-" + name];
      if (document.activeElement !== input) input.value = chosen[name] || "";
      input.placeholder = value;
      var picker = panel.querySelector('[data-capy-picker="' + name + '"]');
      if (document.activeElement !== picker) picker.value = latest.hex[name];
      var row = input.closest(".capy-editor-color");
      row.classList.toggle("capy-editor-overridden", name in chosen);
      var badge = panel.querySelector('[data-capy-badge="' + name + '"]');
      var entry = ratings[name];
      badge.textContent = entry ? (entry.rating === "fail" ? "⚠ " : "") + entry.rating + " " + entry.ratio : "";
      badge.className = "capy-editor-badge" + (entry && entry.rating === "fail" ? " capy-editor-fail" : "");
      badge.title = entry ? "Contrast with its pair (AA needs 4.5:1)" : "";
    });
  }

  ui.sections.push({ order: 20, build: build, fill: fill });
})();
