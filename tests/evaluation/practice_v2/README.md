# Practice set v2 (development, not held-out)

This set contains 400 newly written questions across 16 categories (25 each).
It was split with Python `random.Random(5703)`: shuffle the 25 indices in
each category, put 12 from each of the first eight categories and 13 from
each of the last eight into training, then shuffle each half. The result is
`train.json` (200 questions) and `validation.json` (200 questions). The split
and expectations were committed before either half was run.

Validation SHA-256, calculated immediately after file creation:

`c1dc7a842e4cf1d4fc4b72d23ada48cc13a6e0f56711ebb7cb0eb857d0936e97`

The validation half is locked: do not open, print, or run it until the
training target is met and the B5 validation run is authorised. Results on
training are development results. After validation is used to inform any
change, it is spent too. Neither is a final blind held-out result.

Before splitting, a script checked all 400 questions for shared five-word
phrases against the dev 50, held-out v1-v4, client v1, practice v1, and the
user-supplied v5/v6 wording kept outside Git. Result: zero shared phrases.
The user-supplied v5/v6 text was reconstructed from the supplied message;
it is not asserted to be a byte-for-byte copy of the original files.

Each row records its expected request category, response mode, visible tag,
and whether the local support line is required. In-scope rows also specify
their feature. Ambiguous-feature and unsupported-window non-answers require
the support line in this version. For answered in-scope rows, `answer` means
an eligible evidence response (`normal` or `uncertainty`) grounded in the
named feature, not a literal API response mode.
