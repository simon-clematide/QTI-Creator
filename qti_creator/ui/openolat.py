"""Import and learner-preview guidance for OpenOLAT."""

import gradio as gr

OPENOLAT_MARKDOWN = """
## OpenOLAT Import

QTI-Creator exports an **IMS QTI 2.1 test ZIP**. Download it with **Generate package → Download ZIP** in the [Editor](/editor). After edits, regenerate and download the new ZIP. Upload the ZIP as it is; do not unpack or repackage it.

### Choose Test or Self-test first

| Your goal | Course element |
|---|---|
| Practice with anonymous results and unlimited attempts | **Self-test** |
| Teacher feedback, individually recorded results, or manually graded essays | **Test** |
| Graded examination with controlled attempts | **Test**, with the appropriate course settings |

A Test can be formative as well as summative. Self-test results are anonymous: teachers cannot identify individual learners' responses, and only automatically scorable questions contribute points. Use Test when essays need teacher assessment.

### Import, preview, then publish

1. Open your OpenOLAT course and choose **Administration → Course editor**. You need course-editor rights.
2. Add a **Test** or **Self-test** course element and open **Test configuration**.
3. Use the available **Import** action to upload the QTI-Creator ZIP, and name the imported Test learning resource. Depending on your OpenOLAT version, selection and import may be combined under **Select, replace or import test**.
4. Configure attempts, correction, and result visibility. For essays, choose an appropriate manual-correction option in a Test element.
5. **Preview before publishing.** Check the learner experience using the checklist below. The QTI-Creator Preview is an author view, not a replica of OpenOLAT.
6. Publish the course element when the checks pass, and confirm that intended participants can access it.

See [OpenOLAT's Test course element](https://docs.openolat.org/manual_user/learningresources/Course_Element_Test/) and [Test/Self-test configuration](https://docs.openolat.org/manual_user/learningresources/Tests_at_course_level/). Labels and available options vary with the installed version and your permissions.
"""

LEARNER_CHECKLIST = """
### Learner-preview checklist

- Check section instructions, question order, images, formulas, and code.
- Try correct, incorrect, and partially correct responses; inspect scores and total points.
- Confirm that answer scrambling behaves as intended.
- Open hints and check when feedback and solutions become visible. Their availability also depends on OpenOLAT's test and course settings.
- Verify attempts, submission behavior, result visibility, and manual correction for essays.

If you change QuizMD or media after checking, regenerate the package and repeat the relevant checks after import. Replacing a test already used by learners can affect attempts and assessments; follow [OpenOLAT's replacement guidance](https://docs.openolat.org/manual_user/learningresources/Course_Element_Test/#changes-to-tests-and-self-tests).
"""


def render_openolat_page() -> None:
    with gr.Column(elem_classes=["docs-content"]):
        gr.Markdown(OPENOLAT_MARKDOWN)
        with gr.Accordion("Learner-preview checklist", open=True):
            gr.Markdown(LEARNER_CHECKLIST)
        with gr.Accordion("Alternative: Import into Authoring area", open=False):
            gr.Markdown("""
                Use this route to inspect and manage a reusable complete test before assigning it to a course.

                1. Open **Authoring** and choose **Import** / **Import file** (labels depend on your installation).
                2. Upload the generated ZIP. OpenOLAT creates a **Test learning resource**.
                3. Open and preview it, and configure its settings.
                4. In a course's Test or Self-test element, use **Test configuration** to select this existing resource.
                5. Check the course-level options and learner preview before publishing.

                See [Creating and importing learning resources](https://docs.openolat.org/manual_user/learningresources/Creating_learning_resources/).
            """)
        with gr.Accordion("Alternative: Import questions into Question Bank", open=False):
            gr.Markdown("""
                Use this route for individual reusable questions rather than a complete course test.

                1. Open **Question Bank → My questions** (or the corresponding question list).
                2. Open **Import** and choose the option to upload a **ZIP file from the local computer**.
                3. Upload the generated QTI 2.1 ZIP and complete the import wizard.
                4. Inspect the imported questions before organizing them into pools or lists or building other tests.

                You can also import questions from a Test learning resource in the Authoring area when you have permission to copy it. Question Bank access and actions depend on your role.

                See [Import questions into the Question Bank](https://docs.openolat.org/manual_user/area_modules/Question_Bank_Import_Questions/).
            """)
        with gr.Accordion("Test resource, course element, or Question Bank?", open=False):
            gr.Markdown("""
                The **Test learning resource** contains the reusable test. A **Test / Self-test course element** assigns such a resource to a course and controls how participants encounter it. Importing through a course element also creates a learning resource; these are connected objects, not separate export formats.

                The **Question Bank** instead stores individual questions for reuse. Importing questions there does not by itself publish a course test.
            """)
        with gr.Accordion("Troubleshooting imports", open=False):
            gr.Markdown("""
                ### OpenOLAT rejects the ZIP
                Check QTI-Creator's validation status and diagnostics. Fix errors, regenerate, and download the fresh ZIP. Import the generated archive directly with `imsmanifest.xml` at its root. If it still fails, retain the exact OpenOLAT error and check compatibility with your installation; a green authoring status is not an OpenOLAT runtime guarantee.

                ### An image is missing
                For local images, upload a media ZIP with paths matching QuizMD and enable **Include media in exported QTI package**. For remote images, inclusion downloads them; external URLs otherwise depend on continued network access. Regenerate and reimport after correcting media.

                ### Hints, feedback, or scores differ from the author preview
                Check the learning resource and course-element settings, including result/solution visibility, correction, and attempts. For essays requiring teacher assessment, use Test and manual correction. See [Tests at course level](https://docs.openolat.org/manual_user/learningresources/Tests_at_course_level/).

                ### Learners cannot access the test
                Check publication, participant access, release dates, and the element's visibility or learning-path configuration.
            """)
