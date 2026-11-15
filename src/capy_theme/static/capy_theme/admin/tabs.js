// Turns the theme edit page's sections into tabs (capy_theme.admin.tabs groups them; the
// template wraps each group in a [data-capy-tab] panel). Presentation only: every field
// stays in the form and is submitted as before. Follows the WAI-ARIA tabs pattern.
(function () {
  var panels = Array.prototype.slice.call(document.querySelectorAll("[data-capy-tab]"));
  if (!panels.length) return;

  var STORE_KEY = "capy-theme-admin-tab:" + location.pathname;
  var tabs = [];
  var byId = {};

  panels.forEach(function (panel, n) {
    var id = panel.getAttribute("data-capy-tab");
    if (!byId[id]) {
      byId[id] = {
        id: id,
        label: panel.getAttribute("data-capy-tab-label"),
        order: parseInt(panel.getAttribute("data-capy-tab-order"), 10),
        panels: []
      };
      tabs.push(byId[id]);
    }
    panel.id = id + "-panel-" + n;
    byId[id].panels.push(panel);
  });
  // Inline lists come after all the sections in the page, so put the tabs in their order.
  tabs.sort(function (a, b) { return a.order - b.order; });

  var list = document.createElement("div");
  list.className = "capy-tabs";
  list.setAttribute("role", "tablist");
  list.setAttribute("aria-label", "Theme sections");

  tabs.forEach(function (tab) {
    var button = document.createElement("button");
    button.type = "button";
    button.id = tab.id + "-tab";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", tab.panels.map(function (p) { return p.id; }).join(" "));
    button.textContent = tab.label;
    tab.hasErrors = tab.panels.some(function (p) { return p.querySelector(".errorlist"); });
    if (tab.hasErrors) {
      button.classList.add("capy-tab-has-errors");
      button.insertAdjacentHTML(
        "beforeend",
        '<span class="capy-tab-error" aria-hidden="true"> ⚠</span>' +
          '<span class="capy-visually-hidden"> (has errors)</span>'
      );
    }
    tab.panels.forEach(function (panel) {
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", button.id);
      panel.querySelectorAll("[data-capy-unfold] details").forEach(function (d) { d.open = true; });
    });
    button.addEventListener("click", function () { select(tab, false); });
    tab.button = button;
    list.appendChild(button);
  });
  panels[0].parentNode.insertBefore(list, panels[0]);

  function select(tab, focus) {
    tabs.forEach(function (other) {
      var on = other === tab;
      other.button.setAttribute("aria-selected", on ? "true" : "false");
      other.button.tabIndex = on ? 0 : -1;
      other.panels.forEach(function (p) { p.hidden = !on; });
    });
    if (focus) tab.button.focus();
    try { sessionStorage.setItem(STORE_KEY, tab.id); } catch (e) { /* storage off: fine */ }
  }

  list.addEventListener("keydown", function (event) {
    var i = tabs.findIndex(function (t) { return t.button === document.activeElement; });
    if (i < 0) return;
    var next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    select(tabs[(next + tabs.length) % tabs.length], true);
  });

  var stored = null;
  try { stored = sessionStorage.getItem(STORE_KEY); } catch (e) { /* storage off: fine */ }
  var start = tabs.find(function (t) { return t.hasErrors; }) ||
    (Object.prototype.hasOwnProperty.call(byId, stored) && byId[stored]) || tabs[0];
  select(start, false);

  // Django may already have focused the first field, which can now be in a hidden tab.
  var focused = document.activeElement;
  if (focused && panels.some(function (p) { return p.hidden && p.contains(focused); })) {
    start.button.focus();
  }
})();
