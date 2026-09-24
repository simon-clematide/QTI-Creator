#!/usr/bin/env python3
"""Generate sample QTI 2.1 zip packages for each supported question format.

This allows manual verification in OpenOLAT with minimal effort.
Each question format is saved as its own self-contained .zip package
and accompanied by its source .md file.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.packager import create_qti_package
from src.parser import parse_quizmd

OUTPUT_DIR = Path("sample_quizzes")

SAMPLES = {
    "01_single_choice": """---
title: "Sample 01 - Single Choice"
---

## What is the capital of Switzerland?

Hint: It is de facto the federal city (Bundesstadt).
Feedback: Bern is the federal city of Switzerland.

- [ ] Zurich
- [ ] Geneva
- [X] Bern
- [ ] Basel
""",

    "02_multiple_choice_partial": """---
title: "Sample 02 - Multiple Choice (Partial Scoring)"
---

## Which of the following are official languages of Switzerland?

Hint: Think of the four national language regions.
Feedback: German, French, Italian, and Romansh are official national languages. English and Spanish are not.

- [x] German
- [x] French
- [x] Italian
- [ ] English
- [ ] Spanish
""",

    "03_multiple_choice_all_correct": """---
title: "Sample 03 - Multiple Choice (All Correct)"
scoring: all-correct
---

## Select all prime numbers:

Hint: Primes have exactly two distinct positive divisors: 1 and themselves.
Feedback: 2, 3, and 5 are prime numbers. 4 and 6 are composite numbers.

- [x] 2
- [x] 3
- [ ] 4
- [x] 5
- [ ] 6
""",

    "04_multiple_choice_per_answer": """---
title: "Sample 04 - Multiple Choice (Per Answer Points)"
scoring: per-answer
---

## Which of the following planets are gas giants?

Hint: Jupiter and Saturn are famous examples.
Feedback: Jupiter and Saturn are gas giants; Mars is a terrestrial planet.

- [x] Jupiter
- [x] Saturn
- [ ] Mars
""",

    "05_kprim": """---
title: "Sample 05 - Kprim Matrix"
---

## Evaluate these statements about Mammals:

Hint: Consider hair, milk production, reproduction, and body temperature.
Feedback: Monotremes (e.g. platypus) lay eggs, and mammals are endothermic.

- [+] They possess hair or fur.
- [+] Females produce milk to nourish their young.
- [-] All mammals give birth to live young without exception.
- [-] Mammals are ectothermic organisms.
""",

    "06_true_false": """---
title: "Sample 06 - True / False"
---

## The Earth completes one full orbit around the Sun in approximately 365.25 days.

Hint: Think about why leap years exist.
Feedback: A solar year is approximately 365.2422 days, which is rounded to 365.25 days.

- [X] True
- [ ] False
""",

    "07_fill_blank_single_gap": """---
title: "Sample 07 - Fill in the Blank (Single Gap)"
---

## Color Spelling

Hint: Think of the common US English spelling.
Feedback: In American English, 'gray' is preferred, though 'grey' is also accepted.

The American spelling of the colour is {{gray | grey}}.
""",

    "08_fill_blank_multi_gap": """---
title: "Sample 08 - Fill in the Blank (Multiple Gaps)"
---

## Irregular Verb Forms

Hint: Base verb is 'go'.
Feedback: went is past simple, gone is past participle.

The past tense of go is {{went}} and the past participle is {{gone}}.
""",

    "09_numerical_exact": """---
title: "Sample 09 - Numerical (Exact)"
---

## Cantons in Switzerland

Hint: Total count of full and half cantons.
Feedback: Switzerland consists of 26 cantons (20 full and 6 half cantons).

How many cantons are there in Switzerland?
= 26
""",

    "10_numerical_range": """---
title: "Sample 10 - Numerical (With Tolerance)"
---

## Earth Surface Gravity

Hint: Standard acceleration due to gravity in m/s^2.
Feedback: Standard gravity is approximately 9.81 m/s^2.

What is the acceleration due to gravity on Earth in m/s^2?
= 9.81 ± 0.05
""",

    "11_order": """---
title: "Sample 11 - Order / Sequencing"
---

## Natural Language Processing Pipeline

Hint: Raw text must first be split before syntax analysis.
Feedback: Tokenization precedes parsing, which precedes semantic evaluation.

Put the NLP processing stages in the correct order:
1. [ ] Tokenization
1. [ ] Syntactic Parsing
1. [ ] Semantic Evaluation
""",

    "12_essay": """---
title: "Sample 12 - Essay / Free Text"
---

## Cellular Respiration

Hint: Contrast aerobic (with oxygen) and anaerobic (without oxygen).
Feedback: Aerobic respiration uses oxygen to produce up to ~38 ATP per glucose, while anaerobic respiration occurs without oxygen producing significantly less ATP.

Explain the difference between aerobic and anaerobic respiration in 2-3 sentences.
""",
}

# Also create a comprehensive combined quiz containing all types
ALL_COMBINED_MD = """---
title: "Sample 13 - All Question Types Combined"
---

# Section 1: Choice & Statements

## Capital of Switzerland
Hint: De facto federal city.
Feedback: Bern is the federal city.
- [ ] Zurich
- [ ] Geneva
- [X] Bern
- [ ] Basel

## Official Languages
Hint: Four national language regions.
Feedback: German, French, Italian, and Romansh.
- [x] German
- [x] French
- [x] Italian
- [ ] English

## Mammal Characteristics
Hint: Monotremes and body temperature.
Feedback: Monotremes lay eggs; mammals are endothermic.
- [+] They possess hair or fur.
- [+] Females produce milk.
- [-] All mammals give birth to live young.
- [-] Mammals are ectothermic.

## Leap Year
Hint: 365.25 days.
Feedback: Earth orbits in ~365.25 days.
- [X] True
- [ ] False

# Section 2: Input & Order

## American Spelling
Hint: Gray vs grey.
Feedback: American English uses gray.
The American spelling is {{gray | grey}}.

## Gravity
Hint: Standard acceleration in m/s^2.
Feedback: Standard gravity is 9.81 m/s^2.
What is gravity in m/s^2?
= 9.81 ± 0.05

## NLP Pipeline
Hint: Tokenization first.
Feedback: Tokenize, parse, evaluate.
Order the steps:
1. [ ] Tokenization
1. [ ] Syntactic Parsing
1. [ ] Semantic Evaluation

## Essay on Respiration
Hint: Aerobic vs anaerobic.
Feedback: Look for oxygen requirement and ATP yield differences.
Explain the difference between aerobic and anaerobic respiration.
"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_samples = dict(SAMPLES)
    all_samples["13_all_types_combined"] = ALL_COMBINED_MD

    for name, md_text in all_samples.items():
        # 1. Save Markdown source
        md_path = OUTPUT_DIR / f"{name}.md"
        md_path.write_text(md_text, encoding="utf-8")

        # 2. Parse QuizMD
        quiz, diagnostics = parse_quizmd(md_text)
        fatal_errors = [d for d in diagnostics if d.severity.name == "ERROR"]
        if fatal_errors:
            print(f"ERROR parsing {name}: {fatal_errors}")
            continue

        # 3. Create QTI package
        zip_path = OUTPUT_DIR / f"{name}_qti21.zip"
        create_qti_package(quiz, str(zip_path))
        print(f"Generated: {zip_path.name} ({zip_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
