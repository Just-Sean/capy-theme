# src/capy_theme/css/accessibility.py

**What it is:** CSS that respects two visitor device settings, for the whole page.

- **Reduce motion:** animations and transitions finish almost at once, and smooth scrolling is off. It's 0.01 ms rather than 0, so scripts waiting for "animation ended" events still get them.
- **More contrast:** no noise or depth shading, 2 px borders and a 3 px focus outline. The theme's colors are left alone.

daisyUI only partly does the first and doesn't do the second, so the theme stylesheet adds both.
