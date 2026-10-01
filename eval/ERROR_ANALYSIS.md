# Error Analysis

Where the LLM's classification differs from the reference labels, and why.

All numbers come from `eval/results/` (see `SUMMARY.md`). The per-case rows, with the
model's reason and evidence quote, are in `eval/results/<request>.<prompt>.predictions.csv`.

## Summary of the four prompt versions

| Request | Prompt | Precision | Recall | F1 | False positives | False negatives |
|---|---|---|---|---|---|---|
| E-scooter (n=60, 4 relevant) | v1 baseline | 0.44 | 1.00 | 0.61 | 5 | 0 |
| | v2 rules + evidence | 0.29 | 1.00 | 0.44 | 10 | 0 |
| | **v3 expanded definition** | 0.57 | **1.00** | 0.73 | 3 | 0 |
| | v4 definition + role step | **0.67** | **1.00** | **0.80** | 2 | 0 |
| Cardiovascular (n=40, 18 relevant) | v1 baseline | **0.89** | 0.89 | **0.89** | 2 | 2 |
| | v2 rules + evidence | 0.79 | 0.83 | 0.81 | 4 | 3 |
| | **v3 expanded definition** | 0.69 | **1.00** | 0.82 | 8 | 0 |
| | v4 definition + role step | 0.80 | 0.89 | 0.84 | 4 | 2 |

**No version is best on both requests.** The baseline has the best F1 on cardiovascular
disease and v4 on e-scooter injuries. With 40 and 60 cases, and only 4 relevant e-scooter
cases, one label moves a score by several points, so these rankings are indicative, not
conclusive.

v3 is the default because it is the only version with no false negatives on either
request, and a filter that feeds human review should miss as little as possible. v4 has a
higher F1 than v3 on both sets but missed two relevant cardiovascular cases.

## What each version taught

**v1 (the template from the brief).** A reasonable baseline. Its two false negatives on
cardiovascular disease were both **strokes**: the model did not count cerebrovascular
disease as cardiovascular, while the reference definition (WHO) does. On e-scooters it
accepted "scooter accident" and "motorized scooter" as e-scooter injuries.

**v2 (explicit relevance rules, evidence quote).** Scored *below* the baseline on both
requests. v2 changed several things at once (system prompt, tags, evidence field), so the
cause is not isolated, but the model's own reasons suggest two problems:
- The instruction to "include recognised subtypes and synonyms" appears to have been
  applied backwards in some cases: *"a skate scooter, which is a type of e-scooter"*.
- "Significant finding" was read as any related sign: tachycardia or hypotension was
  enough for cardiovascular disease.
Adding rules also did not fix the stroke scope problem, because the rules never said what
the concept covers.

**v3 (criterion expansion).** The request is first rewritten once into an explicit
definition with inclusions and exclusions, and each case is judged against it.
- E-scooter: the definition lists "scooter injury (unspecified type)" as excluded, which
  removed the unspecified-scooter false positives (precision 0.44 to 0.57).
- Cardiovascular: the definition includes stroke, which recovered both false negatives
  (recall 0.89 to 1.00). But it also lists "hypertension" and "arrhythmia", and the model
  then accepted any mention of them, including past history. Precision fell to 0.69.

**v4 (role step).** The model first names the role of the concept (active, history,
incidental, look-alike, absent) and may answer YES only for an active role. This removed
four of v3's eight cardiovascular false positives and one of three on e-scooters, but
reintroduced two cardiovascular false negatives.

**Reasoning budget.** In a side experiment (results not saved to `eval/results/`), giving
the model a 1,024-token thinking budget changed results by one or two cases in either
direction and roughly tripled latency, so thinking stays disabled.

## Default prompt (v3): every disagreement

### E-scooter injuries: 3 false positives, 0 false negatives

