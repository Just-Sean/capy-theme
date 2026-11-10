// Editor section: the light and dark base themes.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

  function baseSelect(mode) {
    var select = el("select", { "data-capy-base": mode, "aria-label": mode + " base theme" });
    ui.spec.bases[mode].forEach(function (name) {
      var option = el("option", { value: name, text: name });
      if (name === ui.changes[mode + "_base"]) option.selected = true;
      select.appendChild(option);
    });
    select.addEventListener("change", function () {
      ui.changes[mode + "_base"] = select.value;
      ui.update();
    });
    return el("label", { class: "capy-editor-field" }, [
      el("span", { text: mode === "light" ? "Light base" : "Dark base" }),
      select,
    ]);
  }

  ui.sections.push({
    order: 10,
    build: function () {
      return el("section", { class: "capy-editor-section" }, [
        el("h3", { text: "Base themes" }),
        baseSelect("light"),
        baseSelect("dark"),
      ]);
    },
  });
})();
