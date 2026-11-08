"""Shared user guidance for authoring, checking, and packaging quizzes."""

SINGLE_SECTION_EXAMPLE = """---
title: Biology Practice
---
# Cells
Read each question carefully.

## Which structure contains most human DNA?
- [X] The nucleus
- [ ] The cell membrane

### Hint
Think about where chromosomes are located.

### Feedback
Most human DNA is in the nucleus; mitochondria also contain DNA.
"""

MULTI_SECTION_EXAMPLE = """---
title: Biology Practice
---
# Cells
## Which structure contains most human DNA?
- [X] The nucleus
- [ ] The cell membrane

# Genetics
## Complete the abbreviation.
DNA stands for {{deoxyribonucleic acid}}.
"""

AUTHORING_WORKFLOW = """
1. **Write or load QuizMD.** Open the Editor and paste your source or use **Upload source**. On Home, select an example and load it into the Editor. AI drafting is optional; see the [Prompting Guide](/prompting).
2. **Inspect and correct.** Check the validation status and expand the Preview question cards to inspect the inferred types, answer keys, points, hints, and feedback. Use **Refresh** if the preview needs updating.
3. **Prepare images if needed.** In [Media](/media), upload a ZIP whose paths match your image references. Enable **Include media in exported QTI package** for a self-contained package. See the media instructions for remote images and hotspots.
4. **Generate and download.** Click **Generate package**, then **Download ZIP**. After changing the source or media settings, use **Regenerate** and download the new ZIP.
5. **Keep your editable source.** Copy the QuizMD into a local `.md` file and retain the original media ZIP. The generated QTI ZIP does not contain your QuizMD source. The browser session is a temporary workspace, not permanent storage.
6. **Check the learner experience.** Follow [OpenOLAT Import](/openolat), preview the imported test as a learner, and verify scoring and media before publishing.
"""

VALIDATION_GUIDE = """
### What “Valid” establishes
The current source passes QTI-Creator's syntax and content checks, plus the media checks applicable to your settings. It does **not** establish factual accuracy, good assessment design, or successful rendering in your OpenOLAT installation. Package generation is not a full OpenOLAT runtime test.

- **Errors** must be fixed before export. Read the message and use a line link, when provided, to locate the problem.
- **Warnings** need review but do not necessarily prevent export. For example, check whether an image is intentionally external or whether answer length gives away the solution.
- **Preview** is an author view showing solutions and editing controls, not the exact learner interface. Inspect the imported test in OpenOLAT too.
- **Package outdated** means the source or media state has changed since generation. Regenerate and download a fresh ZIP; a previously downloaded ZIP stays unchanged.

### Random, Shortest, and Longest
These are answer-selection heuristics, **not measured student difficulty**. Random estimates a guessing baseline; Shortest and Longest estimate scores from favoring the shortest or longest answer text. A warning means a length-based strategy beats the random baseline, so inspect the affected wording rather than mechanically changing every answer's length.

The headline percentages are weighted by question points over the included question types. Essay, text-entry, numerical, and image-hotspot questions are skipped; the scored/skipped count shows the coverage. “Skipped” here means excluded from this estimate, not omitted from the exported test. Ties and scoring rules affect the estimates.
"""

MEDIA_GUIDE = """
### Match ZIP paths to QuizMD paths
For `![Chart](images/chart.png)`, put `images/chart.png` inside the ZIP, with `images/` at the ZIP root. Do not add an extra enclosing folder. Preserve spelling and letter case.

```text
media.zip
└── images/
    └── chart.png
```

Upload this archive with **Upload media ZIP**. Uploading a ZIP replaces the current media archive and enables export inclusion. Check the file list for referenced, unused, and missing files.

- **Resolve relative media in preview** displays uploaded local images in the author preview. It does not package them for export.
- **Include media in exported QTI package** copies referenced local images into the package and downloads supported remote images. Remote URLs must be reachable by the server; a remote-only quiz needs no ZIP upload.
- With inclusion off, external URLs and relative references remain links. A relative path alone does not carry the image into OpenOLAT; package local images for a portable test.
- **Hotspots require inclusion on** and a resolvable background image, either from your ZIP or a remote URL. Coordinates are resolved against the real image dimensions.

For a ready-to-use local-image example, select **Hotspot Image Questions (with Media)** on [Home](/). Loading it supplies both questions and the matching media ZIP. Expand a hotspot card in the Editor and use **Edit Hotspots** to inspect and adjust its regions. You can also download the example media ZIP from Home.
"""
