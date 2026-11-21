// Editor section: the base theme (a theme is a single scheme — light or dark —
// which comes from its base).
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

  function baseSelect() {
    var select = el("select", { "data-capy-base": "base", "aria-label": "base theme" });
    ui.spec.bases.forEach(function (base) {
      var option = el("option", { value: base.name, text: base.name + " (" + base.scheme + ")" });
      if (base.name === ui.changes.base) option.selected = true;
      select.appendChild(option);
    });
    select.addEventListener("change", function () {
      ui.changes.base = select.value;
      ui.update();
    });
    return el("label", { class: "capy-editor-field" }, [
      el("span", { text: "Base theme" }),
      select,
    ]);
  }

  ui.sections.push({
    order: 10,
    build: function () {
      return ui.section("Base", [baseSelect()]);
    },
  });
})();