| Case | Reference | What happened | Category |
|---|---|---|---|
| PMC9046070_01 | NO | A transport study that mentions "the high accident rate of e-scooters". No patient and no injury is described. Wrong in all four versions. | Model error: topic match instead of case relevance |
| PMC9168337_01 | NO (ambiguous) | A child "riding at 30 mph on a motorized scooter". The text never says electric, and the generated definition counts "motorized scooter injury" as included. | Criterion ambiguity |
| PMC3884183_01 | NO (ambiguous) | A boy injured on a carousel that was driven by an electric scooter. The guidelines require riding one or being hit by one. | Criterion ambiguity |

### Cardiovascular disease: 8 false positives, 0 false negatives

| Case | Reference | What happened | Category |
|---|---|---|---|
| PMC6357786_01 | NO | Hypertension only in the past history | Model error: history rule not applied |
| PMC5438004_01 | NO (ambiguous) | Heart failure and pacemaker in the history; the case is about kidney injury on warfarin | Criterion ambiguity |
| PMC5791395_01 | NO (ambiguous) | Tachycardia and hypertension caused by a bladder paraganglioma | Criterion ambiguity |
| PMC8554308_01 | NO (ambiguous) | Shock from blood loss and intracranial haemorrhage in a newborn | Criterion ambiguity |
| PMC10466787_01 | NO (ambiguous) | Thymic carcinoma invading the pericardium | Criterion ambiguity |
| PMC7305409_01 | NO | "Unexplained tachycardia" in a vaping lung injury | Model error: sign taken for the disease |
| PMC7649878_01 | NO | Small pericardial effusion on imaging in a systemic illness | Model error: incidental finding |
| PMC4322308_01 | NO | A health-services text listing hypertension among conditions managed in clinics; not a patient | Model error: not about a patient |

## Patterns

1. **Most errors are about the definition, not about reading.** 17 of 100 reference
   labels are flagged as debatable, and 6 of v3's 11 disagreements fall on those cases.
   Excluding the flagged cases, v3 F1 is 0.86 (e-scooter) and 0.88 (cardiovascular).
2. **The model errs towards YES.** With v3 there are 11 false positives and no false
   negatives. It finds a matching phrase and treats it as sufficient, even though the
   prompt says a past-history mention or an isolated sign is not enough. The model does
   not reliably follow that rule.
3. **Explicit definitions trade precision for recall.** Naming what counts fixes scope
   errors (strokes, unspecified scooters) but each named term becomes a trigger.
4. **Text that is not a patient case is a recurring problem.** The dataset contains study
   discussions and questionnaires alongside case reports. One such text (PMC9046070_01)
   is wrong in all four versions; another (PMC4322308_01) in v3 and v4.
5. **Evidence quotes are verifiable.** For v3, 31 of 33 YES quotes were found verbatim in
   the case. The two that were not were correct labels with an inexact quote: in one the
   model joined two separate sentences, in the other it dropped a clause from the middle
   of a sentence. The check flagged both.

## Limits of this evaluation

- **Small, enriched test sets** (60 and 40 cases, with only 4 relevant e-scooter cases).
  On the full dataset positives are far rarer, so precision would be lower.
- **Tuned on the test set.** Prompts v3 and v4 and the expansion prompt were written after
  looking at errors on these same cases, and the default was chosen on them. There is no
  held-out set, so their scores are optimistic.
- **Shared wording.** The prompt's relevance rules use the same wording as the labeling
  guidelines, which favours the LLM over the embedding baselines.
- **One set of reference labels, revised once.** After a second independent read of the
  cases, two labels were changed (PMC9168337_01 from YES to NO; PMC5573896_01 from NO to
  YES) and three more were flagged as ambiguous. All results here use the revised labels.
  There is no inter-annotator agreement score.
- **Sampling noise.** The "hard negative" keyword patterns were broad. For cardiovascular
  disease they matched secondary cardiac terms, and 8 of those 10 cases turned out to be
  relevant. For e-scooters they matched some unrelated text (for example the software
  name "Unicycler" and stationary exercise bicycles).
