# Fonts

Place these exact files in this directory (`pdf_generator/static/fonts/`):

- `PlayfairDisplay-Regular.ttf`
- `PlayfairDisplay-Bold.ttf`
- `LibreCaslonText-Regular.ttf`
- `LibreCaslonText-Italic.ttf`
- `LibreCaslonText-Bold.ttf`
- `UnifrakturCook-Bold.ttf`

The stylesheet also declares `local()` sources, so if the fonts are already
installed on the system (e.g. via `fontconfig`) the layout works without these
files. As a final fallback the font stacks end in a generic `serif`.

## Source

Google Fonts:

- Playfair Display — https://fonts.google.com/specimen/Playfair+Display
- Libre Caslon Text — https://fonts.google.com/specimen/Libre+Caslon+Text
- UnifrakturCook — https://fonts.google.com/specimen/UnifrakturCook

Download the TTFs, rename them to the names above, and drop them here.
