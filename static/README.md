Place `landing.png` (your overlay image) in this folder so it can be served at `/static/landing.png`.

Tips:
- Prefer a wide image (1920px+) with transparent or dark background for the best overlay effect.
- If you want the overlay above all page layers (including the noise texture), change the image CSS z-index in `templates/landing-gemini.html` to something larger than 50 (e.g., `z-index: 60`) and adjust content z-index accordingly.