"""PDF structural calculation book."""

from dataclasses import dataclass
import os
from typing import Tuple

from stb_reports.calc_book import chapters_general as general
from stb_reports.calc_book import chapters_results as results
from stb_reports.calc_book import figures
from stb_reports.calc_book.context import ReportContext, build_context
from stb_reports.calc_book.document import CalcDocument, CoverField
from stb_reports.calc_book.render_pdf import render_pdf


@dataclass(frozen=True)
class CalcBook:
    output_path: str
    page_count: int
    warnings: Tuple[str, ...]


def build_document(ctx: ReportContext) -> CalcDocument:
    b = ctx.project.building
    program = "Structural Toolbox  Ver." + (ctx.program_version or "-")
    blocks = []
    blocks.extend(general.chapter_general(ctx, figures))
    blocks.extend(general.chapter_policy(ctx))
    blocks.extend(general.chapter_program(ctx))
    blocks.extend(general.chapter_loads(ctx))
    blocks.extend(general.chapter_preparation(ctx))
    blocks.extend(results.chapter_analysis(ctx))
    blocks.extend(results.chapter_checks(ctx))
    blocks.extend(results.chapters_indices(ctx))
    blocks.extend(results.chapter_foundation(ctx))
    blocks.extend(results.chapter_findings(ctx))
    blocks.extend(results.chapter_echo(ctx))
    return CalcDocument(
        title=ctx.project.report.title or "構造計算書",
        project_name=b.name or "-",
        program=program,
        generated_at=ctx.generated_at.strftime("%Y/%m/%d %H:%M:%S"),
        input_id=ctx.input_id,
        designer=b.designer.name,
        cover_fields=(
            CoverField("プログラムの名称", "Structural Toolbox Ver." + (ctx.program_version or "-")),
            CoverField("設計者", b.designer.name or ""),
            CoverField("資格", b.designer.qualification or ""),
            CoverField("登録番号", b.designer.license_number or ""),
            CoverField("連絡先", b.designer.contact or ""),
        ),
        blocks=tuple(blocks),
    )


def write_calc_book_pdf(output_path, mdl, project, generated_at=None, program_version="") -> CalcBook:
    """Write the book for an already solved model."""

    ctx = build_context(mdl, project, generated_at=generated_at, program_version=program_version)
    pages = render_pdf(build_document(ctx), output_path)
    pages += append_attachments(output_path, attachment_paths(project))
    return CalcBook(output_path=str(output_path), page_count=pages, warnings=ctx.warnings)


def attachment_paths(project):
    """report.attachments, with relative paths taken from the project file's folder."""

    base = os.path.dirname(os.path.abspath(project.source_path)) if project.source_path else os.getcwd()
    return [os.path.join(base, item) if not os.path.isabs(item) else item for item in project.report.attachments]


def append_attachments(output_path, paths) -> int:
    """Append PDF files after the book, each with a bookmark; return the pages added."""

    if not paths:
        return 0
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        raise ValueError("添付PDFが見つかりません: " + ", ".join(missing))

    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter(clone_from=str(output_path))
    added = 0
    parent = writer.add_outline_item("添付資料", len(writer.pages))
    for path in paths:
        reader = PdfReader(path)
        writer.add_outline_item(os.path.basename(path), len(writer.pages), parent=parent)
        for page in reader.pages:
            writer.add_page(page)
            added += 1
    with open(output_path, "wb") as fh:
        writer.write(fh)
    return added
