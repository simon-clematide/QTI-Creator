"""Sample QuizMD documents for the user interface."""

SAMPLE_ALL_TYPES = """# General Knowledge & Science Quiz

A demonstration quiz covering all supported question types with automatic inference.

## What is the capital of France?
- [ ] Berlin
- [X] Paris
- [ ] Rome
- [ ] Madrid

## The Earth completes one full orbit around the Sun in approximately 365.25 days.
- [X] True
- [ ] False

## Which of the following numbers are prime?
- [x] 2
- [x] 3
- [ ] 4
- [x] 5
- [ ] 6

## Characteristics of Mammals
- [+] They possess hair or fur.
- [+] Females produce milk to nourish their young.
- [-] All mammals give birth to live young without exception.
- [-] Mammals are ectothermic organisms.

## Irregular Verb Forms
The past tense of *go* is {{went}} and the past participle is {{gone}}.
The American spelling of the colour between black and white is {{gray | grey}}.

## European Capitals
Switzerland has its federal city in {[Bern|Zurich|Geneva]}, while the capital of Germany is {[Munich|**Berlin**|Hamburg]}.

## Parts of Speech
Select all nouns in the following sentence:
The {** cat **} { sat } on the {** mat **} near the {** fireplace **}.

## Gravitational Acceleration
What is the acceleration due to gravity on Earth's surface in m/s²?
= 9.81 ± 0.05

## Order the stages of a machine learning workflow.
1. [ ] Data collection
1. [ ] Feature engineering
1. [ ] Model training
1. [ ] Evaluation

## Match Words by Part of Speech
Match each word with its corresponding grammatical category:

| Item | Match |
|---|---|
| dog | noun |
| cat | noun |
| run | verb |
| quickly | adverb |

## Drag and Drop Elements by Group
Drag each chemical element into its correct group:

| Item | Drag |
|---|---|
| Helium | Noble gas |
| Neon | Noble gas |
| Sodium | Alkali metal |
| Potassium | Alkali metal |

## Cellular Respiration
Explain the difference between aerobic and anaerobic respiration in 2-3 sentences.

"""

SAMPLE_LINGUISTICS = """---
title: Introduction to Linguistics Quiz
version: 1.1.0
language: en
---

## Which language family does English belong to?
- [ ] Romance
- [X] Germanic
- [ ] Slavic
- [ ] Uralic

## English has grammatical gender comparable to German.
- [ ] True
- [X] False

## The smallest contrastive sound unit in a language is a {{phoneme}}.

## Briefly explain what a minimal pair is.
Provide at least one clear example.
"""

SAMPLE_STEM = """# Physics & Chemistry Quiz
Version: 2.0.0
Language: en

## Which particles are found inside the nucleus of an atom?
- [x] Protons
- [x] Neutrons
- [ ] Electrons
- [ ] Photons

## What is the speed of light in vacuum (in units of 10^8 m/s)?
= 2.998 ± 0.01

## Newton's Third Law
For every action, there is an {{equal}} and {{opposite}} reaction.

## Thermodynamics
State the Second Law of Thermodynamics and explain the concept of entropy.
Points: 4
"""

SAMPLE_CS = r"""# Computer Science & Python Quiz
Version: 1.0.0
Language: en

## Python List Operations
What does the following snippet evaluate to?
```python
numbers = [10, 20, 30, 40]
numbers.append(50)
print(len(numbers))
```
- [ ] `4`
- [X] `5`
- [ ] `50`
- [ ] `Error`

## Boolean Logic in Python
What is the return value of `bool([])` in Python?
- [ ] True
- [X] False

## Recursion
In recursive algorithms, the condition that terminates the recursive calls is called the {{base case}}.

## Hash Table Complexity
What is the average time complexity of looking up a key in a hash table (or Python `dict`)?
- [X] $O(1)$
- [ ] $O(n)$
- [ ] $O(\log n)$
- [ ] $O(n^2)$
"""

