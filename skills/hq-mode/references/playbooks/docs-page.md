# Docs page

**You own a page a reader can act on, where every claim matches the repo.**

1. Name the reader, and pick the kind of page with `technical-writing`. Follow the sibling
   pages' structure and register.
2. Read the sources the page describes: the code, the config, the decision records. Trace
   every claim to a file in the repo.
3. Write the prose with `technical-writing`, then `unslop` as the last pass.
4. Diagrams: pick the format by the diagram's job. A small one-direction flow, up to about 8
   nodes, is Mermaid. An overview, a multi-lane flow, an annotated state machine, or any
   diagram where colour or placement carries meaning is hand-drawn SVG, per
   [SVG diagrams](#svg-diagrams). When the session already drew the diagram as an artifact,
   port that SVG and swap its colours for the site's tokens; redraw only when the site needs a
   different shape. Either format changes in the same diff as the prose around it. Draw one
   version and review it on the built page.
5. Check with the repo's strict docs build, then look at every changed page on the built site
   in the light and the dark theme. In a 1280 px wide window, in both themes, each diagram's
   smallest text measures 11 px or more ([measuring](#measuring-text)). A diagram that fails
   changes format or layout and keeps every node and label; it is never cut down to pass.

**Reply:** the pages changed, the build result, the pages looked at in each theme, each
diagram's smallest text in px, and the open choices.

## SVG diagrams

Each diagram is its own file under the docs folder, such as `docs/diagrams/stores.svg`. The
build inlines it into the page, so its classes take the site's colour tokens in both themes.
Wrap it exactly so:

```html
<figure class="diagram">
--8<-- "docs/diagrams/stores.svg"
<figcaption>The figure's one claim, in plain HTML.</figcaption>
</figure>
```

The `<figure>` carries no `markdown` attribute. The snippet path runs from the repo root,
pymdownx's default `base_path`; a repo that sets its own `base_path` writes paths from there.
A bare snippet line, or a `markdown` attribute, lets Markdown split the SVG into paragraphs at
blank lines and turn `*a*` in a label into italics.

Draw to these rules:

- **A `viewBox`, and no `width` or `height`.** The site's stylesheet sets the width, so a
  wider `viewBox` draws its text smaller ([measuring](#measuring-text)).
- **Colour from `currentColor` and the site's tokens only,** through classes such as
  `class="d-store"`. Each token means one thing, such as one domain, on every figure of the
  page. Text and arrowhead markers take `fill="currentColor"`: SVG text is black by default,
  and black text vanishes in the dark theme.
- **Every arrow carries a label** naming what moves along it.
- **One claim per figure,** stated in the caption.
- **Every `id` is unique on the page.** Inline SVGs share the page's ID space, so two
  diagrams with `id="arrow"` take each other's markers. Prefix each `id` with the file's
  name: `stores-arrow`.

### Site setup

A repo's first SVG diagram adds all three in the same pull request:

- `pymdownx.snippets` under `markdown_extensions`, with `check_paths: true`. Without it a
  wrong path builds green under `--strict` and leaves an empty figure.
- A stylesheet listed in `extra_css`, such as `docs/stylesheets/diagrams.css`, with one token
  per meaning, `--d-<meaning>`, for each scheme, and the full-width rule. Without that rule the figure shrinks
  to its caption's width.

  ```css
  [data-md-color-scheme="default"] { --d-store: #0b7285; }
  [data-md-color-scheme="slate"] { --d-store: #66d9e8; }
  .md-typeset figure.diagram,
  .md-typeset figure.diagram svg { width: 100%; }
  .d-store { stroke: var(--d-store); }
  ```

- `figure` and `figcaption` allowed under markdownlint's MD033 (no inline HTML):
  `MD033: {allowed_elements: [figure, figcaption]}` in the repo's markdownlint config.

## Measuring text

A diagram's smallest text is its font size times its on-screen scale. For the SVG figures,
run this in the browser console on the built page; it gives each figure's smallest text in px:

```js
[...document.querySelectorAll('.md-content figure.diagram > svg')].map(s => Math.min(
  ...[...s.querySelectorAll('text, tspan')].map(t => { const m = t.getScreenCTM();
    return parseFloat(getComputedStyle(t).fontSize) * Math.hypot(m.a, m.b) })).toFixed(1))
```

The Material theme draws each Mermaid diagram inside a closed shadow root that a page script
cannot read. Take the same two numbers from the browser's element inspector: the smallest
label's computed font size, and the scale, the `<svg>`'s rendered width over its `viewBox`
width.

Checked on zensical 0.0.57 with the Material theme and pymdown-extensions 11.0, 2026-11-20.
