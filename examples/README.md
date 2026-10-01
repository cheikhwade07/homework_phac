# Example requests

Output of the command-line tool for four different requests. Only the request text
changes between runs; the code and the prompt template are the same.

| Request | Command | Output |
|---|---|---|
| Leukemia | `casefilter "Filter the cases related to leukemia." --n 20 --seed 3` | [leukemia.txt](leukemia.txt): 2 of 20 relevant |
| Infectious disease | `casefilter "Filter the cases related to infectious disease." --n 20 --seed 3` | [infectious_disease.txt](infectious_disease.txt): 8 of 20 relevant |
| Cardiovascular disease | `casefilter "Filter the cases related to cardiovascular disease." --n 20 --seed 3` | [cardiovascular_disease.txt](cardiovascular_disease.txt): 5 of 20 relevant |
| E-scooter injuries | `casefilter "Filter the cases associated with e-scooter injuries." --keyword scooter --n 40` | [escooter_injuries.txt](escooter_injuries.txt): 7 of 40 relevant |

The first three runs classify the same 20 random cases. The e-scooter run uses the keyword
pre-filter, because only 40 of 110,182 cases mention a scooter.

Each file shows how the request was interpreted, the result for every case, and the
relevant cases with the reason and the supporting quote.
