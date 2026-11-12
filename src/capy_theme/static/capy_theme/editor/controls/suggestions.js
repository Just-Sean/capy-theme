// Palette suggestions (shown in the colors section): from the current primary
// color and from the logo. Clicking one fills in the colors and previews them;
// nothing is saved.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

  function suggestionButton(suggestion) {
    var swatches = el("span", { class: "capy-editor-swatches" });
    Object.keys(suggestion.colors).forEach(function (name) {
      var swatch = el("span", { class: "capy-editor-swatch", title: name + ": " + suggestion.colors[name] });
      swatch.style.backgroundColor = suggestion.colors[name]; // CSSOM, so a strict CSP allows it
      swatches.appendChild(swatch);
    });
    var button = el("button", { type: "button", class: "capy-editor-suggestion", "data-capy-suggestion": suggestion.name }, [
      el("strong", { text: suggestion.name }),
      swatches,
      el("span", { class: "capy-editor-note", text: suggestion.description }),
    ]);
    button.addEventListener("click", function () {
      var target = ui.colors(ui.scheme);
      Object.keys(suggestion.colors).forEach(function (name) {
        target[name] = suggestion.colors[name];
      });
      ui.fill();
      ui.update();
    });
    return button;
  }

  ui.suggestionBox = function () {
    var list = el("div", { class: "capy-editor-suggestions", "aria-live": "polite" });
    var button = el("button", { type: "button", "data-capy-suggest": "", text: "Suggest colors" });
    button.addEventListener("click", function () {
      list.textContent = "Finding suggestions…";
      var primary = ui.latest.values[ui.scheme]["--color-primary"];
      fetch(editor.mount.getAttribute("data-suggestions-url"), {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-CSRFToken": editor.mount.getAttribute("data-csrf-token"),
        },
        body: JSON.stringify({ primary: primary }),
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Suggestions couldn't be loaded (" + response.status + ").");
          return response.json();
        })
        .then(function (data) {
          list.textContent = "";
          data.suggestions.forEach(function (suggestion) {
            list.appendChild(suggestionButton(suggestion));
          });
        })
        .catch(function (error) {
          list.textContent = error.message;
        });
    });
    return el("details", { class: "capy-editor-suggest" }, [
      el("summary", { text: "Suggestions" }),
      el("p", { class: "capy-editor-note", text: "Colors that go with your primary color, or from your logo. Click one to try it on this mode; nothing is saved." }),
      button,
      list,
    ]);
  };
})();
