# Labeling Guidelines

These rules were written **before** any case was labeled. The human labels in
`eval/testsets/` follow them, and they define what "relevant" means for the evaluation.

## General rules (all requests)

A case is **relevant (YES)** when the requested concept is a **diagnosis, cause, mechanism
or significant finding of this patient's case**, including a complication that the report
describes or treats.

A case is **not relevant (NO)** when the concept:
- appears only in the past medical history or medication list and plays no role in the case;
- appears only in the family history;
- is considered and **ruled out** (for example "no evidence of myocardial infarction");
- is mentioned only as background or literature, not about this patient.

**Multiple conditions.** A case can be relevant even when the concept is not the main
diagnosis, as long as it is a significant part of the case course.

**Ambiguity.** Every case gets YES or NO. When the decision is genuinely debatable, the
`ambiguous` flag is set and the note explains why. Ambiguous cases are reported
separately in the error analysis.

**Blind labeling.** Labels are assigned without seeing any model output. The sampling
stratum of each case (keyword match, hard negative, random) is hidden while labeling.

## Request: cardiovascular disease

> Filter the cases related to cardiovascular disease.

Scope follows the WHO definition of cardiovascular diseases: disorders of the heart and
blood vessels.

**YES examples:** coronary artery disease, myocardial infarction, heart failure,
cardiomyopathy, arrhythmias (atrial fibrillation, heart block), valvular disease,
congenital heart disease, myocarditis, pericarditis, endocarditis, cardiac tumours,
aortic aneurysm or dissection, peripheral arterial disease, cerebrovascular disease
(stroke, cerebral venous thrombosis), deep vein thrombosis, pulmonary embolism, vasculitis
of large vessels, and cardiac arrest or new cardiac dysfunction occurring during the case.

**NO examples:** hypertension or hyperlipidaemia listed only as comorbidities; a normal
ECG or echocardiogram as part of a work-up; chest pain shown to be non-cardiac; anaemia,
haemorrhage or bleeding from a non-vascular cause; small-vessel findings that are
incidental.

**Usually ambiguous (flag):** hypertension that is managed during the case but is not the
focus; drug-induced cardiotoxicity mentioned as a risk only; vascular malformations.

## Request: e-scooter injuries

> Filter the cases associated with e-scooter injuries.

**YES:** an injury sustained while riding an electric scooter (e-scooter, electric
kick scooter, stand-up electric scooter), or a person injured by a collision with one.

**NO:**
- mobility scooters for people with reduced mobility;
- motor scooters, mopeds and motorcycles;
- non-electric kick scooters;
- bicycles, e-bikes, hoverboards, Segways and other vehicles;
- an e-scooter mentioned without an injury related to it.

**Usually ambiguous (flag):** "scooter" with no indication of the type; an e-scooter
accident where the report focuses on an unrelated condition found incidentally.
