// Links each color text box with the browser's color picker beside it
// (capy_theme.colors.fields.ColorWidget). Picking writes the hex value into the box;
// typing a hex value moves the picker. Other formats are converted on save.
document.addEventListener("input", function (event) {
  var target = event.target;
  if (target.matches("input[type=color][data-capy-color-for]")) {
    var box = document.getElementById(target.getAttribute("data-capy-color-for"));
    if (box) box.value = target.value;
  } else if (target.id) {
    var picker = document.querySelector('input[data-capy-color-for="' + target.id + '"]');
    if (picker && /^#[0-9a-f]{6}$/i.test(target.value.trim())) picker.value = target.value.trim();
  }
});

// Sizes each picker to sit beside its text box. Set here rather than in a style
// attribute, which a strict Content Security Policy would block (#244).
var CAPY_PICKER_STYLE = {
  "vertical-align": "middle", width: "2.5em", height: "2em",
  padding: "0", border: "none", background: "none",
};
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("input[type=color][data-capy-color-for]").forEach(function (picker) {
    Object.keys(CAPY_PICKER_STYLE).forEach(function (name) {
      picker.style.setProperty(name, CAPY_PICKER_STYLE[name]);
    });
  });
});
