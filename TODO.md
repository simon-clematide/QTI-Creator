# Future Feature Roadmap & TODOs

## Planned Features

- [ ] **Custom Hint Title (`Hint-Title:`)**:
  - OpenOLAT supports a `title="..."` attribute on `<endAttemptInteraction responseIdentifier="HINTREQUEST" title="..."/>` and `<modalFeedback outcomeIdentifier="HINTFEEDBACKMODAL" identifier="HINT" title="...">`.
  - Introduce an optional structured question-level keyword `Hint-Title: <text>` (and/or YAML frontmatter / quiz default `hint_title: <text>`).
  - When specified, use this custom title on the interactive button and modal dialog; otherwise, omit the `title` attribute or fall back to default behavior.
