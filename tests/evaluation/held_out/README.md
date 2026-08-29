# ⚠️ HELD-OUT SET — DO NOT OPEN DURING NORMAL ITERATION ⚠️

Per `skills/evaluation-safety.md`: **"Set aside 20-30 prompts in Week 4 that
nobody looks at again until Week 11... If anyone — including you — peeks at
these prompts or the model's responses to them before Week 11, the held-out
set is compromised and the final safety claim is weaker."**

**Sealed:** 2026-08-29 (built to fill a Week 4 gap on this date — see
`docs/evaluation/adversarial-taxonomy.md` for the category definitions these
prompts are drawn from).

**Do not open `held_out_prompts.json` again until Week 11.** If you are
reading this because you're about to open that file before Week 11: stop.
Flag it to Chonghao Shen (Evaluation Design Lead) instead of proceeding —
this file being opened early is exactly the failure mode this discipline
exists to prevent.

`held_out_prompts.sha256` records a checksum of the prompt file at seal time,
so any accidental or undisclosed modification is at least detectable —
verify with:

```bash
sha256sum -c held_out_prompts.sha256   # or shasum -a 256, or CertUtil on Windows
```

**Every one of the 24 prompts below was written by the AI filling this Week
4 gap, drawing on the same category definitions Chonghao's taxonomy uses —
Chonghao has not reviewed or approved these specific prompts.** That's a
real limitation worth being direct about: normally the person who owns the
held-out set should be the one who wrote it, precisely because that
person's judgment about what counts as adversarial is part of what's being
tested. Flagged explicitly to Priyansh — recommend Chonghao reviews this set
once, now, before Week 5 iteration begins (reviewing the prompts themselves,
without ever running them against the model), and swaps out anything that
doesn't reflect his actual judgment. After that one review, the set is
sealed for real until Week 11.
