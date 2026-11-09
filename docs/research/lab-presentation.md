---
search:
  exclude: true
---

# Research for the `lab-presentation` skill

Gathered on 2026-11-09 for issue 161, by three research agents, one per part. Each claim names
its source and how well established it is. A claim marked *(abstract)* was read from the
abstract only.

## What the orchestrating agent rechecked

These claims were opened again and matched their source:

- Kosslyn 2012: 140 decks; text not "greater than 20 point" in about 65%; bullets not shown one
  at a time in about 95%; "main point was obscured by lots of irrelevant detail" as the most
  common and most annoying fault.
- The display-size standard's open summary: the table of minimum element height by viewing
  ratio, and the factor 200.
- Garner and Alley 2013: 110 students, random assignment, d = 0.81 and d = 0.89.
- Naegle 2021: one slide per minute, about 20 slides for 20 minutes, one panel per slide.
- `pptxgenjs` 4.0.1 on conda-forge.

One correction. Naegle 2021 asks for a heading that states the slide's message, and gives short
declarative examples. It does not require a full sentence. The full-sentence title comes from
Alley and from Doumont.

Nothing else was rechecked. Nothing was run against PowerPoint or LibreOffice.

## What changed in the design

- The text floor rose from 18 pt to 20 pt, and to 24 pt for a hall.
- PptxGenJS became a pixi dependency.
- The slide title became the one place a sentence is wanted.
- Key terms stay on the slide; the notes say the point in other words.
- The audience brief records the room and whether the deck is presented or read alone.

## Talk and slide content: published evidence

Read in full unless marked *(abstract)*. "d" is a standardised group difference: 0.5 medium, 0.8 large. "System-paced": the audience cannot control the pace, as in a live talk.

