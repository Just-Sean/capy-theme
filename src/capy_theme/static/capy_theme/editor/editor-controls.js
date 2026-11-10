// The editor panel's controls: base themes, colours (light and dark) and shape.
// Every change is previewed straight away through capyEditor.schedulePreview();
// nothing is saved. Loaded after editor.js by templates/capy_theme/editor/mount.html.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor) return;

  // The unsaved values: what the preview endpoint (and later Save) receives.
  var changes = null;
  var baseline = "";
  var spec = null;
  var scheme = "light";
  var latest = null;

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "text") node.textContent = attrs[key];
      else node.setAttribute(key, attrs[key]);
    });
    (children || []).forEach(function (child) {
      if (child) node.appendChild(child);
    });
    return node;
  }

  function colors(mode) {
    changes.settings.colors = changes.settings.colors || {};
    changes.settings.colors[mode] = changes.settings.colors[mode] || {};
    return changes.settings.colors[mode];
  }

  function normalized() {
    var copy = JSON.parse(JSON.stringify(changes));
    var c = copy.settings.colors || {};
    Object.keys(c).forEach(function (mode) {
      if (!Object.keys(c[mode]).length) delete c[mode];
    });
    if (!Object.keys(c).length) copy.settings.colors = {};
    var images = copy.settings.images || {};
    Object.keys(images).forEach(function (slot) {
      if (!Object.keys(images[slot]).length) delete images[slot];
    });
    return copy;
  }

  function update() {
    editor.changes = normalized();
    editor.schedulePreview(editor.changes);
    showDirty();
  }

  editor.isDirty = function () {
    return !!changes && JSON.stringify(normalized()) !== baseline;
  };

  function showDirty() {
    var note = editor.panel && editor.panel.querySelector("[data-capy-dirty]");
    if (note) note.textContent = editor.isDirty() ? "Unsaved changes." : "No unsaved changes.";
  }

  // Save draft and Publish

  function actions(state) {
    var save = el("button", { type: "button", class: "capy-editor-primary", "data-capy-save": "", text: "Save draft" });
    var section = el("section", { class: "capy-editor-section capy-editor-actions" }, [
      el("h3", { text: "Save and publish" }),
      el("p", { class: "capy-editor-note", "data-capy-dirty": "", "aria-live": "polite" }),
      save,
    ]);
    save.addEventListener("click", function () {
      saveDraft().catch(function () {});
    });
    if (state.can_publish) {
      var note = el("input", { type: "text", "data-capy-note": "", placeholder: "Note for the history (optional)", "aria-label": "Publish note" });
      var publish = el("button", { type: "button", "data-capy-publish": "", text: "Publish" });
      publish.addEventListener("click", function () {
        if (!window.confirm("Publish this theme? Visitors will see it.")) return;
        (editor.isDirty() ? saveDraft() : Promise.resolve())
          .then(function () {
            return editor.post(editor.mount.getAttribute("data-publish-url"), { note: note.value });
          })
          .then(function (reply) {
            note.value = "";
            build(reply.state);
            editor.applyCss(reply.state.css);
            editor.status("Published as revision " + reply.published + ". Visitors now see it.");
          })
          .catch(function (error) {
            editor.status(error.message, true);
          });
      });
      section.appendChild(el("div", { class: "capy-editor-publish" }, [note, publish]));
    } else {
      section.appendChild(el("p", { class: "capy-editor-note", text: "Publishing needs the publish permission." }));
    }
    return section;
  }

  function saveDraft() {
    return editor
      .post(editor.mount.getAttribute("data-save-url"), editor.changes)
      .then(function (reply) {
        build(reply.state);
        editor.applyCss(reply.state.css);
        editor.status("Draft saved. Visitors won't see it until it's published.");
        return reply;
      })
      .catch(function (error) {
        editor.status(error.message, true);
        throw error;
      });
  }

  // Base themes

  function baseSelect(mode) {
    var select = el("select", { "data-capy-base": mode, "aria-label": mode + " base theme" });
    spec.bases[mode].forEach(function (name) {
      var option = el("option", { value: name, text: name });
      if (name === changes[mode + "_base"]) option.selected = true;
      select.appendChild(option);
    });
    select.addEventListener("change", function () {
      changes[mode + "_base"] = select.value;
      update();
    });
    return el("label", { class: "capy-editor-field" }, [
      el("span", { text: mode === "light" ? "Light base" : "Dark base" }),
      select,
    ]);
  }

  // Colours

  function colorRow(color) {
    var text = el("input", {
      type: "text",
      "data-capy-color": color.name,
      "aria-label": color.label + " (any colour format)",
      spellcheck: "false",
    });
    var picker = el("input", { type: "color", "data-capy-picker": color.name, "aria-label": "Pick " + color.label });
    var reset = el("button", { type: "button", "data-capy-reset": color.name, title: "Use the base theme's colour", text: "Reset" });
    var badge = el("span", { class: "capy-editor-badge", "data-capy-badge": color.name });

    picker.addEventListener("input", function () {
      text.value = picker.value;
      colors(scheme)[color.name] = picker.value;
      update();
    });
    text.addEventListener("change", function () {
      if (text.value.trim()) colors(scheme)[color.name] = text.value.trim();
      else delete colors(scheme)[color.name];
      update();
    });
    reset.addEventListener("click", function () {
      delete colors(scheme)[color.name];
      text.value = "";
      update();
    });
    return el("div", { class: "capy-editor-color" }, [
      el("span", { class: "capy-editor-color-label", text: color.label }),
      picker,
      text,
      reset,
      badge,
    ]);
  }

  function colorSection() {
    var tabs = el("div", { class: "capy-editor-tabs", role: "tablist" });
    ["light", "dark"].forEach(function (mode) {
      var tab = el("button", {
        type: "button",
        role: "tab",
        "data-capy-scheme": mode,
        "aria-selected": mode === scheme ? "true" : "false",
        text: mode === "light" ? "Light colours" : "Dark colours",
      });
      tab.addEventListener("click", function () {
        scheme = mode;
        tabs.querySelectorAll("[data-capy-scheme]").forEach(function (t) {
          t.setAttribute("aria-selected", t.getAttribute("data-capy-scheme") === mode ? "true" : "false");
        });
        fill();
      });
      tabs.appendChild(tab);
    });
    var groups = spec.color_groups.map(function (group, index) {
      var details = el("details", index === 0 ? { open: "" } : {}, [el("summary", { text: group.name })]);
      group.colors.forEach(function (color) {
        details.appendChild(colorRow(color));
      });
      return details;
    });
    return el("section", { class: "capy-editor-section" }, [el("h3", { text: "Colours" }), tabs, suggestionBox()].concat(groups));
  }

  // Palette suggestions: from the current primary colour and from the logo.
  // Clicking one fills in the colours and previews them; nothing is saved.

  function suggestionBox() {
    var list = el("div", { class: "capy-editor-suggestions", "aria-live": "polite" });
    var button = el("button", { type: "button", "data-capy-suggest": "", text: "Suggest colours" });
    button.addEventListener("click", function () {
      list.textContent = "Finding suggestions…";
      var primary = latest.values[scheme]["--color-primary"];
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
      el("p", { class: "capy-editor-note", text: "Colours that go with your primary colour, or from your logo. Click one to try it on this mode; nothing is saved." }),
      button,
      list,
    ]);
  }

  // Which uploaded image each logo slot uses, in light and dark mode, and the
  // header logo heights. Saved with Save draft like everything else.
  function logoChoices(assets) {
    var box = el("div", { class: "capy-editor-logos" }, [el("h4", { text: "Logos, icon and sharing image" })]);
    var images = (changes.settings.images = changes.settings.images || {});
    spec.logo_slots.forEach(function (slot) {
      slot.modes.forEach(function (mode) {
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
          update();
        });
        box.appendChild(el("label", { class: "capy-editor-field" }, [el("span", { text: slot.label + (mode === "dark" ? " (dark)" : "") }), select]));
      });
    });
    spec.logo_heights.forEach(function (item) {
      var input = el("input", { type: "number", min: "16", max: "200", step: "1", placeholder: String(item.default), "data-capy-logo-height": item.name, "aria-label": item.label });
      input.value = (changes.settings.logo || {})[item.name] || "";
      input.addEventListener("input", function () {
        var logo = (changes.settings.logo = changes.settings.logo || {});
        if (input.value === "") delete logo[item.name];
        else logo[item.name] = Number(input.value);
        update();
      });
      box.appendChild(el("label", { class: "capy-editor-field" }, [el("span", { text: item.label }), input]));
    });
    spec.icon_settings.forEach(function (item) {
      var input = item.name === "padding"
        ? el("input", { type: "number", min: "0", max: "25", step: "1", placeholder: "0" })
        : el("input", { type: "text", maxlength: "7", placeholder: "Transparent, or e.g. #ffffff" });
      input.setAttribute("data-capy-icon", item.name);
      input.setAttribute("aria-label", item.label);
      input.title = item.help;
      input.value = (changes.settings.icon || {})[item.name] === undefined ? "" : changes.settings.icon[item.name];
      input.addEventListener("input", function () {
        var icon = (changes.settings.icon = changes.settings.icon || {});
        if (input.value === "") delete icon[item.name];
        else icon[item.name] = item.name === "padding" ? Number(input.value) : input.value.trim();
        update();
      });
      box.appendChild(el("label", { class: "capy-editor-field" }, [el("span", { text: item.label }), input]));
    });
    box.appendChild(el("p", { class: "capy-editor-note", text: "Logos and icons show on the page after you publish (icons are made then); the header height previews straight away." }));
    return box;
  }

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
      var target = colors(scheme);
      Object.keys(suggestion.colors).forEach(function (name) {
        target[name] = suggestion.colors[name];
      });
      fill();
      update();
    });
    return button;
  }

  // Fonts

  function fontSection() {
    var rows = spec.font_roles.map(function (role) {
      var select = el("select", { "data-capy-font": role.name, "aria-label": role.label + " font" });
      select.appendChild(el("option", { value: "", text: "Default" }));
      spec.fonts.forEach(function (font) {
        select.appendChild(el("option", { value: String(font.id), text: font.family + " (" + font.source + ")" }));
      });
      var sample = el("div", { class: "capy-editor-font-sample", "data-capy-font-sample": role.name, text: "The quick brown fox jumps over the lazy dog" });
      select.addEventListener("change", function () {
        var fonts = (changes.settings.fonts = changes.settings.fonts || {});
        if (select.value === "") delete fonts[role.name];
        else fonts[role.name] = Number(select.value);
        showSample(role.name);
        update();
      });
      return el("div", {}, [el("label", { class: "capy-editor-field" }, [el("span", { text: role.label }), select]), sample]);
    });
    spec.type.forEach(function (item) {
      var input = el("input", {
        type: "number",
        step: String(item.step),
        min: String(item.min),
        max: String(item.max),
        "data-capy-type": item.name,
        "aria-label": item.label,
      });
      input.addEventListener("input", function () {
        var type = (changes.settings.type = changes.settings.type || {});
        if (input.value === "") delete type[item.name];
        else type[item.name] = Number(input.value);
        update();
      });
      rows.push(el("label", { class: "capy-editor-field" }, [el("span", { text: item.label + (item.unit ? " (" + item.unit + ")" : "") }), input]));
    });
    var note = spec.fonts.length
      ? null
      : el("p", { class: "capy-editor-note", text: "The font library is empty. Add fonts in the admin under Capy Theme → Fonts." });
    return el("section", { class: "capy-editor-section" }, [el("h3", { text: "Fonts and type" }), note].concat(rows));
  }

  // A sample line under each font dropdown, in the chosen font (the preview's
  // CSS loads its files). Set through the CSSOM, so a strict CSP allows it.
  function showSample(role) {
    var sample = editor.panel.querySelector('[data-capy-font-sample="' + role + '"]');
    if (!sample) return;
    var id = (changes.settings.fonts || {})[role];
    var font = spec.fonts.find(function (f) { return f.id === id; });
    sample.style.fontFamily = font ? font.stack : "";
    sample.hidden = !font;
  }

  // Images: upload straight away (they're checked and cleaned on the server).
  // An upload is stored as a new image of the theme; it isn't used anywhere
  // until a slot setting (5.3 onwards) points at it, so visitors see nothing new.

  function imageList(assets) {
    var list = el("ul", { class: "capy-editor-images", "data-capy-images": "" });
    if (!assets.length) list.appendChild(el("li", { class: "capy-editor-note", text: "No images yet." }));
    assets.forEach(function (asset) {
      list.appendChild(
        el("li", {}, [
          el("img", { src: asset.url, alt: asset.alt_text, width: "48", height: "48" }),
          el("span", {
            text: asset.slot_label + " (" + asset.mode + "): " + asset.width + " × " + asset.height + ", " + Math.ceil(asset.size / 1024) + " KB",
          }),
        ])
      );
    });
    return list;
  }

  function imageSection(state) {
    var slot = el("select", { "data-capy-image-slot": "", "aria-label": "Where the image goes" });
    spec.image_slots.forEach(function (item) {
      slot.appendChild(el("option", { value: item.name, text: item.label + " (up to " + Math.round(item.max_bytes / 1048576) + " MB" + (item.svg ? "" : ", no SVG") + ")" }));
    });
    var mode = el("select", { "data-capy-image-mode": "", "aria-label": "Light or dark mode" });
    [["light", "Light mode"], ["dark", "Dark mode"]].forEach(function (pair) {
      mode.appendChild(el("option", { value: pair[0], text: pair[1] }));
    });
    var alt = el("input", { type: "text", maxlength: "200", "data-capy-image-alt": "", placeholder: "Describe the image (alt text)" });
    var file = el("input", { type: "file", accept: "image/png,image/jpeg,image/webp,image/gif,image/svg+xml", "data-capy-image-file": "" });
    var button = el("button", { type: "button", text: "Upload" });
    var list = imageList(state.assets || []);
    var logos = logoChoices(state.assets || []);
    button.addEventListener("click", function () {
      if (!file.files.length) {
        editor.status("Choose an image to upload.", true);
        return;
      }
      var data = new FormData();
      data.append("slot", slot.value);
      data.append("mode", mode.value);
      data.append("alt_text", alt.value);
      data.append("file", file.files[0]);
      editor.status("Uploading…");
      fetch(state.urls.upload, {
        method: "POST",
        credentials: "same-origin",
        headers: { Accept: "application/json", "X-CSRFToken": editor.mount.getAttribute("data-csrf-token") },
        body: data,
      })
        .then(function (response) {
          return response.json().then(function (body) {
            if (!response.ok) throw new Error((body.errors || [body.error || "The upload failed."]).join(" "));
            return body;
          });
        })
        .then(function (body) {
          var fresh = imageList(body.assets);
          list.replaceWith(fresh);
          list = fresh;
          var freshLogos = logoChoices(body.assets);
          logos.replaceWith(freshLogos);
          logos = freshLogos;
          file.value = "";
          alt.value = "";
          editor.status("Uploaded. Location and camera details were removed.");
        })
        .catch(function (error) {
          editor.status(error.message, true);
        });
    });
    return el("section", { class: "capy-editor-section" }, [
      el("h3", { text: "Images" }),
      el("label", { class: "capy-editor-field" }, [el("span", { text: "Slot" }), slot]),
      el("label", { class: "capy-editor-field" }, [el("span", { text: "Mode" }), mode]),
      el("label", { class: "capy-editor-field" }, [el("span", { text: "Alt text" }), alt]),
      el("label", { class: "capy-editor-field" }, [el("span", { text: "File" }), file]),
      button,
      list,
      logos,
    ]);
  }

  // Web app: what the web app manifest says (names, start page, display).
  function appSection() {
    var app = (changes.settings.app = changes.settings.app || {});
    var rows = spec.app_settings.map(function (item) {
      var input;
      if (item.choices) {
        input = el("select", {});
        input.appendChild(el("option", { value: "", text: "Default" }));
        item.choices.forEach(function (choice) {
          input.appendChild(el("option", { value: choice.value, text: choice.label }));
        });
      } else {
        input = el("input", { type: "text", maxlength: item.name === "short_name" ? "12" : "300" });
      }
      input.setAttribute("data-capy-app", item.name);
      input.setAttribute("aria-label", item.label);
      input.title = item.help;
      input.value = app[item.name] || "";
      input.addEventListener(item.choices ? "change" : "input", function () {
        var value = input.value.trim();
        if (value === "") delete app[item.name];
        else app[item.name] = value;
        update();
      });
      return el("label", { class: "capy-editor-field" }, [el("span", { text: item.label }), input]);
    });
    var social = (changes.settings.social = changes.settings.social || {});
    spec.social_settings.forEach(function (item) {
      var input = el("textarea", { rows: "2", maxlength: "300", "data-capy-social": item.name, "aria-label": item.label });
      input.title = item.help;
      input.value = social[item.name] || "";
      input.addEventListener("input", function () {
        var value = input.value.trim();
        if (value === "") delete social[item.name];
        else social[item.name] = value;
        update();
      });
      rows.push(el("label", { class: "capy-editor-field" }, [el("span", { text: item.label }), input]));
    });
    return el("section", { class: "capy-editor-section" }, [
      el("details", {}, [el("summary", { text: "Web app and link previews" }),
        el("p", { class: "capy-editor-note", text: "How the site installs as an app, and what shows when a link to it is shared. Used after you publish; the icon and sharing image are chosen under Images." })].concat(rows)),
    ]);
  }

  // Shape

  function shapeSection() {
    var rows = spec.sizes.map(function (size) {
      var input = el("input", {
        type: "number",
        step: "any",
        min: String(size.min),
        max: String(size.max),
        "data-capy-shape": size.name,
        "aria-label": size.label + " (" + size.unit + ")",
      });
      input.addEventListener("input", function () {
        var shape = (changes.settings.shape = changes.settings.shape || {});
        if (input.value === "") delete shape[size.name];
        else shape[size.name] = Number(input.value);
        update();
      });
      return el("label", { class: "capy-editor-field" }, [el("span", { text: size.label + " (" + size.unit + ")" }), input]);
    });
    spec.effects.forEach(function (effect) {
      var select = el("select", { "data-capy-effect": effect.name, "aria-label": effect.label });
      [["", "From the base theme"], ["on", "On"], ["off", "Off"]].forEach(function (pair) {
        select.appendChild(el("option", { value: pair[0], text: pair[1] }));
      });
      select.addEventListener("change", function () {
        var shape = (changes.settings.shape = changes.settings.shape || {});
        if (select.value === "") delete shape[effect.name];
        else shape[effect.name] = select.value === "on";
        update();
      });
      rows.push(el("label", { class: "capy-editor-field" }, [el("span", { text: effect.label }), select]));
    });
    return el("section", { class: "capy-editor-section" }, [
      el("details", {}, [el("summary", { text: "Shape and effects" })].concat(rows)),
    ]);
  }

  // Showing the latest values

  function fill() {
    if (!latest) return;
    var panel = editor.panel;
    var chosen = (changes.settings.colors || {})[scheme] || {};
    var ratings = {};
    (latest.contrast[scheme] || []).forEach(function (entry) {
      ratings[entry.background] = ratings[entry.background] || entry;
      ratings[entry.text] = ratings[entry.text] || entry;
    });
    panel.querySelectorAll("[data-capy-color]").forEach(function (input) {
      var name = input.getAttribute("data-capy-color");
      var value = latest.values[scheme]["--color-" + name];
      if (document.activeElement !== input) input.value = chosen[name] || "";
      input.placeholder = value;
      var picker = panel.querySelector('[data-capy-picker="' + name + '"]');
      if (document.activeElement !== picker) picker.value = latest.hex[scheme][name];
      var row = input.closest(".capy-editor-color");
      row.classList.toggle("capy-editor-overridden", name in chosen);
      var badge = panel.querySelector('[data-capy-badge="' + name + '"]');
      var entry = ratings[name];
      badge.textContent = entry ? (entry.rating === "fail" ? "⚠ " : "") + entry.rating + " " + entry.ratio : "";
      badge.className = "capy-editor-badge" + (entry && entry.rating === "fail" ? " capy-editor-fail" : "");
      badge.title = entry ? "Contrast with its pair (AA needs 4.5:1)" : "";
    });
    var shape = changes.settings.shape || {};
    panel.querySelectorAll("[data-capy-shape]").forEach(function (input) {
      var name = input.getAttribute("data-capy-shape");
      var size = spec.sizes.find(function (s) { return s.name === name; });
      if (document.activeElement !== input) input.value = name in shape ? shape[name] : "";
      input.placeholder = (latest.values.light[size.variable] || "").replace(size.unit, "");
    });
    var typeSettings = changes.settings.type || {};
    panel.querySelectorAll("[data-capy-type]").forEach(function (input) {
      var name = input.getAttribute("data-capy-type");
      if (document.activeElement !== input) input.value = name in typeSettings ? typeSettings[name] : "";
    });
    var fonts = changes.settings.fonts || {};
    panel.querySelectorAll("[data-capy-font]").forEach(function (select) {
      var role = select.getAttribute("data-capy-font");
      select.value = role in fonts ? String(fonts[role]) : "";
      showSample(role);
    });
    panel.querySelectorAll("[data-capy-effect]").forEach(function (select) {
      var name = select.getAttribute("data-capy-effect");
      select.value = name in shape ? (shape[name] ? "on" : "off") : "";
    });
  }

  function build(state) {
    spec = state.controls;
    changes = {
      light_base: state.light_base,
      dark_base: state.dark_base,
      settings: {
        colors: JSON.parse(JSON.stringify(state.settings.colors || {})),
        shape: JSON.parse(JSON.stringify(state.settings.shape || {})),
        fonts: JSON.parse(JSON.stringify(state.settings.fonts || {})),
        type: JSON.parse(JSON.stringify(state.settings.type || {})),
        images: JSON.parse(JSON.stringify(state.settings.images || {})),
        logo: JSON.parse(JSON.stringify(state.settings.logo || {})),
        icon: JSON.parse(JSON.stringify(state.settings.icon || {})),
        app: JSON.parse(JSON.stringify(state.settings.app || {})),
        social: JSON.parse(JSON.stringify(state.settings.social || {})),
      },
    };
    editor.changes = normalized();
    baseline = JSON.stringify(editor.changes);
    latest = state;
    var container = editor.panel.querySelector(".capy-editor-controls");
    container.textContent = "";
    container.appendChild(
      el("section", { class: "capy-editor-section" }, [el("h3", { text: "Base themes" }), baseSelect("light"), baseSelect("dark")])
    );
    container.appendChild(colorSection());
    container.appendChild(fontSection());
    container.appendChild(imageSection(state));
    container.appendChild(appSection());
    container.appendChild(shapeSection());
    container.appendChild(actions(state));
    fill();
    showDirty();
  }

  document.addEventListener("capy-editor:loaded", function (event) {
    build(event.detail);
  });
  document.addEventListener("capy-editor:preview", function (event) {
    latest = event.detail;
    fill();
  });
})();
