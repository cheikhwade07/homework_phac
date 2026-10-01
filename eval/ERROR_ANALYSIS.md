# Error Analysis

Where the LLM's classification differs from the reference labels, and why.

All numbers come from `eval/results/` (see `SUMMARY.md`). The per-case rows, with the
model's reason and evidence quote, are in `eval/results/<request>.<prompt>.predictions.csv`.

## Summary of the four prompt versions

| Request | Prompt | Precision | Recall | F1 | False positives | False negatives |
|---|---|---|---|---|---|---|
| E-scooter (n=60, 5 relevant) | v1 baseline | 0.56 | 1.00 | 0.71 | 4 | 0 |
| | v2 rules + evidence | 0.36 | 1.00 | 0.53 | 9 | 0 |
| | **v3 expanded definition** | **0.71** | **1.00** | **0.83** | 2 | 0 |
| | v4 definition + role step | 0.67 | 0.80 | 0.73 | 2 | 1 |
| Cardiovascular (n=40, 17 relevant) | v1 baseline | 0.83 | 0.88 | **0.86** | 3 | 2 |
| | v2 rules + evidence | 0.74 | 0.82 | 0.78 | 5 | 3 |
| | **v3 expanded definition** | 0.65 | **1.00** | 0.79 | 9 | 0 |
| | v4 definition + role step | 0.75 | 0.88 | 0.81 | 5 | 2 |

**No version is best on both requests.** With 40 and 60 cases, a difference of one or two
cases moves F1 by several points, so these rankings are indicative, not conclusive.
v3 is the default because it is the only version with no false negatives on either
request, and a filter that feeds human review should miss as little as possible.

## What each version taught

**v1 (the template from the brief).** A reasonable baseline. Its two false negatives on
cardiovascular disease were both **strokes**: the model did not count cerebrovascular
disease as cardiovascular, while the reference definition (WHO) does. On e-scooters it
accepted any "scooter accident" as an e-scooter injury.

**v2 (explicit relevance rules, evidence quote).** Scored *worse* than the baseline. The
model's own reasons show why:
- The instruction to "include recognised subtypes and synonyms" was applied backwards:
  *"a skate scooter, which is a type of e-scooter"*. It broadened the concept.
- "Significant finding" was read as any related sign: tachycardia or hypotension was
  enough for cardiovascular disease.
- Adding rules did not fix the stroke scope problem, because the rules never said what
  the concept covers.

**v3 (criterion expansion).** The request is first rewritten once into an explicit
definition with inclusions and exclusions, and each case is judged against it.
- E-scooter: the definition lists "scooter injury (unspecified type)" as excluded, which
  removed the unspecified-scooter false positives (precision 0.56 to 0.71).
- Cardiovascular: the definition includes stroke, which recovered both false negatives
  (recall 0.88 to 1.00). But it also lists "hypertension" and "arrhythmia", and the model
  then accepted any mention of them, including past history. Precision fell to 0.65.

**v4 (role step).** The model first names the role of the concept (active, history,
incidental, look-alike, absent) and may answer YES only for an active role. This removed
four of v3's nine cardiovascular false positives but reintroduced two false negatives.

**Reasoning budget.** Giving the model a 1,024-token thinking budget changed results by
one or two cases in either direction and tripled latency (about 0.75 s to 2.5 s per
case), so thinking stays disabled.

## Default prompt (v3): every disagreement

### E-scooter injuries: 2 false positives, 0 false negatives

| Case | Reference | What happened | Category |
|---|---|---|---|
| PMC9046070_01 | NO | A transport study that mentions "the high accident rate of e-scooters". No patient and no injury is described. Wrong in all four versions. | Model error: topic match instead of case relevance |
| PMC3884183_01 | NO (ambiguous) | A boy injured on a carousel that was driven by an electric scooter. The guidelines require riding one or being hit by one. | Criterion ambiguity |

### Cardiovascular disease: 9 false positives, 0 false negatives

| Case | Reference | What happened | Category |
|---|---|---|---|
| PMC6357786_01 | NO | Hypertension only in the past history | Model error: history rule not applied |
| PMC5438004_01 | NO (ambiguous) | Heart failure and pacemaker in the history; the case is about kidney injury on warfarin | Criterion ambiguity |
| PMC5573896_01 | NO (ambiguous) | Hypertension in the history and one mention of deep vein thrombosis; the case is about encephalitis | Criterion ambiguity |
| PMC5791395_01 | NO | Tachycardia and mild hypertension as signs of a bladder paraganglioma | Model error: sign taken for the disease |
| PMC7305409_01 | NO | "Unexplained tachycardia" in a vaping lung injury | Model error: sign taken for the disease |
| PMC8554308_01 | NO | Tachycardia and hypotension from blood loss in a newborn | Model error: sign taken for the disease |
| PMC7649878_01 | NO | Small pericardial effusion on imaging in a systemic illness | Model error: incidental finding |
| PMC10466787_01 | NO | Thymic carcinoma invading the pericardium | Criterion ambiguity (tumour involving the heart lining) |
| PMC4322308_01 | NO | A health-services text listing hypertension among conditions managed in clinics; not a patient | Model error: not about a patient |

## Patterns

1. **Most errors are about the definition, not about reading.** In the reference labels
   14 of 100 cases were flagged as debatable, and 4 of the 11 disagreements above fall on
   those cases or on a borderline concept. Excluding the flagged cases, v3 F1 is 0.86
   (e-scooter) and 0.81 (cardiovascular).
2. **The model errs towards YES.** With v3 there are 11 false positives and no false
   negatives. It finds a matching phrase and treats it as sufficient, even when the rules
   say a past-history mention or an isolated sign is not enough.
3. **Explicit definitions trade precision for recall.** Naming what counts fixes scope
   errors (strokes, unspecified scooters) but each named term becomes a trigger.
4. **Text that is not a patient case confuses every version.** The dataset contains study
   discussions and questionnaires alongside case reports.
5. **Evidence quotes are verifiable.** Across the v3 runs, 31 of 33 YES quotes were found
   verbatim in the case. The two that were not were correct labels where the model had
   joined two separate sentences into one quote. The check flagged both.

## Limits of this evaluation

- The test sets are small (60 and 40 cases) and enriched with likely positives and hard
  negatives. On the full dataset positives are far rarer, so precision would be lower.
- Prompts v3 and v4 were written after looking at errors on these same cases. There is no
  separate held-out set, so their scores are optimistic.
- One set of reference labels was used. A second annotator and an agreement score would
  show how much of the disagreement is inherent to the task.