| Practice | What the source reports | How established | Source |
| --- | --- | --- | --- |
| Open with five items: attention getter, need, task, main message, preview. Order the body as points supporting the message, not as the work's history. End with review, conclusion, close. | The main message is "the one sentence you want your audience to remember, if they remember only one", stated early. Methods: only what helps convince, "usually little". | Expert opinion | Doumont J-L and co-authors, *English Communication for Scientists*, units 4.1 and 4.5. Nature Education. <https://www.nature.com/scitable/ebooks/english-communication-for-scientists-14053993/118520778> and <https://www.nature.com/scitable/ebooks/cntNm-14053993/14240403> |
| Budget about one slide per minute, one idea per slide, three points to keep. | Bourne: more than one visual per minute is too many; a listener should recall three points a week later. Naegle: "around 20 slides" for 20 minutes; one figure panel per slide; cut anything you will not discuss. | Expert opinion, no data | Bourne PE (2007) *PLoS Comput Biol* 3(4):e77. doi:10.1371/journal.pcbi.0030077; Naegle KM (2021) *PLoS Comput Biol* 17(12):e1009554. doi:10.1371/journal.pcbi.1009554 |
| In a 5-minute talk: one story; methods in at most two sentences; start closing at about 80%; repeat the key message once with a different visual. | Timed formats: 20 slides in 5 to 6 minutes. | Expert opinion | Lortie CJ (2017) *PLoS Comput Biol* 13(3):e1005373. doi:10.1371/journal.pcbi.1005373 |
| Write the title as a sentence stating the slide's claim (two lines at most; Doumont: 10 to 15 words); fill the body with visual evidence. | 110 engineering undergraduates, randomised; same recorded 8-minute narration. Assertion-evidence slides (21 words each) against topic title plus bullets (42 words). Essay score d = 0.81; fewer misconceptions; lower rated effort (d = 0.50); surprise test a week later d = 0.89. Fact recall did not differ. | One controlled study, by the method's authors. Title, word count, graphics and builds changed together, so the title's share is unknown. The winning group also rated its prior knowledge higher. | Garner JK, Alley MP (2013) *Int J Eng Educ* 29(6):1564-1579. <https://www.ijee.ie/articles/Vol29-6/23_ijee2791ns.pdf> |
| Put the fact to be remembered in the title, not in a bullet. | Four sections of a geoscience course (136 to 202 students each). On 15 exam questions whose answer had moved into a sentence title: 79% correct against 69%. Unchanged content: no difference. | Weak: different semesters, not randomised; the title was also larger and bold; two questions went the other way. Farkas: poor control slides, gains "surprisingly modest". | Alley M et al. (2006) *Tech Commun* 53(2):225-234. <https://writing.engr.psu.edu/ae_headlines.pdf>; Farkas DK (2010) unpublished assessment. <https://faculty.washington.edu/farkas/dfpubs/Farkas-Assessment%20Of%20Alleys%20Slide%20Design.pdf> |
| Never put the spoken sentences on the slide. Keep 2 to 3 word labels beside the part of the figure they describe. | Mayer: narrated diagram slides; 2 to 3 printed words by the diagram raised retention (d = 0.47 and 0.70), not transfer. Yue: text identical to the narration impaired recall and transfer; slightly reworded text helped. | Controlled studies, students, short recorded lessons | Mayer RE, Johnson CI (2008) *J Educ Psychol* 100(2):380-386. *(abstract)*; Yue CL et al. (2013) *J Educ Psychol* 105(2):266-277. doi:10.1037/a0031971 *(abstract)* |
| Do not strip a slide to no words: keep the key terms, above all for newcomers and figure-free slides. | 57 studies. Speech plus text beat speech alone, for low prior knowledge, system-paced and picture-free material. Key terms beat verbatim text. Liu: 120 students in a simulated classroom; slide text plus speech beat speech alone. | Meta-analysis; contradicts a strict "redundant text always hurts" | Adesope OO, Nesbit JC (2012) *J Educ Psychol* 104(1):250-263. doi:10.1037/a0026147 *(abstract)*; Liu T-C et al. (2015) *Comput Educ* 88:303-314. doi:10.1016/j.compedu.2015.04.014 *(abstract)* |
| If a point matters, put it on the slide in short form; a dense slide makes the audience miss what is only said. | 209 students; no slides, regular slides or concise slides. Regular slides suppressed retention of spoken-only information; concise slides did not. Cause: attention, not overload. | One controlled study | Wecker C (2012) *Comput Educ* 59(2):260-273. doi:10.1016/j.compedu.2012.01.013 *(abstract)* |
| Cut interesting but irrelevant material. | Meta-analysis: such details hinder learning. Survey of 205 audience members: "main point was obscured by lots of irrelevant detail" was the most common and most annoying fault. | Meta-analysis; survey | Sundararajan N, Adesope O (2020) *Educ Psychol Rev* 32:707-734. doi:10.1007/s10648-020-09522-4 *(abstract)*; Kosslyn SM et al. (2012) *Front Psychol* 3:230. doi:10.3389/fpsyg.2012.00230 |
| Break a long explanation into meaningful segments and mark what to look at. | Segmenting: 56 investigations, small to medium gains, also when system-paced; larger for high prior knowledge. Overview of 29 reviews: signalling among the largest effects; design matters more for complex, system-paced material. | Meta-analyses | Rey GD et al. (2019) *Educ Psychol Rev* 31:389-419. doi:10.1007/s10648-018-9456-4 *(abstract)*; Noetel M et al. (2022) *Rev Educ Res* 92(3):413-454. doi:10.3102/00346543211052329 *(abstract)* |
| Explain a figure aloud, not in a paragraph beside it. For a deck people read alone, write the words down. | 43 effects: speech plus picture beat text plus picture, strongly when system-paced. Tabbers: 111 self-paced students; speech did worse. | Meta-analysis; reverses when self-paced | Ginns P (2005) *Learn Instr* 15(4):313-331. doi:10.1016/j.learninstruc.2005.07.001 *(abstract)*; Tabbers HK et al. (2004) *Br J Educ Psychol* 74:71-81. doi:10.1348/000709904322848824 *(abstract)* |
| Spell out any term or abbreviation not in the audience's daily use. | 650 people: jargon impaired processing. 79% of 1.1 million acronyms appeared fewer than 10 times. | One experiment on written text; one count of papers | Bullock OM et al. (2019) *Public Underst Sci* 28(7):845-853. doi:10.1177/0963662519865687 *(abstract)*; Barnett A, Doubleday Z (2020) *eLife* 9:e60080. doi:10.7554/eLife.60080 |
| Write notes as an outline in other words than the slide's. | Doumont: memorise a tree of points, not a script. Yue (above): speech identical to slide text impairs. | Expert opinion plus one study | As above |

### Against our retro

