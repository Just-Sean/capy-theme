// "See it as a visitor": the page (and the Components view) show the published
// theme visitors get instead of the draft, optionally in light or dark, with an
// offered visitor theme, or on a chosen date (to check schedules). Also shows a
// summary of what's set up for visitors. Nothing is saved or changed.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;
  var on = false;
  var originalMode = null;
  var fields = {};

  function field(text, input) {
    return el("label", { class: "capy-editor-field" }, [el("span", { text: text }), input]);
  }

  function dateText(value) {
    return value ? new Date(value).toLocaleString() : "…";
  }

  function summary(info) {
    var items = [
      "Live theme: " + (info.live_theme || "none"),
      "Default mode: " + info.default_mode + ". Visitors " + (info.can_switch ? "can" : "can't") + " switch.",
      "Visitor themes: " + (!info.visitor_themes ? "turned off" : info.offered.length ? info.offered.map(function (t) { return t.name; }).join(", ") : "none offered"),
    ];
    info.schedule.forEach(function (item) {
      items.push("Scheduled: " + item.theme + ", " + dateText(item.starts_at) + " to " + dateText(item.ends_at) + (item.running ? " (running)" : " (upcoming)"));
    });
    if (!info.schedule.length) items.push("Scheduled: none");
    return el("ul", { class: "capy-editor-summary", "data-capy-visitor-summary": "" }, items.map(function (text) {
      return el("li", { text: text });
    }));
  }

  function setMode(mode) {
    var html = document.documentElement;
    if (mode === "light" || mode === "dark") html.setAttribute("data-theme", "capy-" + mode);
    else if (mode === "auto") html.removeAttribute("data-theme");
    else if (originalMode === null) html.removeAttribute("data-theme");
    else html.setAttribute("data-theme", originalMode);
  }

  function load() {
    var query = new URLSearchParams();
    if (fields.theme.value) query.set("theme", fields.theme.value);
    else if (fields.date.value) query.set("date", fields.date.value);
    return fetch(editor.mount.getAttribute("data-visitor-view-url") + "?" + query.toString(), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        return response.json().then(function (body) {
          if (!response.ok) throw new Error((body.errors || [body.error || "That view couldn't be loaded."]).join(" "));
          return body;
        });
      })
      .then(function (body) {
        if (!on) return;
        editor.viewCss = body.css || " ";
        editor.applyCss(editor.viewCss);
        setMode(fields.mode.value);
        document.dispatchEvent(new CustomEvent("capy-editor:view"));
        editor.status(body.theme ? "Showing what visitors see: " + body.theme + " (published)." : "Visitors see no capy-theme theme.");
      })
      .catch(function (error) {
        editor.status(error.message, true);
      });
  }

  function turnOn() {
    on = true;
    originalMode = document.documentElement.getAttribute("data-theme");
    editor.panel.classList.add("capy-editor-visitor-mode");
    fields.box.hidden = false;
    load();
  }

  function turnOff() {
    on = false;
    editor.viewCss = null;
    editor.panel.classList.remove("capy-editor-visitor-mode");
    fields.box.hidden = true;
    fields.mode.value = "";
    setMode("");
    if (ui.latest) editor.applyCss(ui.latest.css);
    document.dispatchEvent(new CustomEvent("capy-editor:view"));
    editor.status("Back to your draft.");
  }

  function build(state) {
    var info = state.visitors;
    var toggle = el("input", { type: "checkbox", "data-capy-visitor": "" });
    toggle.checked = on;
    toggle.addEventListener("change", function () {
      if (toggle.checked) turnOn();
      else turnOff();
    });
    fields.mode = el("select", { "data-capy-visitor-mode": "", "aria-label": "Mode" });
    [["", "As now"], ["light", "Light"], ["dark", "Dark"], ["auto", "Device setting"]].forEach(function (pair) {
      fields.mode.appendChild(el("option", { value: pair[0], text: pair[1] }));
    });
    fields.theme = el("select", { "data-capy-visitor-theme": "", "aria-label": "Visitor's theme choice" });
    fields.theme.appendChild(el("option", { value: "", text: "The site's theme" }));
    if (info.visitor_themes) {
      info.offered.forEach(function (theme) {
        fields.theme.appendChild(el("option", { value: theme.slug, text: theme.name + " (a visitor's choice)" }));
      });
    }
    fields.date = el("input", { type: "date", "data-capy-visitor-date": "", "aria-label": "On date" });
    fields.mode.addEventListener("change", function () { setMode(fields.mode.value); });
    fields.theme.addEventListener("change", function () {
      if (fields.theme.value) fields.date.value = "";
      load();
    });
    fields.date.addEventListener("change", function () {
      if (fields.date.value) fields.theme.value = "";
      load();
    });
    fields.box = el("div", { class: "capy-editor-visitor" }, [
      field("Mode", fields.mode),
      field("Theme", fields.theme),
      field("On date", fields.date),
      el("p", { class: "capy-editor-note", text: "A date shows the site's theme at noon that day, including scheduled themes." }),
      summary(info),
    ]);
    fields.box.hidden = !on;
    return el("section", { class: "capy-editor-section", "data-capy-keep": "" }, [
      el("label", { class: "capy-editor-switch" }, [toggle, el("strong", { text: " See it as a visitor" })]),
      el("p", { class: "capy-editor-note", text: "Shows the published theme visitors get, instead of your draft. Your draft isn't changed." }),
      fields.box,
    ]);
  }

  ui.sections.push({ order: 1, build: build });
})();
