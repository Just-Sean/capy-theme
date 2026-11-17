# src/capy_theme/images/slots.json

**What it is:** data for the image slots: each slot's label, size limit (MB), largest width or height (px), help text and modes.

- **Help:** a detailed explanation of what the slot is for and where it shows, used in the admin and the editor (#271). For the extra logos it names the `{% theme_logo slot="..." %}` to use.
- **Modes:** light and dark for most slots. The email and print logos and the sharing image only have light, since emails, print and link previews have no dark mode.

- **Size limits:** 1 MB for the email logo; 2 MB for the other logos, the icon and the pattern; 5 MB for the print logo, social image and login background.
- **`no_svg`:** the slots that can't take SVG, with the reason:
  - the email logo: email programs don't show SVG
  - the social image: social sites don't accept it
  - the icon: favicons are made from its pixels