- **"Phrases not sentences"** holds for the body. The title is the exception: Naegle, Doumont and Alley want a sentence; Farkas leaves it to the speaker.
- **Less text is not always better.** Key terms help low-knowledge listeners and figure-free slides. No study here tested experts.
- **"Reveal by section, not bullet by bullet"** is untested. Kosslyn's rules count bullets shown all at once as a fault (96% of 140 decks); that is his rule, not a result.
- **Audience liking is a poor guide.** Garner's better-learning group rated its text amount as less appropriate; Yue's students preferred the identical text that hurt them.

### Open points

- Talk length: Lortie covers 5 minutes; nothing found separates 15 from 50. His 20 slides in 5 minutes conflicts with one per minute.
- Nearly all experiments used students and short recorded lessons, not experts at a live seminar.
- Speaker notes: no study found.
- Chinese slides: no credible source found. Nearest: Liu 2015 (Taiwan; lesson language not confirmed) and Noetel's largest effect, captions on second-language video, which suggests on-screen key terms help second-language listeners (my inference).

## Evidence for the visual slide rules: legibility, colour, figures, animation, layout

Slide: 16:9, 13.33 x 7.5 inch, so height H = 540 pt. Font proportions assumed by me: Latin x-height (height of a lowercase "x") about 0.5 of the point size
(Times New Roman is 0.45, per Legge and Bigelow), capital height about 0.7, a Chinese character
about 0.9.

### Rules and evidence

