// The images section's choices: which uploaded image each slot uses (light and
// dark), the header logo heights, and the icon's background and padding.
// Saved with Save draft like everything else.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

  function field(text, input) {
    return el("label", { class: "capy-editor-field" }, [el("span", { text: text }), input]);
  }

  function slotSelect(slot, mode, assets) {
    var images = (ui.changes.settings.images = ui.changes.settings.images || {});
    var select = el("select", { "data-capy-logo": slot.name + ":" + mode, "aria-label": slot.label + " (" + mode + ")" });
    select.appendChild(el("option", { value: "", text: mode === "dark" ? "Same as light" : slot.fallback }));
    assets.forEach(function (asset) {
      if (asset.slot !== slot.name) return;
      var name = asset.url.split("/").pop();
      select.appendChild(el("option", { value: String(asset.id), text: name + " (" + asset.width + " × " + asset.height + ")" }));
    });
    select.value = String((images[slot.name] || {})[mode] || "");
    select.addEventListener("change", function () {
      var chosen = (images[slot.name] = images[slot.name] || {});
      if (select.value === "") delete chosen[mode];
      else chosen[mode] = Number(select.value);
      ui.update();
    });
    return field(slot.label + (mode === "dark" ? " (dark)" : ""), select);
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

  function iconInput(item) {
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
    });
    return field(item.label, input);
  }

  ui.imageChoices = function (assets) {
    var box = el("div", { class: "capy-editor-logos" }, [el("h4", { text: "Where images are used" })]);
    ui.spec.logo_slots.forEach(function (slot) {
      slot.modes.forEach(function (mode) {
        box.appendChild(slotSelect(slot, mode, assets));
      });
    });
    ui.spec.logo_heights.forEach(function (item) {
      box.appendChild(heightInput(item));
    });
    ui.spec.icon_settings.forEach(function (item) {
      box.appendChild(iconInput(item));
    });
    box.appendChild(el("p", { class: "capy-editor-note", text: "Logos and icons show on the page after you publish (icons are made then); backgrounds and the header height preview straight away." }));
    return box;
  };
})();
