// Editor section: uploading images. An upload is checked and cleaned on the
// server and stored straight away as a new image of the theme; it isn't used
// until it's chosen for a slot (image-choices.js) and the theme is published.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var ui = editor.ui;
  var el = ui.el;

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

  function upload(state, fields) {
    var data = new FormData();
    data.append("slot", fields.slot.value);
    data.append("mode", fields.mode.value);
    data.append("alt_text", fields.alt.value);
    data.append("file", fields.file.files[0]);
    return fetch(state.urls.upload, {
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

  function build(state) {
    var fields = {
      slot: el("select", { "data-capy-image-slot": "", "aria-label": "Where the image goes" }),
      mode: el("select", { "data-capy-image-mode": "", "aria-label": "Light or dark mode" }),
      alt: el("input", { type: "text", maxlength: "200", "data-capy-image-alt": "", placeholder: "Describe the image (alt text)" }),
      file: el("input", { type: "file", accept: "image/png,image/jpeg,image/webp,image/gif,image/svg+xml", "data-capy-image-file": "" }),
    };
    ui.spec.image_slots.forEach(function (item) {
      fields.slot.appendChild(el("option", { value: item.name, text: item.label + " (up to " + Math.round(item.max_bytes / 1048576) + " MB" + (item.svg ? "" : ", no SVG") + ")" }));
    });
    [["light", "Light mode"], ["dark", "Dark mode"]].forEach(function (pair) {
      fields.mode.appendChild(el("option", { value: pair[0], text: pair[1] }));
    });
    var button = el("button", { type: "button", text: "Upload" });
    var list = imageList(state.assets || []);
    var choices = ui.imageChoices(state.assets || []);
    button.addEventListener("click", function () {
      if (!fields.file.files.length) {
        editor.status("Choose an image to upload.", true);
        return;
      }
      editor.status("Uploading…");
      upload(state, fields)
        .then(function (body) {
          var fresh = imageList(body.assets);
          list.replaceWith(fresh);
          list = fresh;
          var freshChoices = ui.imageChoices(body.assets);
          choices.replaceWith(freshChoices);
          choices = freshChoices;
          fields.file.value = "";
          fields.alt.value = "";
          editor.status("Uploaded. Location and camera details were removed.");
        })
        .catch(function (error) {
          editor.status(error.message, true);
        });
    });
    return el("section", { class: "capy-editor-section" }, [
      el("h3", { text: "Images" }),
      el("label", { class: "capy-editor-field" }, [el("span", { text: "Slot" }), fields.slot]),
      el("label", { class: "capy-editor-field" }, [el("span", { text: "Mode" }), fields.mode]),
      el("label", { class: "capy-editor-field" }, [el("span", { text: "Alt text" }), fields.alt]),
      el("label", { class: "capy-editor-field" }, [el("span", { text: "File" }), fields.file]),
      button,
      list,
      choices,
    ]);
  }

  ui.sections.push({ order: 40, build: build });
})();