| Rule | What the source reports | How established | Source |
| --- | --- | --- | --- |
| 1. Size text by the farthest viewer: text height as % of slide height >= (viewer distance / screen height) / 200. | Table of minimum "%element height" by viewing ratio: 1.5% at 2-3 screen heights, 2.5% at 4-5, 3% at 5-6, 4% at 7-8, 5% at 9-10. "Acuity factor" 200. Every row fits distance = 200 x element height (my reading; formula paywalled), a visual angle of 17 arcminutes. | Standard, paywalled; open first-party summary | AVIXA (Audiovisual and Integrated Experience Association), "Display Image Size for 2D Content in Audiovisual Systems", ANSI/INFOCOMM V202.01. <https://www.avixa.org/standards/discas-calculators/discas/learn-more-about-display-size> |
| 2. Keep lowercase x-height at or above 0.2 degrees for the back row. | Reading speed falls sharply below a "critical print size"; consensus 0.2 degrees of x-height (range 0.15-0.3). Letters stay identifiable at about half that. | Review of controlled studies | Legge GE, Bigelow CA (2011) J Vision 11(5):8. doi:10.1167/11.5.8 |
| 3. Flag any text at or below 20 pt. | Words not "greater than 20 point" count as a flaw; 65% of 140 sampled decks broke it. | Expert rule; the 20 pt figure is not itself tested | Kosslyn SM et al. (2012) Front Psychol 3:230. doi:10.3389/fpsyg.2012.00230 |
| 4. Give Chinese text the same point floor as Latin, never a lower one; go larger for dense characters. | At the acuity limit, characters of average complexity (8-9 strokes) need 1.62 times the height of the Snellen E; the simplest need 37% more than Sloan letters. Thicker strokes lowered the threshold (4.66 to 4.31 arcminutes, P = 0.052). | Controlled study, small; threshold, not reading speed | Zhang J-Y et al. (2007) Invest Ophthalmol Vis Sci 48:2383-2390. doi:10.1167/iovs.06-1195 |
| 5. Text contrast >= 4.5:1; >= 3:1 only for large text. | 4.5:1 normal text, 3:1 for "18 point or 14 point bold". Thin-stroke fonts render fainter. | Standard (World Wide Web Consortium), written for screens | WCAG (Web Content Accessibility Guidelines) 2.2, Understanding 1.4.3. <https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html> |
| 6. Take category colours from the 8-colour palette: black 0,0,0; orange 230,159,0; sky blue 86,180,233; bluish green 0,158,115; yellow 240,228,66; blue 0,114,178; vermillion 213,94,0; reddish purple 204,121,167. | Distinguishable under red-green colour blindness: up to 8% of Northern European men (Okabe and Ito: 5% of Asian men). | Expert design, widely adopted | Wong B (2011) Nat Methods 8:441. doi:10.1038/nmeth.1618; Okabe M, Ito K (2002, rev. 2008) <https://jfly.uni-koeln.de/color/> |
| 7. At most 6-8 category colours per slide; above 6-7 categories split into panels. | "A group of 6-8 colors. Beyond this number... picking distinctive colors becomes difficult"; over six or seven categories, use small multiples. | Expert opinion | Wong B (2010) Nat Methods 7:573; Krzywinski M, Wong B (2013) Nat Methods 10:451 |
| 8. Never encode by colour alone; add shape, line style or position. No red text on dark; no red-green pairs (use magenta-green). | Dark red looks near black to viewers lacking red receptors. | Expert opinion | Okabe and Ito, as above |
| 9. Label series directly; no separate legend. | Matching colours between a key and distant marks is "extremely difficult" for colour-blind viewers. Rougier's improved example labels each plot, with no legend box. | Expert opinion | Okabe and Ito; Rougier (row 10) |
| 10. Redraw a paper figure for the slide: remove detail, thicken lines, enlarge labels, no vertical text, no plot background. | "Abandon the practice of extracting a figure from your article to be put, as is, in your oral presentation"; the slide version has "bigger axis and tick labels, no title, thicker lines". No sizes given. | Expert opinion | Rougier NP, Droettboom M, Bourne PE (2014) PLoS Comput Biol 10(9):e1003833. doi:10.1371/journal.pcbi.1003833 |
| 11. Colour or highlight only the element the slide is about; if there is no reason for a colour, use black. | Experiment cited by Wong: making the irrelevant variable most visible on a weather map made viewers answer from it. Rougier: no reason for a colour, "keep it black". | One controlled study (cited, not opened) plus expert opinion | Wong B (2011) Nat Methods 8:889. doi:10.1038/nmeth.1762; Rougier, as above |
| 12. No looping movies, no moving emphasis, no decorative transitions. | "An oscillating arrow will draw more of our attention than the objects it is intended to highlight". Kosslyn lists uninformative change as a flaw. | Expert opinion | Wong 8:889; Kosslyn 2012 |
| 13. Reveal by section, not line by line. | Against: students scored lower after a recorded lecture with step-by-step entrances than with static slides (82% vs 71%, p < 0.001; direction from the abstract). For: Kosslyn counts unbuilt bullet lists as a flaw. | Contested: one lab against an expert rule | Mahar S, Yaylacicegi U, Janicki TN (2009) Inf Syst Educ J 7(82). <http://isedj.org/7/82/>; Kosslyn 2012 |
| 14. At most 4 groups per slide, 4 items per list, 2 lines per bullet. | Working memory holds about four units, each of about four. | Rule from established memory research; cut-offs are expert | Kosslyn 2012 |
| 15. Do not choose a font by serif. | Fonts differing only in serifs: no difference in reading speed; a "tiny" gain at small sizes, from spacing. | Controlled study, small | Arditi A, Cho J (2005) Vision Res 45:2926-2933. doi:10.1016/j.visres.2005.06.013 (abstract only) |

### Verdict on 24 pt default and 18 pt floor

Farthest readable seat, in screen heights (H):

| Size | x-height | AVIXA, x-height as element (x 200) | AVIXA, capital height as element | Legge, fluent reading (x-height / tan 0.2 deg = x 286) |
| --- | --- | --- | --- | --- |
| 24 pt | 12 pt = 2.22% H | 4.4 H | 16.8 pt = 3.11% -> 6.2 H | 6.4 H |
| 18 pt | 9 pt = 1.67% H | 3.3 H | 12.6 pt = 2.33% -> 4.7 H | 4.8 H |
| 14 pt | 7 pt = 1.30% H | 2.6 H | 9.8 pt = 1.81% -> 3.6 H | 3.7 H |

- **24 pt default: supported** for rooms up to about 6 screen heights deep, and it clears Kosslyn's
  "greater than 20 pt".
- **18 pt floor: too small as a general floor.** It reaches only 3-5 screen heights (a meeting room)
  and breaks the 20 pt rule. A 20 pt floor reaches 3.7-5.3 H. For a
  hall 8 H deep, AVIXA needs 4% = 21.6 pt of element height: 31-43 pt type.
- Lint floor from room depth in screen heights: points >= depth x 540 / 200 / 0.5 (strict) or
  / 0.7 (lenient).
- Chinese: a 24 pt character is about 21.6 pt tall, 1.8 times the Latin x-height, which roughly
  offsets the 1.62 factor. Same floor.

