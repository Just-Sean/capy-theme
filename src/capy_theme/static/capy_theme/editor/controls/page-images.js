// Shows the draft's logos and icon on the page while the editor is open (#271).
// logo_html marks each logo for editors with data-capy-logo-slot (and the
// attributes the template gave it); this swaps them for the draft's logo, and
// points the browser-tab icon at the draft's icon. No reload, nothing saved:
// closing the editor puts the published ones back. Visitors never see it.
(function () {
  "use strict";

  var editor = window.capyEditor;
  if (!editor || !editor.ui) return;
  var HEADER = ["logo_main", "logo_stacked", "logo_mark", "logo_wordmark"];
  // What logo_html writes, and the only attributes copied from its
  // data-capy-logo-attrs onto the draft's logo: class, title and aria-*. Anything
  // else (event handlers, style, src, id, data-*...) is left off the preview: a page
  // could hold a forged marker, e.g. in content its users wrote.
  var MARKED = ["IMG", "PICTURE", "SPAN"];
  var SAFE = /^(class|title|aria-[a-z-]+)$/;
  var spots = null; // [{slot, attrs, nodes, originals}]
  var icons = null; // [{link, href}] and whether we added the link

  function findSpots() {
    var found = [];
    document.querySelectorAll("[data-capy-logo-slot]").forEach(function (node) {
      var slot = node.getAttribute("data-capy-logo-slot");
      if (MARKED.indexOf(node.tagName) === -1 || HEADER.concat(["logo_email", "logo_print"]).indexOf(slot) === -1) return;
      var last = found[found.length - 1];
      if (last && last.slot === slot && last.nodes[last.nodes.length - 1] === node.previousElementSibling) {
        last.nodes.push(node);
        return;
      }
      found.push({ slot: slot, attrs: safeAttrs(node.getAttribute("data-capy-logo-attrs")), nodes: [node] });
    });
    found.forEach(function (spot) {
      spot.originals = spot.nodes.slice();
    });
    return found;
  }

  function safeAttrs(text) {
    var attrs = {};
    var parsed = null;
    try {
      parsed = JSON.parse(text || "{}");
    } catch (error) {
      parsed = null;
    }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return attrs;
    Object.keys(parsed).forEach(function (key) {
      if (SAFE.test(key) && typeof parsed[key] === "string") attrs[key] = parsed[key];
    });
    return attrs;
  }

  function img(spot, image) {
    var node = document.createElement("img");
    Object.keys(spot.attrs).forEach(function (key) {
      if (key !== "class") node.setAttribute(key, spot.attrs[key]);
    });
    var classes = [HEADER.indexOf(spot.slot) !== -1 ? "capy-logo" : "", spot.attrs["class"] || ""].join(" ").trim();
    if (classes) node.className = classes;
    node.src = image.src;
    node.alt = image.alt || "";
    if (image.width && image.height) {
      node.width = image.width;
      node.height = image.height;
    }
    return node;
  }

  function draft(spot, logo, siteName) {
    if (logo) return [img(spot, logo)];
    var span = document.createElement("span");
    Object.keys(spot.attrs).forEach(function (key) {
      span.setAttribute(key, spot.attrs[key]);
    });
    span.textContent = siteName;
    span.hidden = !siteName;
    return [span];
  }

  function put(spot, nodes) {
    var first = spot.nodes[0];
    if (!first.parentNode) return;
    nodes.forEach(function (node) {
      first.parentNode.insertBefore(node, first);
    });
    spot.nodes.forEach(function (node) {
      if (nodes.indexOf(node) === -1 && node.parentNode) node.parentNode.removeChild(node);
    });
    spot.nodes = nodes;
  }

  function showIcon(url) {
    if (!icons) {
      var links = Array.prototype.slice.call(document.querySelectorAll('link[rel~="icon"]'));
      icons = {
        links: links.map(function (link) {
          return { link: link, href: link.href, type: link.getAttribute("type") };
        }),
        added: null,
      };
    }
    if (!url) {
      restoreIcon();
      return;
    }
    if (!icons.links.length && !icons.added) {
      icons.added = document.createElement("link");
      icons.added.rel = "icon";
      document.head.appendChild(icons.added);
    }
    icons.links.forEach(function (item) {
      item.link.removeAttribute("type"); // the draft's icon may be another kind of file
      item.link.href = url;
    });
    if (icons.added) icons.added.href = url;
  }

  function restoreIcon() {
    if (!icons) return;
    icons.links.forEach(function (item) {
      if (item.type) item.link.setAttribute("type", item.type);
      item.link.href = item.href;
    });
    if (icons.added && icons.added.parentNode) icons.added.parentNode.removeChild(icons.added);
    icons.added = null;
  }

  function show(data) {
    // Only while the editor is shown; closing it put the published ones back.
    if (!data || !data.page_images || !editor.panel || editor.panel.hidden) return;
    if (!spots) spots = findSpots();
    var images = data.page_images;
    spots.forEach(function (spot) {
      put(spot, draft(spot, images.logos[spot.slot], images.site_name));
    });
    showIcon(images.icon);
  }

  function restore() {
    (spots || []).forEach(function (spot) {
      put(spot, spot.originals);
    });
    restoreIcon();
  }

  document.addEventListener("capy-editor:loaded", function (event) {
    show(event.detail);
  });
  document.addEventListener("capy-editor:preview", function (event) {
    show(event.detail);
  });
  document.addEventListener("capy-editor:closed", restore);
})();
