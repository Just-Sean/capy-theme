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
    // tabindex="-1" so opening the editor can move focus to the panel itself.
    var panel = el("aside", { class: "capy-editor", role: "dialog", "aria-label": "Theme editor", tabindex: "-1" });
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

  // Keyboard focus (#245). Below this width the panel covers the whole page
  // (editor.css), so the page behind it is made inert: Tab can't reach it.
  var covered = window.matchMedia("(max-width: 47.99rem)");

  function isEditorUi(node) {
    return /(^|\s)capy-editor/.test(node.className || "");
  }

  function coverPage() {
    var open = editor.panel && !editor.panel.hidden;
    Array.prototype.forEach.call(document.body.children, function (node) {
      if (isEditorUi(node)) return;
      if (open && covered.matches) {
        if (node.hasAttribute("inert")) return; // the page's own; left alone
        node.setAttribute("inert", "");
        node.setAttribute("data-capy-editor-inert", "");
      } else if (node.hasAttribute("data-capy-editor-inert")) {
        node.removeAttribute("inert");
        node.removeAttribute("data-capy-editor-inert");
      }
    });
  }
  covered.addEventListener("change", coverPage);

  // Back to whatever opened the editor (the Edit theme button or a link), if it's still there.
  function returnFocus() {
    var opener = editor.opener;
    editor.opener = null;
    if (opener && opener.isConnected && !opener.hidden) opener.focus();
    else if (editor.launch && !editor.launch.hidden) editor.launch.focus();
  }

  editor.open = function () {
    var wasOpen = editor.panel && !editor.panel.hidden;
    var active = document.activeElement;
    if (!wasOpen) editor.opener = active && active !== document.body ? active : null;
    if (!editor.panel) editor.panel = buildPanel();
    if (!editor.banner) editor.banner = buildBanner();
    editor.panel.hidden = false;
    editor.banner.hidden = false;
    if (editor.launch) editor.launch.hidden = true;
    document.documentElement.classList.add("capy-editor-open"); // the page makes room (editor.css)
    coverPage();
    if (!wasOpen) editor.panel.focus();
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
    editor.cancelPreview(); // a preview still on its way mustn't bring the draft back
    removeCss();
    if (editor.panel) editor.panel.hidden = true;
    if (editor.banner) editor.banner.hidden = true;
    if (editor.launch) editor.launch.hidden = false;
    document.documentElement.classList.remove("capy-editor-open");
    document.dispatchEvent(new CustomEvent("capy-editor:closed")); // e.g. page-images.js
    coverPage();
    returnFocus();
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

  // The live edit page's Switch theme menu (#269): with unsaved changes, ask first,
  // naming the theme, instead of the browser's generic "leave site?" warning.
  var switching = false;
  document.addEventListener("click", function (event) {
    var link = event.target.closest && event.target.closest("[data-capy-edit-switch]");
    // A new tab or window (Ctrl, Cmd, Shift, middle click) or a download (Alt) loses
    // nothing here. The theme already being edited is a reload: the browser's own
    // warning covers it.
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (!link || link.getAttribute("aria-current") === "page") return;
    if (!editor.panel || editor.panel.hidden || !editor.isDirty()) return;
    var name = link.getAttribute("data-capy-edit-switch");
    if (window.confirm("You have unsaved changes. Switch to " + name + " and lose them? Choose Cancel, then Save draft, to keep them.")) {
      switching = true;
    } else {
      event.preventDefault();
    }
  });

  window.addEventListener("beforeunload", function (event) {
    if (switching) {
      switching = false; // skips this one warning only: if the switch stops, it's back
      return;
    }
    if (editor.panel && !editor.panel.hidden && editor.isDirty()) {
      event.preventDefault();
      event.returnValue = "";
    }
  });

  editor.applyCss = applyCss;

  // Ask the server for the CSS, values and contrast of unsaved values, and show
  // them on the page. `changes` is {light_base?, dark_base?, settings?: {colors?, shape?}}.
  // Nothing is saved.
  // Bumped by cancelPreview(), so a preview still on its way when the changes are
  // reverted can't put them back on the page (#261).
  var previewRound = 0;

  editor.preview = function (changes) {
    var round = previewRound;
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
        if (round !== previewRound) return result; // reverted meanwhile: ignore it
        linkStylesheets(result.stylesheets);
        applyCss(result.css);
        if (editor.panel) status("Previewing unsaved changes. Nothing is saved yet.");
        document.dispatchEvent(new CustomEvent("capy-editor:preview", { detail: result }));
        return result;
      })
      .catch(function (error) {
        if (editor.panel && round === previewRound) status(error.message, true);
        throw error;
      });
  };

  // The same, but waits until changes stop for a moment (e.g. while dragging a
  // color picker), so the server gets one request instead of dozens.
  var pending = null;
  editor.schedulePreview = function (changes) {
    clearTimeout(pending);
    pending = setTimeout(function () {
      editor.preview(changes).catch(function () {});
    }, 150);
  };

  // Drop a scheduled preview and ignore any still on its way (Revert uses this).
  editor.cancelPreview = function () {
    clearTimeout(pending);
    previewRound += 1;
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

  // Escape closes the editor while focus is in its panel or banner. While the
  // Components view is open, Escape closes only that view (controls/components.js) (#251).
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape" || event.defaultPrevented) return;
    if (!editor.panel || editor.panel.hidden) return;
    var inEditor = event.target.closest && event.target.closest(".capy-editor, .capy-editor-banner");
    if (!inEditor) return;
    if (document.querySelector(".capy-editor-components:not([hidden])")) return; // that closes first
    event.preventDefault();
    editor.close();
  });

  editor.launch = floatingButton();

  // Open straight away when the page is loaded with ?edit=… (e.g. from the admin).
  if (new URLSearchParams(window.location.search).has("edit")) editor.open();
})();