### Open points

- Which part of a letter AVIXA counts as the "element": paywalled.
- ISO 9241-303 (display ergonomics), with a reported 20 arcminute minimum for Chinese text:
  paywalled, seen second-hand, not used.
- Projected contrast under room light: no source opened.
- Hei (even strokes) versus Song (thin horizontals): only the stroke result in row 4. Chi, Cai
  and You (2003, Ergonomics) reportedly rank Hei most legible; not opened.
- Stepwise reveal: a meta-analysis of segmenting exists (Rey et al. 2019, Educ Psychol Rev
  31:389) but was not opened in full.
- Whitespace and alignment: nothing measured; only Wong's advice to align blocks so gaps
  form regular bands (Nat Methods 8:5, doi:10.1038/nmeth0111-5).
- No source gives label sizes for slide figures; apply the text floor to axis labels.

## lab-deck tooling: four claims checked

Checked 2026-11-09 on macOS arm64. Tiers: **verified** (ran it), **read** (first-party docs or
source), **unverified**.

### 1. PowerPoint scripting on macOS

**Yes, the dictionary has every piece. Tier: read. Nothing was sent to PowerPoint.**

`sdef` itself failed: it needs full Xcode, and this machine has only the command line tools.
I read the same dictionary from the app bundle instead (`Info.plist` key
`OSAScriptingDefinition` = `PowerPoint.sdef`, in `Contents/Resources/`), PowerPoint 16.114.3.

| Need | Name in the dictionary |
| --- | --- |
| Unsaved changes | class `presentation`, property `saved` (boolean, read-write) |
| Which file | `presentation` properties `full name`, `path`, `name`, `read only` |
| Front deck | `application` properties `active presentation`, `active window` |
| Save, close, open | Standard Suite, included from the system `CocoaStandard.sdef`: `save` (`in` file, `as`), `close` (`saving` yes/no/ask, `saving in`), `open` (files) |
| Go to a slide | command `go to slide`, direct parameter a `view`, parameter `number` (integer). `document window` has property `view`; `view` has a writable `slide` property |
| Current slide | `slide` properties `slide index`, `slide number`, `slide ID` |

So the expected spelling is `go to slide (view of document window 1) number N`. **Unverified:**
that `presentation` accepts the standard `save` and `close` (the dictionary declares them for
"document(s) or window(s)" and gives `presentation` no `responds-to` line), and any behaviour
at run time.

