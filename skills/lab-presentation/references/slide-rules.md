# Slide rules

Every slide of every deck keeps these rules. Read the audience brief first: rules 1, 4 and 8
depend on it. [practice.md](practice.md) gives the evidence behind them.

Rule numbers are stable ids that the skill, the deck lint and other pages cite. A removed rule
leaves a gap.

<!-- The list numbers are the rule ids: they run on across the headings. -->
<!-- markdownlint-disable MD029 -->

## Content

1. **Phrases and key terms in the body.** No full sentence below the title. Keep the key terms
   on the slide, and leave the sentence to the speaker. "We found that trimming the reads
   improved the alignment rate" becomes "Trimmed reads: higher alignment rate". A quote may
   stay a sentence. A deck the brief marks as read alone may carry its own sentences.
2. **The title states the conclusion.** One short sentence, two lines at most. It is the only
   sentence the slide needs. "Alignment rate by sample" becomes "Trimming raises the alignment
   rate in every sample".
3. **One idea per slide, and the idea is on it.** A point that matters appears on the slide in
   short form, because the audience misses what is only said. Cut what the talk will not
   discuss, however interesting.
4. **Jargon is judged against the brief.** Spell out a term or an abbreviation at first use,
   unless the brief lists it under known terms. Say what a named tool does in one plain line.
   The agent's own sense of what is common knowledge decides nothing.
5. **The field's own wording.** Take each term of art from the field's papers. A paraphrase
   sounds wrong to the experts in the room.
6. **A real figure, simplified.** Where a figure panel exists, use it. Never redraw a result
   by hand. Simplify it for the slide: one panel, less detail, thicker lines, larger labels,
   and labels on the data in place of a legend.
7. **Round numbers and short citations.** "About 80%", not "79.6%", unless the digits are the
   point. Cite as author, journal, year.

## Size

8. **Size by the room.** The floor holds for everything the audience must read, figure labels
   included, and for Chinese text as for Latin. Fix an overflow by cutting words, never by
   shrinking under the floor.

   | Room in the brief | Default body | Floor | Citation line |
   | --- | --- | --- | --- |
   | Meeting room, or no room given | 24 pt | 20 pt | 12 pt, one line |
   | Hall | 28 pt | 24 pt | 12 pt, one line |

## Look

9. **Colour only with meaning.** Text is black. One accent colour marks the element the slide
   is about, and nothing else. A colour with no reason becomes black.
10. **Colours a colour-blind viewer can tell apart.** Take category colours from this palette,
    as red, green, blue: black 0,0,0; orange 230,159,0; sky blue 86,180,233; bluish green
    0,158,115; yellow 240,228,66; blue 0,114,178; vermillion 213,94,0; reddish purple
    204,121,167. Never mark a difference by colour alone: add shape, line style or position.
    No red beside green.
11. **White background, no decoration.** A white 16:9 slide in one plain font. No texture,
    shadow, gradient, frame, clip art or logo strip. A deck's theme file may change the font
    and the accent colour, and nothing else. Do not add decoration because a slide looks
    empty.

## Animation

12. **Reveal by section.** A click shows or hides a whole section, never one line of a list.
    Use a few clicks per slide at most.
13. **Appear and Disappear only.** No other entrance, exit, motion path, looping movie or
    slide transition. Movement suggests an emphasis nobody intended.

## Editing

14. **State the slide and the change before editing.** One line: the page number, the slide,
    and the exact change. "Slide 7: shorten the title to one line." When the target is
    unclear, ask which slide.
15. **Change only what was named.** Add, cut, move and restyle nothing else, on that slide or
    any other. List every change in the reply. An improvement you noticed is a proposal, not
    an edit.
