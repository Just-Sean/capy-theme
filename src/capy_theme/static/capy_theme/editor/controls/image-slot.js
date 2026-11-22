// One image slot in the editor (#271): what it's for, the current image, a choice
// of this slot's earlier uploads, a new upload and the alt text. A theme is a
// single scheme, so each slot has one image (no light/dark). An upload is checked
// and stored on the server straight away and chosen in the unsaved changes; Save
// draft keeps the choice, Revert drops it (the image stays in the theme's list).
// Used by image-sections.js. Loaded after core.js.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;
  var counter = 0;

  function chosen(slot) {
    return (ui.changes.settings.images || {})[slot];
  }

  function choose(slot, id) {
    var images = (ui.changes.settings.images = ui.changes.settings.images || {});
    if (id) images[slot] = id;
    else delete images[slot];
    ui.update();
  }

  function asset(id) {
    return ui.assets.find(function (a) { return a.id === id; });
  }

  // Remember a new upload, also in the saved state, so Revert keeps it in the lists,
  // and refresh the box's list for that slot so it's there too. Only the list: a file
  // chosen in another box, not yet uploaded, stays chosen.
  function remember(assets, slot) {
    ui.assets = assets;
    if (ui.saved) ui.saved.assets = assets;
    var panel = editor.panel;
    if (!panel) return;
    panel.querySelectorAll("[data-capy-slot]").forEach(function (box) {
      if (box.getAttribute("data-capy-slot") === slot && box.capyRefreshList) {
        box.capyRefreshList();
      }
    });
  }

  // The list of a slot's images: None and each upload.
  function fillOptions(select, slot, value) {
    select.textContent = "";
    select.appendChild(el("option", { value: "", text: "None" }));
    ui.assets.forEach(function (a) {
      if (a.slot !== slot) return;
      select.appendChild(el("option", { value: String(a.id), text: a.name + " (" + a.width + " × " + a.height + ")" }));
    });
    select.value = value;
  }

  function send(url, slot, file, alt) {
    var data = new FormData();
    data.append("slot", slot);
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

  // The control for one slot; it redraws itself when its image changes.
  ui.slotControl = function (spec) {
    var box = el("div", { class: "capy-editor-slot", "data-capy-slot": spec.name });
    var uploading = false; // kept across redraws, so a redraw can't allow a second upload
    function draw() {
      box.textContent = "";
      var id = "capy-slot-" + (counter += 1);
      var label = spec.label;
      var current = asset(chosen(spec.name));
      box.appendChild(el("h4", { class: "capy-editor-slot-title", text: label }));
      box.appendChild(el("p", { class: "capy-editor-note", id: id + "-help", text: spec.help }));
      box.appendChild(
        current
          ? el("img", { class: "capy-editor-slot-preview", src: current.url, alt: current.alt_text || "", width: String(current.width), height: String(current.height) })
          : el("p", { class: "capy-editor-slot-empty", text: spec.empty })
      );

      var select = el("select", { id: id + "-choice", "aria-describedby": id + "-help" });
      fillOptions(select, spec.name, current ? String(current.id) : "");
      select.disabled = uploading;
      box.capyRefreshList = function () {
        fillOptions(select, spec.name, select.value);
      };
      select.addEventListener("change", function () {
        choose(spec.name, select.value ? Number(select.value) : null);
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
        box.appendChild(el("label", { class: "capy-editor-stack", for: id + "-alt" }, [el("span", { text: "Alt text of the current image (describes it for screen readers)" }), altInput]));
      }

      var file = el("input", { type: "file", id: id + "-file", accept: spec.svg ? "image/png,image/jpeg,image/webp,image/gif,image/svg+xml" : "image/png,image/jpeg,image/webp,image/gif" });
      var newAlt = el("input", { type: "text", id: id + "-new-alt", maxlength: "200" });
      var button = el("button", { type: "button", text: uploading ? "Uploading…" : "Upload and use" });
      button.disabled = uploading;
      button.addEventListener("click", function () {
        if (uploading) return;
        if (!file.files.length) {
          editor.status("Choose an image to upload for the " + label.toLowerCase() + ".", true);
          return;
        }
        uploading = true; // one upload at a time (#222)
        select.disabled = true;
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
        button.textContent = "Uploading…";
        editor.status("Uploading…");
        send(ui.saved.urls.upload, spec.name, file.files[0], newAlt.value)
          .then(function (body) {
            uploading = false;
            // Closed, saved or reverted meanwhile: this box is gone. The image is in
            // the slot's lists; it isn't chosen behind the user's back.
            if (!box.isConnected || !editor.panel || editor.panel.hidden) {
              remember(body.assets, spec.name);
              if (editor.panel && !editor.panel.hidden) {
                editor.status("Uploaded. It's in the list for the " + label.toLowerCase() + ", but not chosen.");
              }
              return;
            }
            remember(body.assets, spec.name);
            choose(spec.name, body.uploaded.id);
            draw();
            editor.status("Uploaded and chosen for the " + label.toLowerCase() + ". Save draft to keep it. Location and camera details were removed.");
            box.querySelector("select").focus();
          })
          .catch(function (error) {
            uploading = false;
            // Nothing redrawn, so the chosen file and the open fold stay as they were.
            select.disabled = false;
            button.disabled = false;
            button.removeAttribute("aria-busy");
            button.textContent = "Upload and use";
            editor.status(error.message, true);
          });
      });
      box.appendChild(
        el("details", { class: "capy-editor-upload", "data-capy-fold": "Upload: " + spec.name }, [
          el("summary", { text: "Upload a new image" }),
          el("label", { class: "capy-editor-stack", for: id + "-file" }, [el("span", { text: "Image file" }), file]),
          el("label", { class: "capy-editor-stack", for: id + "-new-alt" }, [el("span", { text: "Alt text for the new image" }), newAlt]),
          button,
        ])
      );
    }
    draw();
    return box;
  };
})();
