// The live theme editor: a panel on top of the page that previews a theme's
// draft in this browser only. Data comes from the JSON views in editor/views.py, which
// use the same code as publishing. Loaded by templates/capy_theme/editor/mount.html,
// which {% theme_head %} outputs for staff who can edit, so it works on any page.
(function () {
  "use strict";

  var mount = document.getElementById("capy-editor");
  if (!mount) return;

  var editor = {
    mount: mount,
    state: null,
    panel: null,
    sheet: null,
  };
  window.capyEditor = editor;

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      node.setAttribute(key, attrs[key]);
    });
    if (text) node.textContent = text;
    return node;
  }

  // The draft's CSS goes in a constructed stylesheet added after the page's own,
  // so it wins over the published theme. Constructed stylesheets aren't blocked
  // by a Content Security Policy the way <style> elements are.
  function applyCss(css) {
    if (!editor.sheet) {
      editor.sheet = new CSSStyleSheet();
      document.adoptedStyleSheets = document.adoptedStyleSheets.concat([editor.sheet]);
    }
    editor.sheet.replaceSync(css);
  }

  // External font stylesheets (e.g. Adobe Fonts) can't go in a constructed
  // stylesheet, so they're added as <link> elements, once each.
  function linkStylesheets(urls) {
    (urls || []).forEach(function (url) {
      var already = Array.prototype.some.call(document.querySelectorAll('link[rel="stylesheet"]'), function (link) {
        return link.href === url;
      });
      if (!already) {
        var link = el("link", { rel: "stylesheet", href: url, "data-capy-editor-font": "" });
        document.head.appendChild(link);
      }
    });
  }

  function removeCss() {
    if (!editor.sheet) return;
    var sheet = editor.sheet;
    document.adoptedStyleSheets = document.adoptedStyleSheets.filter(function (s) {
      return s !== sheet;
    });
    editor.sheet = null;
  }

  // A small "Edit theme" button in the corner of every page (unless the project
  // turns it off with CAPY_THEME_EDITOR_BUTTON = False).
  function floatingButton() {
    if (mount.getAttribute("data-floating-button") !== "true") return null;
    var button = el("button", { type: "button", class: "capy-editor-launch", "data-capy-editor-open": "" }, "Edit theme");
    document.body.appendChild(button);
    return button;
  }

  // While the editor is open, a banner says that only this user sees the draft.
  function buildBanner() {
    var banner = el("div", { class: "capy-editor-banner", role: "status" });
    banner.appendChild(
      el("span", {}, "Previewing the draft of " + mount.getAttribute("data-theme-name") + ". Only you see it.")
    );
    banner.appendChild(el("button", { type: "button", "data-capy-editor-close": "" }, "Exit"));
    document.body.appendChild(banner);
    return banner;
  }

  function buildPanel() {
    var panel = el("aside", { class: "capy-editor", role: "dialog", "aria-label": "Theme editor" });
    var header = el("div", { class: "capy-editor-header" });
    header.appendChild(el("h2", {}, "Editing " + mount.getAttribute("data-theme-name")));
    var close = el("button", { type: "button", "data-capy-editor-close": "" }, "Close");
    header.appendChild(close);
    panel.appendChild(header);
    panel.appendChild(
      el("p", { class: "capy-editor-note" },
        "You're seeing this theme's draft. Only you see it; visitors keep seeing the published theme.")
    );
    panel.appendChild(el("p", { class: "capy-editor-status", "aria-live": "polite" }));
    panel.appendChild(el("div", { class: "capy-editor-controls" }));
    document.body.appendChild(panel);
    return panel;
  }

  function status(text, isError) {
    var node = editor.panel.querySelector(".capy-editor-status");
    node.textContent = text;
    node.className = "capy-editor-status" + (isError ? " capy-editor-error" : "");
  }

  editor.open = function () {
    if (!editor.panel) editor.panel = buildPanel();
    if (!editor.banner) editor.banner = buildBanner();
    editor.panel.hidden = false;
    editor.banner.hidden = false;
    if (editor.launch) editor.launch.hidden = true;
    document.documentElement.classList.add("capy-editor-open"); // the page makes room (editor.css)
    status("Loading the draft…");
    return fetch(mount.getAttribute("data-state-url"), {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        if (!response.ok) throw new Error("The draft couldn't be loaded (" + response.status + ").");
        return response.json();
      })
      .then(function (state) {
        editor.state = state;
        linkStylesheets(state.stylesheets);
        applyCss(state.css);
        var live = state.live_revision ? "Live: revision " + state.live_revision + "." : "Not published yet.";
        status(live + (state.has_unpublished_changes ? " The draft has unpublished changes." : ""));
        document.dispatchEvent(new CustomEvent("capy-editor:loaded", { detail: state }));
      })
      .catch(function (error) {
        status(error.message, true);
      });
  };

  // Set by the controls: true while there are changes that aren't saved yet.
  editor.isDirty = function () {
    return false;
  };

  editor.close = function () {
    if (editor.isDirty() && !window.confirm("Discard your unsaved changes?")) return;
    removeCss();
    if (editor.panel) editor.panel.hidden = true;
    if (editor.banner) editor.banner.hidden = true;
    if (editor.launch) editor.launch.hidden = false;
    document.documentElement.classList.remove("capy-editor-open");
  };

  // POST JSON to one of the editor's URLs; resolves with the reply, or rejects
  // with the server's error messages.
  editor.post = function (url, data) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": mount.getAttribute("data-csrf-token"),
      },
      body: JSON.stringify(data || {}),
    }).then(function (response) {
      return response.json().then(function (body) {
        if (!response.ok) throw new Error((body.errors || [body.error || "Something went wrong."]).join(" "));
        return body;
      });
    });
  };

  editor.status = function (text, isError) {
    if (editor.panel) status(text, isError);
  };

  window.addEventListener("beforeunload", function (event) {
    if (editor.panel && !editor.panel.hidden && editor.isDirty()) {
      event.preventDefault();
      event.returnValue = "";
    }
  });

  editor.applyCss = applyCss;

  // Ask the server for the CSS, values and contrast of unsaved values, and show
  // them on the page. `changes` is {light_base?, dark_base?, settings?: {colors?, shape?}}.
  // Nothing is saved.
  editor.preview = function (changes) {
    return fetch(mount.getAttribute("data-preview-url"), {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": mount.getAttribute("data-csrf-token"),
      },
      body: JSON.stringify(changes),
    })
      .then(function (response) {
        return response.json().then(function (body) {
          if (!response.ok) {
            throw new Error((body.errors || [body.error || "Preview failed."]).join(" "));
          }
          return body;
        });
      })
      .then(function (result) {
        linkStylesheets(result.stylesheets);
        // While "See it as a visitor" is on, the page keeps the visitors' theme.
        if (!editor.viewCss) applyCss(result.css);
        if (editor.panel) status("Previewing unsaved changes. Nothing is saved yet.");
        document.dispatchEvent(new CustomEvent("capy-editor:preview", { detail: result }));
        return result;
      })
      .catch(function (error) {
        if (editor.panel) status(error.message, true);
        throw error;
      });
  };

  // The same, but waits until changes stop for a moment (e.g. while dragging a
  // colour picker), so the server gets one request instead of dozens.
  var pending = null;
  editor.schedulePreview = function (changes) {
    clearTimeout(pending);
    pending = setTimeout(function () {
      editor.preview(changes).catch(function () {});
    }, 150);
  };

  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-capy-editor-open]")) {
      event.preventDefault();
      editor.open();
    } else if (event.target.closest("[data-capy-editor-close]")) {
      event.preventDefault();
      editor.close();
    }
  });

  editor.launch = floatingButton();

  // Open straight away when the page is loaded with ?edit=… (e.g. from the admin).
  if (new URLSearchParams(window.location.search).has("edit")) editor.open();
})();
