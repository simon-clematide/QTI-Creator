"""Theme definition for QTI-Creator."""

import gradio as gr

THEME = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="blue",
    font=[
        gr.themes.GoogleFont("Source Sans 3"),
        "Source Sans Pro",
        "Arial",
        "sans-serif",
    ],
).set(
    block_label_background_fill="transparent",
    block_label_background_fill_dark="transparent",
    block_label_border_width="0px",
    block_label_border_width_dark="0px",
    block_label_shadow="none",
    block_label_text_color="#0f172a",
    block_label_text_size="1.05rem",
    block_label_text_weight="600",
    block_label_padding="0px 0px 4px 0px",
    block_label_margin="0px",
    section_header_text_size="1.05rem",
    section_header_text_weight="600",
)
