// Editor section: the 20 colors, with light and dark tabs and contrast badges.
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
      ui.colors(ui.scheme)[color.name] = picker.value;
      ui.update();
    });
    text.addEventListener("change", function () {
      if (text.value.trim()) ui.colors(ui.scheme)[color.name] = text.value.trim();
      else delete ui.colors(ui.scheme)[color.name];
      ui.update();
    });
    reset.addEventListener("click", function () {
      delete ui.colors(ui.scheme)[color.name];
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

  function tabs() {
    var list = el("div", { class: "capy-editor-tabs", role: "tablist" });
    ["light", "dark"].forEach(function (mode) {
      var tab = el("button", {
        type: "button",
        role: "tab",
        "data-capy-scheme": mode,
        "aria-selected": mode === ui.scheme ? "true" : "false",
        text: mode === "light" ? "Light colors" : "Dark colors",
      });
      tab.addEventListener("click", function () {
        ui.scheme = mode;
        list.querySelectorAll("[data-capy-scheme]").forEach(function (t) {
          t.setAttribute("aria-selected", t.getAttribute("data-capy-scheme") === mode ? "true" : "false");
        });
        ui.fill();
      });
      list.appendChild(tab);
    });
    return list;
  }

  function build() {
    var groups = ui.spec.color_groups.map(function (group, index) {
      var details = el("details", index === 0 ? { open: "" } : {}, [el("summary", { text: group.name })]);
      group.colors.forEach(function (color) {
        details.appendChild(colorRow(color));
      });
      return details;
    });
    return el("section", { class: "capy-editor-section" }, [
      el("h3", { text: "Colors" }),
      tabs(),
      ui.suggestionBox(),
    ].concat(groups));
  }

  // Each color's value (typed or worked out), its picker and its contrast badge.
  function fill() {
    var panel = editor.panel;
    var scheme = ui.scheme;
    var latest = ui.latest;
    var chosen = (ui.changes.settings.colors || {})[scheme] || {};
    var ratings = {};
    (latest.contrast[scheme] || []).forEach(function (entry) {
      ratings[entry.background] = ratings[entry.background] || entry;
      ratings[entry.text] = ratings[entry.text] || entry;
    });
    panel.querySelectorAll("[data-capy-color]").forEach(function (input) {
      var name = input.getAttribute("data-capy-color");
      var value = latest.values[scheme]["--color-" + name];
      if (document.activeElement !== input) input.value = chosen[name] || "";
      input.placeholder = value;
      var picker = panel.querySelector('[data-capy-picker="' + name + '"]');
      if (document.activeElement !== picker) picker.value = latest.hex[scheme][name];
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
