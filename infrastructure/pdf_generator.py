"""
PDF Generator - Exportação da análise para PDF usando ReportLab.
Gera todos os visuais empilhados (gráficos, tabelas, métricas) com filtros aplicados.
"""

from typing import List, Dict, Any, Optional
import os
import io
import html
from datetime import datetime

from domain.entities import Analysis, Visualization, VisualizationType
from domain.value_objects import ExportOptions


class PDFGenerator:
    def __init__(self, output_dir: str = "download"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ── Font helpers ──────────────────────────────────────────────────────────

    def _register_fonts(self):
        """
        Registra fonte TTF para suporte a acentos/Unicode.
        Tenta caminhos comuns em Linux (Streamlit Cloud) e Windows.
        Retorna (nome_regular, nome_bold).
        """
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # matplotlib é garantido no requirements.txt e já inclui DejaVu Sans
        candidates = []
        try:
            import matplotlib as _mpl
            _mpl_ttf = os.path.join(
                os.path.dirname(_mpl.__file__), "mpl-data", "fonts", "ttf"
            )
            candidates += [
                (os.path.join(_mpl_ttf, "DejaVuSans.ttf"),
                 os.path.join(_mpl_ttf, "DejaVuSans-Bold.ttf")),
            ]
        except Exception:
            pass
        candidates += [
            # DejaVu — presente na maioria dos containers Linux
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ("/usr/share/fonts/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
            # Liberation Sans
            ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
            ("/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
             "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"),
            # Ubuntu Font
            ("/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
             "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"),
            # Noto Sans
            ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
             "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
            # Windows
            ("C:/Windows/Fonts/arial.ttf",   "C:/Windows/Fonts/arialbd.ttf"),
            ("C:/Windows/Fonts/Arial.ttf",   "C:/Windows/Fonts/ArialBd.ttf"),
            # macOS
            ("/Library/Fonts/Arial.ttf",     "/Library/Fonts/Arial Bold.ttf"),
        ]

        for reg_path, bold_path in candidates:
            if not reg_path or not os.path.exists(reg_path):
                continue
            try:
                pdfmetrics.registerFont(TTFont("PDFRegular", reg_path))
                if bold_path and os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("PDFBold", bold_path))
                    return "PDFRegular", "PDFBold"
                return "PDFRegular", "PDFRegular"
            except Exception:
                continue

        return "Helvetica", "Helvetica-Bold"

    @staticmethod
    def _t(text: str) -> str:
        """Escapa texto para uso seguro em Paragraph (evita quebra por & < >)."""
        return html.escape(str(text or ""))

    # ── Geração principal ─────────────────────────────────────────────────────

    def generate_pdf(
        self,
        analysis: Analysis,
        options: ExportOptions,
        chart_images: Optional[Dict[str, bytes]] = None,
        table_data: Optional[Dict[str, Dict]] = None,
        metric_data: Optional[Dict[str, Dict]] = None,
    ) -> str:
        from reportlab.lib.pagesizes import A4, letter, legal
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        chart_images = chart_images or {}
        table_data = table_data or {}
        metric_data = metric_data or {}

        font_reg, font_bold = self._register_fonts()

        page_sizes = {"a4": A4, "letter": letter, "legal": legal}
        page_size = page_sizes.get(options.paper_size, A4)
        if options.orientation == "landscape":
            page_size = (page_size[1], page_size[0])

        base_name = (options.file_name or analysis.name).strip()
        safe_base = "".join(c if c.isalnum() or c in " _-" else "_" for c in base_name)
        output_filename = f"{safe_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(self.output_dir, output_filename)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=options.margin_mm * mm,
            leftMargin=options.margin_mm * mm,
            topMargin=options.margin_mm * mm,
            bottomMargin=options.margin_mm * mm,
        )

        styles = getSampleStyleSheet()
        usable_w = page_size[0] - 2 * options.margin_mm * mm

        # ── Estilos ───────────────────────────────────────────────────────────
        style_cover_title = ParagraphStyle(
            "CoverTitle",
            parent=styles["Normal"],
            fontSize=26,
            leading=32,
            alignment=TA_CENTER,
            textColor=colors.white,
            fontName=font_bold,
        )
        style_cover_sub = ParagraphStyle(
            "CoverSub",
            parent=styles["Normal"],
            fontSize=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#CBD5E1"),
            fontName=font_reg,
        )
        style_subtitle = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=8,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#64748B"),
            fontName=font_reg,
        )
        style_slide = ParagraphStyle(
            "SlideTitle",
            parent=styles["Normal"],
            fontSize=14,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#1E293B"),
            fontName=font_bold,
        )
        style_viz_title = ParagraphStyle(
            "VizTitle",
            parent=styles["Normal"],
            fontSize=11,
            spaceBefore=12,
            spaceAfter=5,
            textColor=colors.HexColor("#334155"),
            fontName=font_bold,
        )
        style_caption = ParagraphStyle(
            "Caption",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#94A3B8"),
            alignment=TA_CENTER,
            fontName=font_reg,
            spaceAfter=8,
        )
        style_comment = ParagraphStyle(
            "Comment",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#64748B"),
            fontName=font_reg,
            leftIndent=12,
            spaceAfter=8,
        )
        style_metric_label = ParagraphStyle(
            "MetricLabel",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#64748B"),
            alignment=TA_CENTER,
            fontName=font_reg,
            spaceAfter=4,
        )
        style_metric_value = ParagraphStyle(
            "MetricValue",
            parent=styles["Normal"],
            fontSize=28,
            textColor=colors.HexColor("#1E293B"),
            alignment=TA_CENTER,
            fontName=font_bold,
            spaceAfter=16,
        )

        story = []

        # ── Capa ─────────────────────────────────────────────────────────────
        cover_title = (options.file_name or analysis.name).strip()
        total_vizs = sum(
            1 for s in analysis.slides
            for v in s.visualizations
            if v.config and v.config.visualization_type != VisualizationType.MEASURES
        )

        # Faixa escura com título em branco (suporte a acentos via TTF)
        cover_rows = [
            [Spacer(1, 10 * mm)],
            [Paragraph(self._t(cover_title), style_cover_title)],
        ]
        if options.subtitle:
            cover_rows.append([Spacer(1, 4 * mm)])
            cover_rows.append([Paragraph(self._t(options.subtitle), style_cover_sub)])
        cover_rows.append([Spacer(1, 10 * mm)])

        cover_table = Table(cover_rows, colWidths=[usable_w])
        cover_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#1E293B")),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 24),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 24),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("ROUNDEDCORNERS", [6]),
        ]))

        story.append(Spacer(1, 14 * mm))
        story.append(cover_table)
        story.append(Spacer(1, 6 * mm))
        story.append(
            Paragraph(
                self._t(f"Exportado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"),
                style_subtitle,
            )
        )
        story.append(
            Paragraph(
                self._t(f"{len(analysis.slides)} slide(s) · {total_vizs} visualização(ões)"),
                style_subtitle,
            )
        )
        story.append(Spacer(1, 8 * mm))

        # ── Slides ────────────────────────────────────────────────────────────
        for slide_idx, slide in enumerate(analysis.slides):
            vizs = [
                v for v in slide.visualizations
                if v.config and v.config.visualization_type != VisualizationType.MEASURES
            ]
            if not vizs:
                continue

            if slide_idx > 0:
                story.append(PageBreak())

            story.append(Paragraph(self._t(slide.title), style_slide))
            story.append(self._hr(doc, page_size, options.margin_mm * mm))
            story.append(Spacer(1, 4 * mm))

            for viz in vizs:
                vtype = viz.config.visualization_type
                viz_title = viz.config.title

                if viz_title:
                    story.append(Paragraph(self._t(viz_title), style_viz_title))

                if vtype == VisualizationType.METRIC_CARD and viz.id in metric_data:
                    story.extend(
                        self._build_metric(metric_data[viz.id], style_metric_value, style_metric_label)
                    )

                elif vtype == VisualizationType.TABLE and viz.id in table_data:
                    story.extend(
                        self._build_table(table_data[viz.id], doc, page_size, options.margin_mm * mm, font_reg, font_bold)
                    )

                elif viz.id in chart_images:
                    story.extend(
                        self._build_chart(chart_images[viz.id], doc, page_size, options.margin_mm * mm)
                    )

                else:
                    story.append(
                        Paragraph("[Visual não disponível]", style_caption)
                    )

                if options.include_comments and viz.comment:
                    story.append(Paragraph(self._t(f"💬 {viz.comment}"), style_comment))

                story.append(Spacer(1, 4 * mm))

        # ── Rodapé ───────────────────────────────────────────────────────────
        if options.footer_text:
            story.append(Spacer(1, 8 * mm))
            story.append(Paragraph(self._t(options.footer_text), style_caption))

        doc.build(story)
        return output_path

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _hr(self, doc, page_size, margin):
        from reportlab.platypus import HRFlowable
        usable_width = page_size[0] - 2 * margin
        return HRFlowable(
            width=usable_width,
            thickness=0.5,
            color="#E2E8F0",
            spaceAfter=6,
        )

    def _build_chart(self, img_bytes: bytes, doc, page_size, margin) -> list:
        from reportlab.platypus import Image
        from reportlab.lib.units import inch

        usable_width = page_size[0] - 2 * margin
        max_height = page_size[1] * 0.45

        buf = io.BytesIO(img_bytes)
        img = Image(buf, width=usable_width, height=max_height, kind="proportional")
        return [img]

    def _build_table(self, tdata: dict, doc, page_size, margin, font_reg="Helvetica", font_bold="Helvetica-Bold") -> list:
        from reportlab.platypus import Table, TableStyle, Spacer
        from reportlab.lib import colors
        from reportlab.lib.units import mm

        cols = tdata.get("columns", [])
        rows = tdata.get("data", [])
        if not cols or not rows:
            return []

        usable_width = page_size[0] - 2 * margin
        col_w = usable_width / max(len(cols), 1)

        header = [str(c) for c in cols]
        body = [[str(r.get(c, ""))[:30] for c in cols] for r in rows[:60]]
        table_data = [header] + body

        t = Table(table_data, colWidths=[col_w] * len(cols), repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1E293B")),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  font_bold),
            ("FONTSIZE",      (0, 0), (-1, 0),  9),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  8),
            ("TOPPADDING",    (0, 0), (-1, 0),  8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TEXTCOLOR",     (0, 1), (-1, -1), colors.HexColor("#334155")),
            ("FONTNAME",      (0, 1), (-1, -1), font_reg),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("TOPPADDING",    (0, 1), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return [t, Spacer(1, 3 * mm)]

    def _build_metric(self, mdata: dict, style_value, style_label) -> list:
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm

        val = mdata.get("value")
        title = mdata.get("title", "")
        agg_labels = {"sum": "Total", "mean": "Média", "count": "Contagem",
                      "min": "Mínimo", "max": "Máximo"}
        agg_label = agg_labels.get(mdata.get("agg", "sum"), "")

        if val is None:
            return []

        if isinstance(val, float):
            if abs(val) >= 1_000_000:
                formatted = f"{val / 1_000_000:.2f}M"
            elif abs(val) >= 1_000:
                formatted = f"{val / 1_000:.2f}K"
            else:
                formatted = f"{val:.2f}"
        else:
            try:
                formatted = f"{int(val):,}"
            except Exception:
                formatted = str(val)

        inner = [
            [Paragraph(self._t(formatted), style_value)],
            [Paragraph(self._t(f"{agg_label} · {title}"), style_label)],
        ]
        t = Table(inner, colWidths=["100%"])
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
            ("BOX",            (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
            ("ROUNDEDCORNERS", [8]),
            ("TOPPADDING",     (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 14),
            ("LEFTPADDING",    (0, 0), (-1, -1), 20),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 20),
        ]))
        return [t, Spacer(1, 4 * mm)]
