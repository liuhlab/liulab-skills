# unslop-zh: Chinese that reads like Chinese

Chinese writing, strict translation and polishing. The skill loads by itself when the
deliverable contains Chinese prose, including mixed and bilingual documents. You can also call
it directly:

```text
/unslop-zh Translate this English API document into strict Simplified Chinese.
```

It routes by the deliverable's language, not the request's language. English, other
non-Chinese and pure-code deliverables do not load it.

## Writes for the task

**Original and source-based writing** start in Chinese, without an English draft. Source-based
writing uses only facts supported by the source and changes the selection or structure only
when you allow it.

**Strict translation** keeps every detail, condition, degree qualifier, technical term and
document structure. It can split or join sentences to make natural Chinese, but it does not
summarize, add explanations or remove the author's deliberate rhetoric.

**Chinese polishing** changes only actual faults inside the authorized scope. Natural text can
come back unchanged. Long sentences, passive voice and other sentence forms are not faults on
their own.

## Keeps facts and voice

Facts and certainty come before style. The skill preserves actors, conditions, scope, negation,
modality, degree, quotations and terms. Project rules and the source's conventions decide
script, regional wording, register and formatting.

Mixed documents change only the authorized Chinese prose. Code, commands, paths, versions,
placeholders, English and other protected content stay intact. A final check reads the Chinese
alone for naturalness, then compares it with the source or task for meaning and omissions.

## What it reads

Five reference pages sit behind the skill. One covers natural Chinese and minimal polishing.
Two hold Yu Guangzhong's diagnosis and repair examples for English-shaped Chinese, with his
original examples kept intact. Another covers machine-writing habits. The last covers strict
technical translation, terminology and protected mixed content.

For English prose, the agent uses `unslop` instead. It does not run both skills over the same
Chinese text.