SAMPLE_MATH = r"""---
title: Mathematics & LaTeX Typesetting Test
version: 1.2.0
language: en
---
A comprehensive test suite covering diverse mathematical typesetting: inline equations, display math, integrals, limits, summations, matrices, and piecewise functions across multiple question types.

## Calculus: Integration by Parts
Evaluate the indefinite integral:
$$\int x e^x \, dx$$
- [ ] $(x + 1)e^x + C$
- [X] $(x - 1)e^x + C$
- [ ] $x^2 e^x + C$
- [ ] $\frac{1}{2} x^2 e^x + C$
Feedback: Using integration by parts $\int u \, dv = uv - \int v \, du$ with $u = x$ and $dv = e^x dx$.

## Linear Algebra: Matrix Determinants
Which of the following $2 \times 2$ matrices have determinant $\det(M) = 1$?
$$\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc$$
- [x] $\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}$
- [x] $\begin{pmatrix} 2 & 1 \\ 1 & 1 \end{pmatrix}$
- [ ] $\begin{pmatrix} 1 & 1 \\ 1 & 1 \end{pmatrix}$
- [x] $\begin{pmatrix} 0 & -1 \\ 1 & 0 \end{pmatrix}$

## Euler's Identity
The equation $e^{i\pi} + 1 = 0$ connects the fundamental constants $e$, $i$, $\pi$, $1$, and $0$.
- [X] True
- [ ] False

## Limits and Derivatives
The fundamental limit $\lim_{x \to 0} \frac{\sin x}{x} =$ {{1}}, and the derivative $\frac{d}{dx}\cos(x) =$ {{- \sin(x)}}.

## Projectile Motion: Maximum Height
A projectile launched at angle $\theta = 30^\circ$ with velocity $v_0 = 20\text{ m/s}$ has maximum height:
$$h = \frac{v_0^2 \sin^2(\theta)}{2g}$$
Given $g = 9.81\text{ m/s}^2$, calculate $h$ in meters:
= 5.10 ± 0.15

## Real Analysis & Logic Statements
Points: 2
Evaluate the validity of each statement for real numbers $x, a, b \in \mathbb{R}$:
- [+] $\forall x \in \mathbb{R},\; x^2 \ge 0$
- [+] $\sqrt{a \cdot b} = \sqrt{a} \cdot \sqrt{b}$ for all $a, b \ge 0$
- [-] $\forall x \in \mathbb{R},\; \sqrt{x^2} = x$
- [-] $\frac{1}{x} < 1 \implies x > 1$ for all $x \ne 0$

## Completing the Square
Derive the quadratic formula by completing the square for $ax^2 + bx + c = 0$ where $a \ne 0$.
State each algebraic step clearly.
Points: 4
"""

SAMPLE_CONFIG_SHOWCASE = r"""---
title: Advanced Configuration & Metadata Showcase
version: 2.1.0
language: de
topic: Computer Science
keywords: [algorithms, data-structures, python]
shuffle: yes
additional_info: Final Exam - Section A
description: |
  Demonstrating all global and question-level configuration options in QuizMD:
  YAML frontmatter, metadata inheritance, local overrides, custom point weights,
  post-submission feedback, custom QTI identifiers, and shuffling toggles.
---

## Linear Search Time Complexity
Points: 2
Shuffle: no
Topic: Search Algorithms
Keywords: search, linear, complexity
Additional_Info: Source: Knuth TAOCP Vol 3
Hint: Think about how many comparisons are made if the target element is at the very end of the list.
Feedback: Linear search scans sequentially through $n$ elements, resulting in $O(n)$ worst-case time complexity.
- [ ] $O(1)$
- [X] $O(n)$
- [ ] $O(n \log n)$
- [ ] $O(n^2)$

## Which data structures are non-linear?
Points: 3
- [x] Tree
- [x] Graph
- [ ] Array
- [ ] Linked list
Feedback: Trees and graphs are non-linear hierarchical or networked structures.

## An empty Python list evaluates to True in a boolean context.
Points: 0.5
Feedback: In Python, empty collections (lists, tuples, dicts, sets) evaluate to False.
- [ ] True
- [X] False

## Complexity Hierarchy
Points: 2.5
Feedback: Arrange from slowest growing (fastest execution) to fastest growing.
1. [ ] Constant: $O(1)$
1. [ ] Logarithmic: $O(\log n)$
1. [ ] Linear: $O(n)$
1. [ ] Quadratic: $O(n^2)$

## String Formatting Syntax
Points: 2
Feedback: Both 'upper' and 'str.upper' or 'uppercase' are accepted synonyms.
In Python, to convert a string to uppercase one calls the {{upper | uppercase | str.upper}} method, while {{lower | lowercase}} converts to lowercase.

## Floating Point Tolerance
Points: 2
Feedback: Exact answer is 0.125 with an allowable tolerance band of ±0.001.
What is the decimal value of $2^{-3}$?
= 0.125 +- 0.001

## Binary Search Trees
Points: 4
Topic: Tree Data Structures
Keywords: bst, trees, invariant
Evaluate each statement regarding Binary Search Trees:
- [+] The left subtree contains only nodes with keys less than the node's key.
- [+] The right subtree contains only nodes with keys greater than the node's key.
- [-] An in-order traversal of a BST yields elements in descending order.
- [-] Lookup in any binary search tree is guaranteed to be $O(\log n)$ in the worst case.
Feedback: In-order traversal yields ascending order. Unbalanced trees degrade to $O(n)$.

## Explain Amortized Complexity
Points: 5
Topic: Complexity Theory
Keywords: amortized, analysis, array
Identifier: amortized_analysis_q08
Provide a detailed explanation of amortized time complexity.
Discuss how dynamic array resizing achieves $O(1)$ amortized insertion despite $O(n)$ worst-case copy steps.
"""

