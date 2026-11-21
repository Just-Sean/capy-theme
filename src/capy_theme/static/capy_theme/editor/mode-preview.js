// The live editor's own light / dark / auto PREVIEW toggle. capy-theme's editor is
// its own tool previewing on its own page, so this switches only this page's preview
// (it forces data-theme on <html>, or removes it for "auto" so the device decides).
// It applies nothing to any consumer and stores nothing. No inline script, so a strict
// Content Security Policy never blocks it.
(function () {
  var root = document.documentElement;
  var buttons = document.querySelectorAll("[data-capy-preview-mode]");

  function apply(mode) {
    if (mode === "auto") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", "capy-" + mode);
    buttons.forEach(function (button) {
      var on = button.getAttribute("data-capy-preview-mode") === mode;
      button.setAttribute("aria-pressed", on ? "true" : "false");
      button.classList.toggle("btn-active", on);
    });
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      apply(button.getAttribute("data-capy-preview-mode"));
    });
  });

  apply("auto");
})();
