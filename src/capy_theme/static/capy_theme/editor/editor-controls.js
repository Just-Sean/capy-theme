// The editor panel's controls: base themes, colours (light and dark) and shape.
// Every change is previewed straight away through capyEditor.schedulePreview();
// nothing is saved. Loaded after editor.js by templates/capy_theme/editor/mount.html.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor) return;

  // The unsaved values: what the preview endpoint (and later Save) receives.
  var changes = null;
  var spec = null;
  var scheme = "light";
  var latest = null;

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "text") node.textContent = attrs[key];
      else node.setAttribute(key, attrs[key]);
    });
    (children || []).forEach(function (child) {
      if (child) node.appendChild(child);
    });
    return node;
  }

  function colors(mode) {
    changes.settings.colors = changes.settings.colors || {};
    changes.settings.colors[mode] = changes.settings.colors[mode] || {};
    return changes.settings.colors[mode];
  }

  function update() {
    var copy = JSON.parse(JSON.stringify(changes));
    var c = copy.settings.colors || {};
    Object.keys(c).forEach(function (mode) {
      if (!Object.keys(c[mode]).length) delete c[mode];
    });
    if (!Object.keys(c).length) copy.settings.colors = {};
    editor.changes = copy;
    editor.schedulePreview(copy);
  }

  // Base themes

  function baseSelect(mode) {
    var select = el("select", { "data-capy-base": mode, "aria-label": mode + " base theme" });
    spec.bases[mode].forEach(function (name) {
      var option = el("option", { value: name, text: name });
      if (name === changes[mode + "_base"]) option.selected = true;
      select.appendChild(option);
    });
    select.addEventListener("change", function () {
      changes[mode + "_base"] = select.value;
      update();
    });
    return el("label", { class: "capy-editor-field" }, [
      el("span", { text: mode === "light" ? "Light base" : "Dark base" }),
      select,
    ]);
  }

  // Colours

  function colorRow(color) {
    var text = el("input", {
      type: "text",
      "data-capy-color": color.name,
      "aria-label": color.label + " (any colour format)",
      spellcheck: "false",
    });
    var picker = el("input", { type: "color", "data-capy-picker": color.name, "aria-label": "Pick " + color.label });
    var reset = el("button", { type: "button", "data-capy-reset": color.name, title: "Use the base theme's colour", text: "Reset" });
    var badge = el("span", { class: "capy-editor-badge", "data-capy-badge": color.name });

    picker.addEventListener("input", function () {
      text.value = picker.value;
      colors(scheme)[color.name] = picker.value;
      update();
    });
    text.addEventListener("change", function () {
      if (text.value.trim()) colors(scheme)[color.name] = text.value.trim();
      else delete colors(scheme)[color.name];
      update();
    });
    reset.addEventListener("click", function () {
      delete colors(scheme)[color.name];
      text.value = "";
      update();
    });
    return el("div", { class: "capy-editor-color" }, [
      el("span", { class: "capy-editor-color-label", text: color.label }),
      picker,
      text,
      reset,
      badge,
    ]);
  }

  function colorSection() {
    var tabs = el("div", { class: "capy-editor-tabs", role: "tablist" });
    ["light", "dark"].forEach(function (mode) {
      var tab = el("button", {
        type: "button",
        role: "tab",
        "data-capy-scheme": mode,
        "aria-selected": mode === scheme ? "true" : "false",
        text: mode === "light" ? "Light colours" : "Dark colours",
      });
      tab.addEventListener("click", function () {
        scheme = mode;
        tabs.querySelectorAll("[data-capy-scheme]").forEach(function (t) {
          t.setAttribute("aria-selected", t.getAttribute("data-capy-scheme") === mode ? "true" : "false");
        });
        fill();
      });
      tabs.appendChild(tab);
    });
    var groups = spec.color_groups.map(function (group, index) {
      var details = el("details", index === 0 ? { open: "" } : {}, [el("summary", { text: group.name })]);
      group.colors.forEach(function (color) {
        details.appendChild(colorRow(color));
      });
      return details;
    });
    return el("section", { class: "capy-editor-section" }, [el("h3", { text: "Colours" }), tabs].concat(groups));
  }

  // Shape

  function shapeSection() {
    var rows = spec.sizes.map(function (size) {
      var input = el("input", {
        type: "number",
        step: "any",
        min: String(size.min),
        max: String(size.max),
        "data-capy-shape": size.name,
        "aria-label": size.label + " (" + size.unit + ")",
      });
      input.addEventListener("input", function () {
        var shape = (changes.settings.shape = changes.settings.shape || {});
        if (input.value === "") delete shape[size.name];
        else shape[size.name] = Number(input.value);
        update();
      });
      return el("label", { class: "capy-editor-field" }, [el("span", { text: size.label + " (" + size.unit + ")" }), input]);
    });
    spec.effects.forEach(function (effect) {
      var select = el("select", { "data-capy-effect": effect.name, "aria-label": effect.label });
      [["", "From the base theme"], ["on", "On"], ["off", "Off"]].forEach(function (pair) {
        select.appendChild(el("option", { value: pair[0], text: pair[1] }));
      });
      select.addEventListener("change", function () {
        var shape = (changes.settings.shape = changes.settings.shape || {});
        if (select.value === "") delete shape[effect.name];
        else shape[effect.name] = select.value === "on";
        update();
      });
      rows.push(el("label", { class: "capy-editor-field" }, [el("span", { text: effect.label }), select]));
    });
    return el("section", { class: "capy-editor-section" }, [
      el("details", {}, [el("summary", { text: "Shape and effects" })].concat(rows)),
    ]);
  }

  // Showing the latest values

  function fill() {
    if (!latest) return;
    var panel = editor.panel;
    var chosen = (changes.settings.colors || {})[scheme] || {};
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
    var shape = changes.settings.shape || {};
    panel.querySelectorAll("[data-capy-shape]").forEach(function (input) {
      var name = input.getAttribute("data-capy-shape");
      var size = spec.sizes.find(function (s) { return s.name === name; });
      if (document.activeElement !== input) input.value = name in shape ? shape[name] : "";
      input.placeholder = (latest.values.light[size.variable] || "").replace(size.unit, "");
    });
    panel.querySelectorAll("[data-capy-effect]").forEach(function (select) {
      var name = select.getAttribute("data-capy-effect");
      select.value = name in shape ? (shape[name] ? "on" : "off") : "";
    });
  }

  function build(state) {
    spec = state.controls;
    changes = {
      light_base: state.light_base,
      dark_base: state.dark_base,
      settings: {
        colors: JSON.parse(JSON.stringify(state.settings.colors || {})),
        shape: JSON.parse(JSON.stringify(state.settings.shape || {})),
      },
    };
    editor.changes = JSON.parse(JSON.stringify(changes));
    latest = state;
    var container = editor.panel.querySelector(".capy-editor-controls");
    container.textContent = "";
    container.appendChild(
      el("section", { class: "capy-editor-section" }, [el("h3", { text: "Base themes" }), baseSelect("light"), baseSelect("dark")])
    );
    container.appendChild(colorSection());
    container.appendChild(shapeSection());
    fill();
  }

  document.addEventListener("capy-editor:loaded", function (event) {
    build(event.detail);
  });
  document.addEventListener("capy-editor:preview", function (event) {
    latest = event.detail;
    fill();
  });
})();
