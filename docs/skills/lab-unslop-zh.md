# lab-unslop-zh: Chinese that reads like Chinese

The last pass over Chinese writing. It loads by itself when what you are making is in
Chinese, and stays out of the way when it is not.

Ask for a Chinese page, a Chinese protocol, or a Chinese version of an English document, and
the agent reads this skill before it writes.

## The problem it fixes

An agent asked for Chinese tends to translate instead of write. It takes the English
sentence, swaps each word for a Chinese one, and keeps the English shape. The result is
grammatical and still wrong: no one who grew up reading Chinese would put a sentence
together that way.

The other half is the sound of machine writing. Set phrases at the start of every paragraph,
a dash where a full stop belongs, lists of three when there are only two things to say.

## What it does

**It writes, instead of translating.** The rule is to read the whole passage, work out what
it means, and then say that in Chinese, breaking and reordering sentences freely. One
sentence of English does not have to become one sentence of Chinese.

**It knows when to leave your writing alone.** This matters more than the fixing. The skill
carries a list of things that are *not* a reason to edit, because a pass that rewrites
everything costs you your own voice. Your long sentences stay long. If you address your
reader formally, it keeps that, and never swaps it for the casual form.

**It keeps your facts.** Nothing may be added to make a sentence sound more specific, and a
"maybe" never turns into a "certainly".

## What it reads

Four pages sit behind it. Three come from a set of essays on how English has bent written
Chinese out of shape: one finds the fault by the kind of word doing the damage, one holds
the rewrites, and one is a check you run on your own draft. The fourth covers the habits
that mark machine writing rather than translation.

## When it does not load

If what you are making is English, the agent uses `unslop` instead, even when the subject is
Chinese. Translating a Chinese document into English is English work, so this skill stays
out of that too.
