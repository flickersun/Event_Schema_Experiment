# Qualtrics setup

Two surveys wrap the experiment:

```
SONA  →  Qualtrics 1 (consent + demographics)
      →  the experiment (GitHub Pages)
      →  Qualtrics 2 (familiarity + debrief)
      →  SONA credit
```

Two surveys rather than one because the SONA credit URL contains `&` parameters:
letting **Qualtrics 2** do that redirect means it never has to be percent-encoded by
hand, which is the easiest thing in this chain to get silently wrong.

`survey1_pre.txt` and `survey2_post.txt` import the question content. Survey flow,
embedded data and redirects are **not** covered by the TXT format and must be set by
hand — that is everything in steps 2–4 below.

---

## 1. Import the questions

Qualtrics → **Create new project** → **Survey** → **From a file** → upload the `.txt`.
Do this twice, once per file. Name them e.g. `Event Schema — Part 1` and `— Part 2`.

Two blocks in the imported text are placeholders you **must** replace with your
IRB-approved language: the consent block in Part 1 and the debrief block in Part 2.

## 2. Embedded data (both surveys)

**Survey Flow** → **Add a New Element** → **Embedded Data** → drag it to the very top.
Add one field, leave the value blank so it is captured from the URL:

```
sona
```

Blank value = "take it from the query string". Both surveys need this.

## 3. Redirects

**Part 1** → Survey Options → **Survey Termination** → *Redirect to a URL*:

```
https://flickersun.github.io/Event_Schema_Experiment/?pid=${e://Field/sona}&next=<ENCODED_PART2_URL>
```

`<ENCODED_PART2_URL>` is Part 2's anonymous link, percent-encoded, with the code
passed on. If Part 2's link is
`https://ucdavis.co1.qualtrics.com/jfe/form/SV_ABC123`, then:

```
https%3A%2F%2Fucdavis.co1.qualtrics.com%2Fjfe%2Fform%2FSV_ABC123%3Fsona%3D${e://Field/sona}
```

so the whole thing reads:

```
https://flickersun.github.io/Event_Schema_Experiment/?pid=${e://Field/sona}&next=https%3A%2F%2Fucdavis.co1.qualtrics.com%2Fjfe%2Fform%2FSV_ABC123%3Fsona%3D${e://Field/sona}
```

Encoding table for the part after `next=`: `:` → `%3A`, `/` → `%2F`, `?` → `%3F`,
`=` → `%3D`, `&` → `%26`. Encoding is required because an unencoded `?` or `&` would
be read as belonging to the *experiment's* URL, so `next` would arrive truncated and
the participant would never reach Part 2 — with no error shown.

**Part 2** → Survey Termination → *Redirect to a URL*: paste the SONA completion URL
exactly as SONA gives it (no encoding needed here), appending the code:

```
https://ucdavis.sona-systems.com/webstudy_credit.aspx?experiment_id=XXXX&credit_token=YYYY&survey_code=${e://Field/sona}
```

## 4. SONA study settings

- **Should participants be identified only by a random, unique ID code?** → **Yes**.
  Data then carry a random code rather than anything identifying, and credit still
  works through the completion URL.
- **Study URL** → Part 1's anonymous link with the code appended:

```
https://ucdavis.co1.qualtrics.com/jfe/form/SV_PART1?sona=%SURVEY_CODE%
```

## 5. Optional screening

`device_ok` and `consent` in Part 1 are worth branching on: in Survey Flow add a
Branch so that answering "No" to either skips to an End-of-Survey element with a short
message, rather than continuing into the study.

---

## Test the whole chain before recruiting

Start from SONA as a real participant would and go all the way through until you see
the credit granted. Check at each hand-off:

1. Part 1 loads and `sona` is populated (Survey Flow → the embedded data shows a value)
2. The experiment loads and the saved data's `subject_id` equals that code
3. The experiment hands off to Part 2 and `sona` is still populated there
4. Part 2 redirects to SONA and credit appears

Every one of these fails **silently** if a parameter is wrong — the participant simply
finishes without credit, or the data arrive with no usable identifier. This is the one
part of the setup that cannot be verified by reading it.

## Notes

- The familiarity item uses a 1–7 scale, per spec §4. The scales *inside* the
  experiment are 6-point; that is deliberate and unrelated (6-point, even, no neutral
  midpoint is what the confidence-ROC analysis needs). Familiarity is a covariate, so
  its scale length does not matter.
- `order_predictability` is a secondary manipulation check. The per-scene rating
  collected during encoding already serves that purpose, so this block can be dropped
  if you want to shorten Part 2.
- `guessed_purpose` is worth keeping: participants who report having expected a memory
  test were not encoding incidentally, and you may want to check whether excluding
  them changes the results.
