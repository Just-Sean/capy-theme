// One image slot and mode in the editor (#271): what it's for, the current image,
// a choice of this slot's earlier uploads, a new upload and the alt text. An
// upload is checked and stored on the server straight away and chosen in the
// unsaved changes; Save draft keeps the choice, Revert drops it (the image stays
// in the theme's list). Used by image-sections.js. Loaded after core.js.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;
  var counter = 0;

  function chosen(slot, mode) {
    return ((ui.changes.settings.images || {})[slot] || {})[mode];
  }

  function choose(slot, mode, id) {
    var images = (ui.changes.settings.images = ui.changes.settings.images || {});
    var modes = (images[slot] = images[slot] || {});
    if (id) modes[mode] = id;
    else delete modes[mode];
    ui.update();
  }

  function asset(id) {
    return ui.assets.find(function (a) { return a.id === id; });
  }

  // Remember a new upload, also in the saved state, so Revert keeps it in the lists.
  function remember(assets) {
    ui.assets = assets;
    if (ui.saved) ui.saved.assets = assets;
  }

  function send(url, slot, mode, file, alt) {
    var data = new FormData();
    data.append("slot", slot);
    data.append("mode", mode);
    data.append("alt_text", alt);
    data.append("file", file);
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-CSRFToken": editor.mount.getAttribute("data-csrf-token") },
      body: data,
    }).then(function (response) {
      return response.json().then(function (body) {
        if (!response.ok) throw new Error((body.errors || [body.error || "The upload failed."]).join(" "));
        return body;
      });
    });
  }

  // The control for one slot and mode; it redraws itself when its image changes.
  ui.slotControl = function (spec, mode) {
    var box = el("div", { class: "capy-editor-slot", "data-capy-slot": spec.name + ":" + mode });
    function draw() {
      box.textContent = "";
      var id = "capy-slot-" + (counter += 1);
      var label = spec.label + (spec.modes.length > 1 ? " (" + mode + ")" : "");
      var current = asset(chosen(spec.name, mode));
      box.appendChild(el("h4", { class: "capy-editor-slot-title", text: label }));
      box.appendChild(el("p", { class: "capy-editor-note", id: id + "-help", text: spec.help[mode] }));
      box.appendChild(
        current
          ? el("img", { class: "capy-editor-slot-preview", src: current.url, alt: current.alt_text || "", width: String(current.width), height: String(current.height) })
          : el("p", { class: "capy-editor-slot-empty", text: spec.empty[mode] })
      );

      var select = el("select", { id: id + "-choice", "aria-describedby": id + "-help" });
      select.appendChild(el("option", { value: "", text: mode === "dark" ? "Same as light" : "None" }));
      ui.assets.forEach(function (a) {
        if (a.slot !== spec.name) return;
        select.appendChild(el("option", { value: String(a.id), text: a.name + " (" + a.width + " × " + a.height + (a.mode === "dark" ? ", dark" : "") + ")" }));
      });
      select.value = current ? String(current.id) : "";
      select.addEventListener("change", function () {
        choose(spec.name, mode, select.value ? Number(select.value) : null);
        draw();
        box.querySelector("select").focus();
      });
      box.appendChild(el("label", { class: "capy-editor-stack", for: id + "-choice" }, [el("span", { text: "Current image" }), select]));

      if (current) {
        var altInput = el("input", { type: "text", id: id + "-alt", maxlength: "200" });
        var alts = (ui.changes.alts = ui.changes.alts || {});
        altInput.value = current.id in alts ? alts[current.id] : current.alt_text;
        altInput.addEventListener("input", function () {
          if (altInput.value.trim() === current.alt_text) delete alts[current.id];
          else alts[current.id] = altInput.value;
          ui.update();
        });
        box.appendChild(el("label", { class: "capy-editor-stack", for: id + "-alt" }, [el("span", { text: "Alt text (describes the image for screen readers)" }), altInput]));
      }

      var file = el("input", { type: "file", id: id + "-file", accept: spec.svg ? "image/png,image/jpeg,image/webp,image/gif,image/svg+xml" : "image/png,image/jpeg,image/webp,image/gif" });
      var newAlt = el("input", { type: "text", id: id + "-new-alt", maxlength: "200" });
      var button = el("button", { type: "button", text: "Upload and use" });
      button.addEventListener("click", function () {
        if (button.disabled) return;
        if (!file.files.length) {
          editor.status("Choose an image to upload for the " + label.toLowerCase() + ".", true);
          return;
        }
        button.disabled = true; // one upload at a time (#222)
        button.setAttribute("aria-busy", "true");
        button.textContent = "Uploading…";
        editor.status("Uploading…");
        send(ui.saved.urls.upload, spec.name, mode, file.files[0], newAlt.value)
          .then(function (body) {
            remember(body.assets);
            choose(spec.name, mode, body.uploaded.id);
            draw();
            editor.status("Uploaded and chosen for the " + label.toLowerCase() + ". Save draft to keep it. Location and camera details were removed.");
            box.querySelector("select").focus();
          })
          .catch(function (error) {
            button.disabled = false;
            button.removeAttribute("aria-busy");
            button.textContent = "Upload and use";
            editor.status(error.message, true);
          });
      });
      box.appendChild(
        el("details", { class: "capy-editor-upload", "data-capy-fold": "Upload: " + spec.name + ":" + mode }, [
          el("summary", { text: "Upload a new image" }),
          el("label", { class: "capy-editor-stack", for: id + "-file" }, [el("span", { text: "Image file" }), file]),
          el("label", { class: "capy-editor-stack", for: id + "-new-alt" }, [el("span", { text: "Alt text (describes the image for screen readers)" }), newAlt]),
          button,
        ])
      );
    }
    draw();
    return box;
  };
})();
