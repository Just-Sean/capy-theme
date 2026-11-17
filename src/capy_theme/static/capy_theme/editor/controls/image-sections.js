// Editor sections for images, named like the admin's (#271): Logos (the main logo,
// its heights, and the other logo versions folded away), Icon (with a preview of
// its background and padding), Backgrounds and Sharing image. Each slot is a
// ui.slotControl (image-slot.js). Saved with Save draft like everything else.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;
  var drawIcon = null;
  document.addEventListener("capy-editor:preview", function () {
    if (drawIcon) drawIcon();
  });

  function spec(name) {
    return ui.spec.image_slots.find(function (s) { return s.name === name; });
  }

  function controls(names) {
    var nodes = [];
    names.forEach(function (name) {
      var s = spec(name);
      s.modes.forEach(function (mode) {
        nodes.push(ui.slotControl(s, mode));
      });
    });
    return nodes;
  }

  function field(text, input) {
    return el("label", { class: "capy-editor-field" }, [el("span", { text: text }), input]);
  }

  function heightInput(item) {
    var input = el("input", { type: "number", min: "16", max: "200", step: "1", placeholder: String(item.default), "data-capy-logo-height": item.name, "aria-label": item.label });
    input.value = (ui.changes.settings.logo || {})[item.name] || "";
    input.addEventListener("input", function () {
      var logo = (ui.changes.settings.logo = ui.changes.settings.logo || {});
      if (input.value === "") delete logo[item.name];
      else logo[item.name] = Number(input.value);
      ui.update();
    });
    return field(item.label, input);
  }

  function iconInput(item, onChange) {
    var input = item.name === "padding"
      ? el("input", { type: "number", min: "0", max: "25", step: "1", placeholder: "0" })
      : el("input", { type: "text", maxlength: "7", placeholder: "Transparent, or e.g. #ffffff" });
    input.setAttribute("data-capy-icon", item.name);
    input.setAttribute("aria-label", item.label);
    input.title = item.help;
    var icon = ui.changes.settings.icon || {};
    input.value = icon[item.name] === undefined ? "" : icon[item.name];
    input.addEventListener("input", function () {
      var settings = (ui.changes.settings.icon = ui.changes.settings.icon || {});
      if (input.value === "") delete settings[item.name];
      else settings[item.name] = item.name === "padding" ? Number(input.value) : input.value.trim();
      ui.update();
      onChange();
    });
    return field(item.label, input);
  }

  // Roughly how the icon will look (its background and padding). The real icons
  // are made when publishing; the browser tab shows the draft icon meanwhile.
  function iconPreview() {
    var box = el("div", { class: "capy-editor-icon-preview", "aria-hidden": "true" });
    function draw() {
      box.textContent = "";
      var id = ((ui.changes.settings.images || {}).icon || {}).light;
      var image = ui.assets.find(function (a) { return a.id === id; });
      var settings = ui.changes.settings.icon || {};
      box.style.backgroundColor = /^#[0-9a-fA-F]{6}$/.test(settings.background || "") ? settings.background : "transparent";
      box.style.padding = Math.min(Math.max(Number(settings.padding) || 0, 0), 25) + "%";
      if (image) box.appendChild(el("img", { src: image.url, alt: "" }));
      else box.appendChild(el("span", { text: "No icon" }));
    }
    draw();
    drawIcon = draw; // the panel is rebuilt on Save and Revert: only the newest draws
    return { node: el("div", { class: "capy-editor-field" }, [el("span", { text: "Preview" }), box]), draw: draw };
  }

  function logos() {
    var others = ["logo_stacked", "logo_mark", "logo_wordmark", "logo_email", "logo_print"];
    var more = el("details", { "data-capy-fold": "Logos: More logo versions" }, [
      el("summary", { text: "More logo versions (optional)" }),
      el("p", { class: "capy-editor-note", text: "Optional versions of your logo for particular places. Each one says what it's for. Any you leave empty use the main logo, so you only need these if your logo should look different there." }),
    ].concat(controls(others)));
    return ui.section(
      "Logos",
      controls(["logo_main"]).concat(ui.spec.logo_heights.map(heightInput), [more])
    );
  }

  function icon() {
    var preview = iconPreview();
    return ui.section(
      "Icon",
      controls(["icon"]).concat(
        ui.spec.icon_settings.map(function (item) { return iconInput(item, preview.draw); }),
        [preview.node]
      )
    );
  }

  ui.sections.push({ order: 40, build: logos });
  ui.sections.push({ order: 41, build: icon });
  ui.sections.push({ order: 42, build: function () { return ui.section("Backgrounds", controls(["background_login", "background_pattern"])); } });
  ui.sections.push({ order: 43, build: function () { return ui.section("Sharing image", controls(["social"])); } });
})();
