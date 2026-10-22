"""Comment templates for Structural Toolbox input file formats."""

from stb_gui.dat_format_headers import SECTION_HEADERS, new_model_template

NEW_MODEL_TEMPLATE = new_model_template()
NEW_MODEL_TEMPLATE_SIMPLE = new_model_template("simple")

EJNT_EDITOR_HEADER = (
    "\n".join(SECTION_HEADERS["EJNT"])
    + "\n# Delete a line to remove EJNT (rigid joint).\n\n"
)