SAMPLE_MEDIA = r"""---
title: Astronomy & Science Image Quiz
version: 1.0.0
language: en
topic: Astronomy & History of Science
keywords: [astronomy, science, images, space]
shuffle: yes
---
A multimedia quiz demonstrating remote image embedding from Wikimedia Commons. Images render directly in preview and can be packaged as self-contained assets in OpenOLAT.

## Mars Exploration
![Mars in true color](https://upload.wikimedia.org/wikipedia/commons/0/02/OSIRIS_Mars_true_color.jpg)
The image above shows the "Red Planet". What chemical compound is primarily responsible for its reddish surface appearance?
- [ ] Copper oxide
- [X] Iron(III) oxide (rust)
- [ ] Silicon dioxide
- [ ] Titanium dioxide
Feedback: Iron(III) oxide (rust) in the Martian regolith gives the surface its distinctive reddish hue.

## Hubble Space Telescope
Points: 2
![Hubble Space Telescope during Servicing Mission 4](https://upload.wikimedia.org/wikipedia/commons/3/3f/HST-SM4.jpeg)
Which statements regarding the Hubble Space Telescope are correct?
- [x] It was designed to be serviced in orbit by Space Shuttle astronauts.
- [x] It operates in low Earth orbit outside the distorting effects of the atmosphere.
- [ ] It observes exclusively in the microwave and radio wavelengths.
- [x] It has provided deep-field observations revealing thousands of early galaxies.
Feedback: Hubble observes in ultraviolet, visible, and near-infrared wavelengths (not radio/microwaves).

## DNA Pioneer
Points: 1.5
![Historical portrait](https://upload.wikimedia.org/wikipedia/commons/9/97/Rosalind_Franklin.jpg)
This scientist's Photo 51 was critical to discovering the double-helix structure of DNA. Who is she?
- [ ] Marie Curie
- [ ] Ada Lovelace
- [X] Rosalind Franklin
- [ ] Lise Meitner
Feedback: Rosalind Franklin's X-ray diffraction images of DNA, particularly Photo 51, enabled Watson and Crick to determine the double-helix structure.

## European Union Geography
![Map of Europe](https://upload.wikimedia.org/wikipedia/commons/f/f0/European_Union_map.png)
The member states of the European Union are highlighted on the map.
The administrative headquarters and principal seat of the European Commission is located in {{Brussels}}.
Feedback: Brussels, Belgium serves as the de facto capital of the European Union.
"""

SAMPLE_MULTI_SECTION = """---
title: Comprehensive Computer Science Exam
version: 2.0.0
language: en
shuffle: yes
topic: Computer Science
---

# Section 1: Algorithms & Data Structures
This section assesses asymptotic complexity, binary search, and elementary data structures. Calculators are not permitted.

## Binary Search Complexity
What is the worst-case time complexity of binary search on a sorted array of $n$ elements?
- [ ] $O(1)$
- [X] $O(\\log n)$
- [ ] $O(n)$
- [ ] $O(n \\log n)$
Feedback: Binary search halves the search interval at each step, taking logarithmic time.

## Binary Search Tree Invariants
Points: 2
- [+] The left subtree contains keys strictly less than the node's key.
- [+] The right subtree contains keys strictly greater than the node's key.
- [-] An in-order traversal of a BST yields values in descending order.
- [-] Any binary search tree guarantees $O(\\log n)$ lookup regardless of insertion order.
Feedback: In-order traversal yields ascending order. Unbalanced trees can degrade to $O(n)$.

# Section 2: Systems & Networking
Questions in this section cover memory hierarchies, process management, and protocols.

## Memory Hierarchy
Points: 2
Arrange storage media from fastest access speed to slowest:
1. [ ] CPU Registers
1. [ ] L1 / L2 Cache
1. [ ] Main Memory (RAM)
1. [ ] Solid State Drive (SSD)

## Transport Layer Protocols
Which protocol provides connection-oriented, reliable byte-stream transmission?
- [X] TCP
- [ ] UDP
- [ ] IP
- [ ] ICMP
Feedback: TCP provides connection setup, retransmission, and flow control.
"""

EXAMPLES = {
    "All Question Types (Showcase)": SAMPLE_ALL_TYPES,
    "Multi-Section Exam (Sections & Rubrics)": SAMPLE_MULTI_SECTION,
    "Full Configuration & Metadata Showcase": SAMPLE_CONFIG_SHOWCASE,
    "Astronomy & Science (Images Showcase)": SAMPLE_MEDIA,
    "Mathematics & LaTeX Typesetting": SAMPLE_MATH,
    "Computer Science & Python (Code Snippets)": SAMPLE_CS,
    "STEM & Physics Quiz": SAMPLE_STEM,
    "Linguistics Quiz": SAMPLE_LINGUISTICS,
}



