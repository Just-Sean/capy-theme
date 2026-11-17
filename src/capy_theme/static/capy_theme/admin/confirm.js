// Asks before a button that changes what visitors see (publish, activate) does it
// (#273): buttons with data-capy-confirm show it as a question; Cancel stops them.
// Without JavaScript the buttons just work, without the question. No inline script.
(function () {
  "use strict";

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-capy-confirm]");
    if (button && !window.confirm(button.getAttribute("data-capy-confirm"))) {
      event.preventDefault();
    }
  });
})();
