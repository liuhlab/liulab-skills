# Images

Open this page when a slide needs a picture.

## Reuse first

Before you design a picture, look in the user's earlier decks for a slide that already draws
it: the deck folders beside this one, and any deck the request or the source text names. Reuse
that slide's drawing code or its picture file with its prompt. The audience has seen the
style, and the design work is done. Say in the slide plan's side panel which slide it comes
from.

## A real figure first

Slide rule 6 in [slide-rules.md](slide-rules.md) decides: where a figure panel exists, use
it, simplified as that rule says. Draw a picture only for a schematic or an illustration that
no panel shows. A result is never drawn.

`hq-mode`'s [`figure`](../../hq-mode/references/playbooks/figure.md) playbook owns the steps
around the drawing: the one message, the candidates, the user's choice and the check at final
size. Its working-style page says where Codex runs. This page adds only what a slide needs.

## What goes in the picture

The picture holds the drawing. Every word stays a PowerPoint text box on top of it, so the
user can edit a label, the size floor of rule 8 holds, and the deck lint can read the text.

## The prompt

Write the prompt as a file, `<name>.prompt.md`. Fill in this template and keep every line of
its last three paragraphs:

```markdown
Use your image generation tool to draw <the subject, in one sentence>.

Canvas: <square, or 16:9>, as large as you can make it, at least 1024 px on the short side.
Pure flat white background.

Content and layout:
- <Position>: <one element, with its shape and its colour>.
- <Position>: <the next element>.

Style: <one style, named once, such as "clean textbook illustration">. The same line weight,
lighting and level of detail in every element. Colour only where it tells two things apart;
everything else in one muted colour. No background gradient, no shadow on the background, no
frame and no border.

IMPORTANT: no text anywhere in the image. No labels, letters, numbers, captions or title.
Leave clear empty white space <where each label will go> for labels added later.

Save the final image as a PNG file named <name>.png in the current working directory. Copy
it there if your tool saves it elsewhere. Then reply with only its absolute path.
```

To remake a picture that exists, attach it and open with "Remake the attached illustration.
Keep exactly the same organization and content; change only the art style."

Use one style line for every picture in a deck. Copy it from the deck's first prompt file.

## The command

Run it in a scratch folder, never in the deck folder:

```sh
codex exec --skip-git-repo-check -C <scratch folder> -s workspace-write \
  --enable image_generation - < <name>.prompt.md
```

Add `-i <reference image>` before the `-` to attach a picture to remake. The command was read
from a deck built with `codex-cli` 0.154.0. If a flag fails, read `codex exec --help` and do
not guess.

## Make the background pure white

A generated "white" background is often slightly off-white, and a PNG with no transparency is
opaque. On the white slide of rule 11 the picture then shows as a faint box, and it covers any
text under it. So set every near-white pixel to pure white: a pixel whose red, green and blue
are all 248 or more becomes 255, 255, 255.

```python
from PIL import Image

image = Image.open("<name>.png").convert("RGB")
image.putdata([(255, 255, 255) if min(p) >= 248 else p for p in image.getdata()])
image.save("<name>.png")
```

The snippet needs Pillow, which the plugin does not ship. Any tool that applies the same rule
will do. Even after this step the picture is opaque: keep its box off the slide's text.

## Keep the prompt beside the picture

Copy two files into the deck folder's `pictures/`, and commit them together:

| File | Holds |
| --- | --- |
| `<name>.png` | The picture, after the white step |
| `<name>.prompt.md` | The date, the Codex version, the exact command, the attached image if any, each step done afterwards, and then the prompt word for word |

With both files, anyone can remake the picture. A slide reads the picture as
`deck.picture("<name>.png")`.

Labels sit at positions measured on the picture. After a remake, measure them again, then
look at the slide's rendered pictures as the check step says.
