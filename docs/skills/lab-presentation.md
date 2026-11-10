# lab-presentation: slides an audience can follow

The skill loads by itself when you ask for slides, a deck, a talk or a PowerPoint file. You
can also call it directly:

```text
/lab-presentation A 15-minute update for group meeting on the new pipeline.
```

## What happens, in order

1. **The audience brief.** The agent needs to know who is listening before it writes a word.
   It asks only for what your request left out.
2. **A text outline.** You agree the content as plain text first. No slide exists yet.
3. **The slides.** The agent builds the deck from the outline.
4. **The check.** The agent looks at a picture of every slide, at every click, before it
   tells you the deck is done.
5. **Speaker notes.** Only when you ask, or for a formal talk. They are written last.

A three-slide update gets steps 1, 2 and 4 and stays quick. If you reject a slide, the agent
shows you 2 to 4 built options to choose from.

## The audience brief

| Line | Example | If you leave it out |
| --- | --- | --- |
| Audience | Our own group | The agent asks |
| What they already know | The old pipeline | The agent asks |
| Length | 15 minutes | The agent asks |
| Language | English | The agent asks |
| Known terms | The short names we use every day | The agent asks |
| Room | Meeting room or hall | Meeting room |
| Use | Presented or read alone | Presented |

The brief decides what counts as jargon. A short name on the known-terms line stays as it
is. Any other is spelled out the first time it appears.

## The slide rules

The rules are numbered, so you can point at one. The main ones:

- The body holds phrases and key terms. The speaker says the sentences.
- The title states the slide's conclusion in one short sentence, two lines at most.
- One idea per slide. A point that matters is on the slide in short form.
- Colour appears only where it means something, from a set of colours that colour-blind
  viewers can tell apart.
- The background is white, with nothing added for looks.
- A click shows a whole section at a time. Nothing flies in.

Text size follows the room:

| Room | Body text | Smallest text you must read | Citation line |
| --- | --- | --- | --- |
| Meeting room | 24 pt | 20 pt | 12 pt, one line |
| Hall | 28 pt | 24 pt | 12 pt, one line |

## When you ask for a change

The agent first repeats the slide and the exact change in one line. Then it changes only
that. It adds nothing you did not name, and it lists what it changed.

## Where the rules come from

A second page behind the skill lists what published work says about talks and slides. Each
item names its source and says how well tested it is. Most of the tests used students and
short recorded lessons, so the rules are sound defaults and not laws.
