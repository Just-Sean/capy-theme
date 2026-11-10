// Links each colour text box with the browser's colour picker beside it
// (capy_theme.forms.ColorWidget). Picking writes the hex value into the box;
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