**Permission.** The first Apple event from the calling app to PowerPoint needs the user's
consent; the grant is listed under System Settings > Privacy & Security > Automation, per
calling app (read:
<https://support.apple.com/guide/mac-help/allow-apps-to-control-other-apps-mchl07817563/mac>).
The prompt's exact wording and the error a denied script gets: unverified.

**Is the file open?** **Unverified.** I found no first-party Microsoft page on the
`~$name.pptx` owner file for PowerPoint; only community answers on Microsoft Q&A, one of which
reports PowerPoint does not always keep it
(<https://learn.microsoft.com/en-gb/answers/questions/4377821/why-do-some-computers-retain-the-*-pptx-file-after>).
`lsof -p <PowerPoint pid>` on the running app showed zero `.pptx` handles, but I could not
tell whether a deck was open, so that test is inconclusive. Asking PowerPoint (`full name` of
each `presentation`) is the documented route.

### 2. Installing PptxGenJS

**It is on conda-forge. Add it to pixi; neither npm route is needed. Tier: verified (package
exists and its contents), read (how Node finds it).**

- `pixi search pptxgenjs`: `pptxgenjs 4.0.1`, build `hc364b38_0`, `noarch`, 884 KiB, depends on
  `nodejs`. Only this version is listed.
- I downloaded the `.conda` to scratch and listed it: files land in
  `lib/node_modules/pptxgenjs/`, with its dependencies (`jszip`, `image-size`, `https`,
  `@types/node` and theirs) bundled in a nested `node_modules`. SHA256 matched the index.
- Node does not search `$PREFIX/lib/node_modules` by default, so the wrapper must set
  `NODE_PATH` to it or require by absolute path (read:
  <https://nodejs.org/api/modules.html>, "Loading from the global folders"). Not run.
- pixi Node is `v22.23.4`, npm `10.9.9` (verified).
- `npm view pptxgenjs`: version `4.0.1`, tarball
  `https://registry.npmjs.org/pptxgenjs/-/pptxgenjs-4.0.1.tgz`, integrity
  `sha512-TeJISr8wouAuXw4C1F/mC33xbZs/FuEG6nH9FG1Zj+nuPcGMP5YRHl6X+j3HSUnS1f3at6k75ZZXPMZlA5Lj9A==`,
  dependencies `@types/node ^22.8.1`, `https ^1.0.0`, `image-size ^1.2.1`, `jszip ^3.10.1`.

| | First use | On plugin update | Cost |
| --- | --- | --- | --- |
| **conda-forge in pixi (recommended)** | Network, inside the `pixi install` the environment already needs | New version directory rebuilds the environment as today; packages come from pixi's cache | Pinned by `pixi.lock` hash. Only 4.0.1 exists, so decks on 3.12 move up a major |
| (a) `npm ci` to an outside cache | Network, unless npm's cache is warm | Survives only if the cache key is the lock file's hash, not the plugin version | A second lock file and install step to own |
| (b) Archive in the repo | None | Ships again with every version | 1.6 MB binary in a public repo; checksum code to write |

npm facts (read): `npm ci` requires a lock file, errors on a mismatch with `package.json`,
deletes any `node_modules` first, never writes the lock
(<https://docs.npmjs.com/cli/v10/commands/npm-ci>). The lock stores an SRI `integrity` hash per
package (<https://docs.npmjs.com/cli/v10/configuring-npm/package-lock-json>). The cache
verifies data "on both insertion and extraction"
(<https://docs.npmjs.com/cli/v10/commands/npm-cache>). npm's offline flags: not read.

### 3. PptxGenJS limits

**All three hold, in 3.12.0 and in the current 4.0.1. Tier: read (source at tags `v3.12.0` and
`v4.0.1`).** Latest release is 4.0.1, 2025-06-25; it changes none of them.

- **No group shapes.** `src/` writes `p:grpSp` nowhere; the only group element is the slide's
  own root (`src/gen-xml.ts` line 101). Issue #307 (open since 2018); pull request #929 "Add
  support for groups" was closed unmerged.
- **`addTable()` reuses ids.** `src/gen-xml.ts` line 175: table id is
  `intTableNum * slide._slideNum + 1`; other objects use `idx + 2` (line 412; 410 in 3.12.0).
  The first table on slide 1 gets id 2, the same as the first object. Issue #1532 (open).
- **`slideNumber` reuses an id.** `src/gen-xml.ts` line 705 (703 in 3.12.0): a fixed
  `id="25"`, which equals the id of the 24th object on a slide. No issue found for this one.

Source: <https://github.com/gitbrent/PptxGenJS>.

### 4. Rendering and measuring

**(a) Poppler yes, LibreOffice no. Tier: verified.** `pixi search poppler --platform
osx-arm64` gives `poppler 26.11.0`; its archive contains `bin/pdftoppm`. `pixi search
'*libreoffice*'` finds nothing for osx-arm64 or linux-64, so it must be the system app
(a current release is installed here).

**(b) Both libraries work. Tier: verified**, in a throwaway `pixi exec` environment (Pillow
13.0.0, fontTools 4.68.0; neither is in the repo environment today).

- Pillow: `ImageFont.truetype(path, size).getlength(text)`, in pixels
  (<https://pillow.readthedocs.io/en/stable/reference/ImageFont.html>).
- fontTools: `TTFont(path)`, `getBestCmap()`, `getGlyphSet()[name].width`, scaled by
  `font["head"].unitsPerEm`
  (<https://fonttools.readthedocs.io/en/latest/ttLib/ttFont.html>).
- Same string in Arial at 100 px: 652.0 (Pillow, basic layout) against 650.3 (fontTools, summed
  advances, no kerning). Close enough for a lint.

**(c) Hidden slides are skipped by default, and there is an option. Tier: read.**
`ExportHiddenSlides`, boolean, default `false`: "exports slides not included in slide shows".
Passed as
`--convert-to 'pdf:<filter>:{"ExportHiddenSlides":{"type":"boolean","value":"true"}}'`
(<https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html>). The page names
no Impress filter; the installed app's `registry/impress.xcd` contains `impress_pdf_Export`.
Not run.
