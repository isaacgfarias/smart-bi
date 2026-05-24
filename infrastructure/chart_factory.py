"""
Chart Factory - Creates visualization charts using Plotly.
Follows Factory Pattern for creating different chart types.
"""

from typing import Dict, Any, Optional, List
import polars as pl
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from domain.entities import VisualizationType, VisualizationConfig


class ChartFactory:
    """Factory class for creating different types of charts using Plotly."""

    COLOR_SCHEMES: Dict[str, list] = {
        "default": px.colors.qualitative.Plotly,
        "pastel":  px.colors.qualitative.Pastel,
        "dark":    px.colors.qualitative.Dark24,
        "vivid":   px.colors.qualitative.Vivid,
        "safe":    px.colors.qualitative.Safe,
        "d3":      px.colors.qualitative.D3,
        "set1":    px.colors.qualitative.Set1,
        "set2":    px.colors.qualitative.Set2,
    }

    def __init__(self, default_height: int = 400, default_width: int = 600):
        self.default_height = default_height
        self.default_width = default_width

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def create_chart(
        self,
        df: pl.DataFrame,
        config: VisualizationConfig,
        sort_by: str = "none",
    ) -> go.Figure:
        """Create a Plotly figure based on VisualizationConfig."""
        vtype = config.visualization_type

        # Tipos que suportam ordenação pelo usuário
        if vtype == VisualizationType.COLUMN_CHART:
            fig = self._create_column_chart(df, config, sort_by)
        elif vtype == VisualizationType.BAR_CHART:
            fig = self._create_bar_chart(df, config, sort_by)
        elif vtype == VisualizationType.PIE_CHART:
            fig = self._create_pie_chart(df, config, sort_by)
        elif vtype == VisualizationType.LINE_CHART:
            fig = self._create_line_chart(df, config)
        elif vtype == VisualizationType.AREA_CHART:
            fig = self._create_area_chart(df, config)
        elif vtype == VisualizationType.SCATTER_PLOT:
            fig = self._create_scatter_plot(df, config)
        elif vtype == VisualizationType.HISTOGRAM:
            fig = self._create_histogram(df, config)
        elif vtype == VisualizationType.BOX_PLOT:
            fig = self._create_box_plot(df, config)
        else:
            fig = self._create_empty_figure(
                f"Tipo '{vtype.value}' não implementado"
            )

        self._apply_common_style(fig, config)

        # Coluna com muitas categorias: aplica margem após _apply_common_style
        # para não ser sobrescrita
        if vtype == VisualizationType.COLUMN_CHART and config.x_column and config.x_column in df.columns:
            try:
                n_cats = df[config.x_column].n_unique()
            except Exception:
                n_cats = 0
            if n_cats > 6:
                fig.update_layout(margin=dict(b=160))

        return fig

    def export_figure_to_bytes(
        self, fig: go.Figure, format: str = "png", scale: float = 2.0
    ) -> bytes:
        try:
            pio.kaleido.scope.chromium_args = ("--no-sandbox",)
        except Exception:
            pass
        return pio.to_image(fig, format=format, scale=scale)

    def export_figure_to_base64(
        self, fig: go.Figure, format: str = "png", scale: float = 2.0
    ) -> str:
        import base64
        return base64.b64encode(self.export_figure_to_bytes(fig, format, scale)).decode()

    def render_to_image_bytes(
        self,
        df: pl.DataFrame,
        config: "VisualizationConfig",
    ) -> bytes:
        """Gera PNG do gráfico usando Pillow ImageDraw — sem C extensions extras."""
        import io as _io
        import math
        from PIL import Image, ImageDraw, ImageFont

        W, H = 1200, 650
        ML, MR, MT, MB = 110, 40, 55, 180  # margens — MB grande para rótulos rotacionados

        PALETTE = [
            (78, 121, 167), (242, 142, 43), (225, 87, 89), (118, 183, 178),
            (89, 161, 79),  (237, 201, 72), (176, 122, 161),(255, 157, 167),
            (156, 117, 95), (186, 176, 172),
        ]

        def hex_to_rgb(h: str) -> tuple:
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        # usa a cor escolhida pelo utilizador como primeira cor da paleta
        _user_hex = (config.color_scheme or "").strip()
        if _user_hex.startswith("#") and len(_user_hex) == 7:
            try:
                _ur, _ug, _ub = hex_to_rgb(_user_hex)
                PALETTE[0] = (_ur, _ug, _ub)
            except Exception:
                pass

        def palette_color(i: int, alpha: int = 255) -> tuple:
            r, g, b = PALETTE[i % len(PALETTE)]
            return (r, g, b, alpha)

        def fmt_label(v, max_len=10) -> str:
            s = str(v)
            return s[:max_len] + "…" if len(s) > max_len else s

        vtype = config.visualization_type
        title = config.title or vtype.value.replace("_", " ").title()
        agg = config.aggregation or "sum"

        img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img, "RGBA")

        def _load_ttf(size: int):
            """Carrega TTF com suporte a acentos; fallback para bitmap."""
            import os as _os
            # matplotlib é garantido no requirements.txt e inclui DejaVu
            _candidates = []
            try:
                import matplotlib as _mpl
                _mpl_ttf = _os.path.join(
                    _os.path.dirname(_mpl.__file__), "mpl-data", "fonts", "ttf"
                )
                _candidates += [
                    _os.path.join(_mpl_ttf, "DejaVuSans.ttf"),
                    _os.path.join(_mpl_ttf, "DejaVuSans-Oblique.ttf"),
                ]
            except Exception:
                pass
            _candidates += [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
            ]
            for path in _candidates:
                if _os.path.exists(path):
                    try:
                        return ImageFont.truetype(path, size)
                    except Exception:
                        continue
            try:
                return ImageFont.load_default(size=size)
            except Exception:
                return ImageFont.load_default()

        font_sm   = _load_ttf(12)
        font_md   = _load_ttf(14)
        font_bold = _load_ttf(16)

        cx0 = ML          # chart area left
        cy0 = MT          # chart area top
        cw  = W - ML - MR # chart area width
        ch  = H - MT - MB # chart area height
        cx1 = cx0 + cw    # chart area right
        cy1 = cy0 + ch    # chart area bottom  (pixels grow downward)

        GRAY_AXIS  = (203, 213, 225)
        GRAY_GRID  = (226, 232, 240)
        GRAY_LABEL = (71, 85, 105)

        def draw_axes():
            draw.line([(cx0, cy0), (cx0, cy1)], fill=GRAY_AXIS, width=1)
            draw.line([(cx0, cy1), (cx1, cy1)], fill=GRAY_AXIS, width=1)

        def draw_rotated_text(text, cx, cy, angle=-45, font=None, fill=(71, 85, 105)):
            """Draw text rotated by `angle` degrees, top-left anchor at (cx, cy)."""
            font = font or font_sm
            tmp = Image.new("RGBA", (220, 22), (0, 0, 0, 0))
            tmp_draw = ImageDraw.Draw(tmp)
            tmp_draw.text((0, 0), text, font=font, fill=fill)
            rotated = tmp.rotate(angle, expand=True)
            rx = int(cx - rotated.width / 2)
            ry = int(cy)
            # clamp so label never goes outside image bounds
            rx = max(0, min(rx, W - rotated.width))
            ry = max(0, min(ry, H - rotated.height))
            img.paste(rotated, (rx, ry), rotated)

        def draw_y_grid(min_v, max_v, n=5, integer_labels=False):
            rng = max_v - min_v or 1
            for i in range(n + 1):
                val = min_v + rng * i / n
                y = cy1 - (val - min_v) / rng * ch
                draw.line([(cx0, y), (cx1, y)], fill=GRAY_GRID, width=1)
                if integer_labels:
                    label = f"{round(val):,}"
                else:
                    label = f"{val:,.0f}" if abs(val) >= 10 else f"{val:.1f}"
                draw.text((cx0 - 4, y - 5), label, fill=GRAY_LABEL, font=font_sm, anchor="rm")

        def val_to_y(v, min_v, max_v):
            rng = max_v - min_v or 1
            return cy1 - (v - min_v) / rng * ch

        try:
            # ── Coluna / Barra ───────────────────────────────────────────────
            if vtype in (VisualizationType.COLUMN_CHART, VisualizationType.BAR_CHART):
                x_col = config.x_column
                y_cols = config.y_columns or ([config.y_column] if config.y_column else [])
                y_cols = [c for c in y_cols if c and c in df.columns]
                if x_col and x_col in df.columns and y_cols:
                    agged = self._aggregate(df, x_col, y_cols, agg)
                    cats  = agged[x_col].cast(pl.String).to_list()
                    series = {yc: agged[yc].to_list() for yc in y_cols if yc in agged.columns}
                    all_vals = [v for lst in series.values() for v in lst if v is not None]
                    min_v, max_v = 0, (max(all_vals) * 1.1 if all_vals else 1)

                    if vtype == VisualizationType.COLUMN_CHART:
                        draw_axes()
                        draw_y_grid(min_v, max_v)
                        n_cats  = len(cats)
                        rotate_labels = n_cats > 6
                        group_w = cw / max(n_cats, 1)
                        bar_w   = group_w * 0.6 / max(len(y_cols), 1)
                        for ci, cat in enumerate(cats):
                            x_base = cx0 + group_w * ci + group_w * 0.2
                            for si, (yc, vals) in enumerate(series.items()):
                                v  = vals[ci] if vals[ci] is not None else 0
                                bh = (v - min_v) / (max_v - min_v) * ch
                                bx = x_base + bar_w * si
                                draw.rectangle(
                                    [(bx, cy1 - bh), (bx + bar_w - 1, cy1)],
                                    fill=palette_color(si),
                                )
                            lbl = fmt_label(cat, 12 if not rotate_labels else 14)
                            lx  = x_base + bar_w * len(y_cols) / 2
                            if rotate_labels:
                                draw_rotated_text(lbl, lx, cy1 + 4, angle=45, font=font_sm, fill=GRAY_LABEL)
                            else:
                                draw.text((lx, cy1 + 4), lbl, fill=GRAY_LABEL, font=font_sm, anchor="mt")

                    else:  # BAR_CHART horizontal
                        n_cats = len(cats)
                        bar_h  = ch / max(n_cats, 1) * 0.6
                        all_x  = [v for lst in series.values() for v in lst if v is not None]
                        max_x  = max(all_x) * 1.1 if all_x else 1
                        draw.line([(cx0, cy0), (cx0, cy1)], fill=GRAY_AXIS, width=1)
                        for ci, cat in enumerate(cats):
                            y_base = cy0 + ci * (ch / max(n_cats, 1)) + ch / max(n_cats, 1) * 0.2
                            for si, (yc, vals) in enumerate(series.items()):
                                v  = vals[ci] if vals[ci] is not None else 0
                                bw = v / max_x * cw
                                by = y_base + bar_h * si
                                draw.rectangle(
                                    [(cx0, by), (cx0 + bw, by + bar_h - 1)],
                                    fill=palette_color(si),
                                )
                            lbl = fmt_label(cat, 12)
                            draw.text((cx0 - 4, y_base + bar_h / 2), lbl,
                                      fill=GRAY_LABEL, font=font_sm, anchor="rm")

            # ── Linha / Área ─────────────────────────────────────────────────
            elif vtype in (VisualizationType.LINE_CHART, VisualizationType.AREA_CHART):
                x_col = config.x_column
                y_col = config.y_column or (config.y_columns[0] if config.y_columns else None)
                if x_col and y_col and x_col in df.columns and y_col in df.columns:
                    agged = self._aggregate(df, x_col, [y_col], agg)
                    cats  = agged[x_col].cast(pl.String).to_list()
                    vals  = [v if v is not None else 0 for v in agged[y_col].to_list()]
                    min_v, max_v = 0, (max(vals) * 1.1 if vals else 1)
                    draw_axes()
                    draw_y_grid(min_v, max_v)
                    n    = len(vals)
                    step = cw / max(n - 1, 1)
                    pts  = [(cx0 + i * step, val_to_y(v, min_v, max_v))
                            for i, v in enumerate(vals)]
                    color_line = palette_color(0)
                    if vtype == VisualizationType.AREA_CHART and len(pts) >= 2:
                        poly = [(cx0, cy1)] + list(pts) + [(pts[-1][0], cy1)]
                        draw.polygon(poly, fill=palette_color(0, 80))
                    if len(pts) >= 2:
                        draw.line(pts, fill=color_line, width=2)
                    for i, (px, py) in enumerate(pts):
                        r = 3
                        draw.ellipse([(px - r, py - r), (px + r, py + r)],
                                     fill=color_line, outline=(255, 255, 255, 255), width=1)
                        if i % max(1, n // 8) == 0:
                            draw.text((px, cy1 + 4), fmt_label(cats[i], 8),
                                      fill=GRAY_LABEL, font=font_sm, anchor="mt")

            # ── Pizza ────────────────────────────────────────────────────────
            elif vtype == VisualizationType.PIE_CHART:
                x_col = config.x_column
                y_col = config.y_column
                if x_col and y_col and x_col in df.columns and y_col in df.columns:
                    agged  = self._aggregate(df, x_col, [y_col], agg)
                    labels = agged[x_col].cast(pl.String).to_list()
                    vals   = [abs(v) if v is not None else 0 for v in agged[y_col].to_list()]
                    total  = sum(vals) or 1
                    pcx, pcy = W // 2 - 60, H // 2
                    r = int(min(ch, cw) * 0.38)
                    bbox = [(pcx - r, pcy - r), (pcx + r, pcy + r)]
                    angle = -90.0
                    for i, (lbl, v) in enumerate(zip(labels, vals)):
                        sweep = v / total * 360
                        draw.pieslice(bbox, start=angle, end=angle + sweep,
                                      fill=palette_color(i), outline=(255, 255, 255, 255))
                        mid_a = math.radians(angle + sweep / 2)
                        lx = pcx + (r + 16) * math.cos(mid_a)
                        ly = pcy + (r + 16) * math.sin(mid_a)
                        pct = f"{v / total * 100:.1f}%"
                        draw.text((lx, ly), pct, fill=(51, 65, 85), font=font_sm, anchor="mm")
                        angle += sweep
                    # legend
                    lx0 = pcx + r + 20
                    for i, lbl in enumerate(labels[:10]):
                        ly0 = pcy - r + i * 18
                        draw.rectangle([(lx0, ly0), (lx0 + 10, ly0 + 10)],
                                       fill=palette_color(i))
                        draw.text((lx0 + 14, ly0 + 5), fmt_label(lbl, 14),
                                  fill=GRAY_LABEL, font=font_sm, anchor="lm")

            # ── Dispersão ────────────────────────────────────────────────────
            elif vtype == VisualizationType.SCATTER_PLOT:
                x_col, y_col = config.x_column, config.y_column
                if x_col and y_col and x_col in df.columns and y_col in df.columns:
                    xs = [v for v in df[x_col].to_list() if v is not None]
                    ys = [v for v in df[y_col].to_list() if v is not None]
                    if xs and ys:
                        min_x, max_x = min(xs), max(xs) or 1
                        min_y, max_y = min(ys), max(ys) or 1
                        rx = max_x - min_x or 1
                        ry = max_y - min_y or 1
                        draw_axes()
                        draw_y_grid(min_y, max_y)
                        c = palette_color(0, 140)
                        for xv, yv in list(zip(xs, ys))[:500]:
                            px_ = cx0 + (xv - min_x) / rx * cw
                            py_ = val_to_y(yv, min_y, max_y)
                            r = 3
                            draw.ellipse([(px_ - r, py_ - r), (px_ + r, py_ + r)], fill=c)

            # ── Histograma ───────────────────────────────────────────────────
            elif vtype == VisualizationType.HISTOGRAM:
                x_col = config.x_column
                if x_col and x_col in df.columns:
                    vals = sorted([v for v in df[x_col].to_list() if v is not None])
                    if vals:
                        n_bins = min(20, len(set(vals)))
                        min_v, max_v = vals[0], vals[-1]
                        rng   = max_v - min_v or 1
                        bin_w = rng / n_bins
                        counts = [0] * n_bins
                        for v in vals:
                            bi = min(int((v - min_v) / bin_w), n_bins - 1)
                            counts[bi] += 1
                        max_c = float(max(counts) + 1)
                        draw_axes()
                        draw_y_grid(0, max_c, integer_labels=True)
                        bw = cw / n_bins
                        for i, c in enumerate(counts):
                            bh = c / max_c * ch
                            bx = cx0 + i * bw
                            draw.rectangle(
                                [(bx + 1, cy1 - bh), (bx + bw - 1, cy1)],
                                fill=palette_color(0),
                            )
                        # x-axis bin boundary labels
                        step_bins = max(1, n_bins // 8)
                        for i in range(0, n_bins + 1, step_bins):
                            bin_val = min_v + i * bin_w
                            lbl = f"{bin_val:,.0f}" if abs(bin_val) >= 10 else f"{bin_val:.1f}"
                            bx = cx0 + i * bw
                            draw.text((bx, cy1 + 4), lbl, fill=GRAY_LABEL, font=font_sm, anchor="mt")

            # ── Box Plot ─────────────────────────────────────────────────────
            elif vtype == VisualizationType.BOX_PLOT:
                y_col = config.y_column
                x_col = config.x_column
                if y_col and y_col in df.columns:
                    groups = {}
                    if x_col and x_col in df.columns:
                        for g in df[x_col].unique().sort().to_list():
                            groups[str(g)] = df.filter(pl.col(x_col) == g)[y_col].drop_nulls().to_list()
                    else:
                        groups[y_col] = df[y_col].drop_nulls().to_list()
                    all_v = [v for lst in groups.values() for v in lst]
                    if all_v:
                        min_v, max_v = min(all_v), max(all_v) * 1.05 or 1
                        draw_axes()
                        draw_y_grid(min_v, max_v)
                        gnames = list(groups.keys())
                        gw = cw / len(gnames)
                        for gi, (gname, gvals) in enumerate(groups.items()):
                            if not gvals:
                                continue
                            sv  = sorted(gvals)
                            n   = len(sv)
                            q1  = sv[n // 4]
                            med = sv[n // 2]
                            q3  = sv[3 * n // 4]
                            lo  = sv[0]
                            hi  = sv[-1]
                            bx  = cx0 + gw * gi + gw * 0.25
                            bw2 = gw * 0.5
                            mid = bx + bw2 / 2
                            r, g_c, b = PALETTE[gi % len(PALETTE)]
                            draw.rectangle(
                                [(bx, val_to_y(q3, min_v, max_v)),
                                 (bx + bw2, val_to_y(q1, min_v, max_v))],
                                fill=(r, g_c, b, 100), outline=(r, g_c, b, 255), width=2,
                            )
                            my = val_to_y(med, min_v, max_v)
                            draw.line([(bx, my), (bx + bw2, my)], fill=(r, g_c, b, 255), width=2)
                            draw.line([(mid, val_to_y(lo, min_v, max_v)),
                                       (mid, val_to_y(q1, min_v, max_v))],
                                      fill=(r, g_c, b, 200), width=1)
                            draw.line([(mid, val_to_y(q3, min_v, max_v)),
                                       (mid, val_to_y(hi, min_v, max_v))],
                                      fill=(r, g_c, b, 200), width=1)
                            draw.text((bx + bw2 / 2, cy1 + 4), fmt_label(gname, 10),
                                      fill=GRAY_LABEL, font=font_sm, anchor="mt")

            # ── Heatmap ──────────────────────────────────────────────────────
            elif vtype == VisualizationType.HEATMAP:
                x_col  = config.x_column
                y_col  = config.y_column
                val_col = config.color_column
                if x_col and y_col and val_col and all(
                    c in df.columns for c in [x_col, y_col, val_col]
                ):
                    agged = (df.group_by([x_col, y_col])
                               .agg(pl.col(val_col).sum().alias(val_col)))
                    xs = sorted(set(agged[x_col].cast(pl.String).to_list()))
                    ys = sorted(set(agged[y_col].cast(pl.String).to_list()))
                    lookup = {}
                    for row in agged.iter_rows(named=True):
                        lookup[(str(row[x_col]), str(row[y_col]))] = row[val_col] or 0
                    all_v = list(lookup.values())
                    min_v = min(all_v) if all_v else 0
                    max_v = max(all_v) if all_v else 1
                    rng   = max_v - min_v or 1
                    cell_w = cw / max(len(xs), 1)
                    cell_h = ch / max(len(ys), 1)
                    for xi, xv in enumerate(xs[:20]):
                        for yi, yv in enumerate(ys[:20]):
                            v = lookup.get((xv, yv), 0)
                            t = (v - min_v) / rng
                            r_ = int(237 - 140 * t)
                            g_ = int(247 - 102 * t)
                            b_ = int(252 - 76 * t)
                            px_ = cx0 + xi * cell_w
                            py_ = cy0 + yi * cell_h
                            draw.rectangle(
                                [(px_, py_), (px_ + cell_w - 1, py_ + cell_h - 1)],
                                fill=(r_, g_, b_, 255),
                            )
                        draw.text((cx0 + xi * cell_w + cell_w / 2, cy1 + 4),
                                  fmt_label(xv, 6), fill=GRAY_LABEL, font=font_sm, anchor="mt")
                    for yi, yv in enumerate(ys[:20]):
                        draw.text((cx0 - 4, cy0 + yi * cell_h + cell_h / 2),
                                  fmt_label(yv, 8), fill=GRAY_LABEL, font=font_sm, anchor="rm")

            else:
                draw.text((W // 2, H // 2), f"Visual: {title}",
                          fill=(148, 163, 184), font=font_md, anchor="mm")

        except Exception as e:
            img2 = Image.new("RGBA", (W, H), (255, 245, 245, 255))
            draw2 = ImageDraw.Draw(img2)
            draw2.text((W // 2, H // 2), f"Erro: {str(e)[:60]}",
                       fill=(239, 68, 68), font=font_sm, anchor="mm")
            img = img2
            draw = draw2

        # título
        draw.text((W // 2, 18), title, fill=(30, 41, 59), font=font_bold, anchor="mm")

        buf = _io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        return buf.read()

    def get_available_color_schemes(self) -> List[str]:
        return list(self.COLOR_SCHEMES.keys())

    # ─────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _colors(self, config: VisualizationConfig) -> list:
        cs = config.color_scheme or "default"
        if cs.startswith("#"):
            default = self.COLOR_SCHEMES["default"]
            return [cs] + [c for c in default if c.upper() != cs.upper()]
        return self.COLOR_SCHEMES.get(cs, self.COLOR_SCHEMES["default"])

    def _agg_expr(self, col: str, agg: str) -> pl.Expr:
        return {
            "sum":   pl.col(col).sum(),
            "mean":  pl.col(col).mean(),
            "count": pl.col(col).count(),
            "min":   pl.col(col).min(),
            "max":   pl.col(col).max(),
        }.get(agg, pl.col(col).sum())

    def _aggregate(
        self,
        df: pl.DataFrame,
        x_col: str,
        y_cols: List[str],
        agg: str,
        group_col: Optional[str] = None,
        sort_by: str = "none",
    ) -> pl.DataFrame:
        """GroupBy x_col (+ group_col), aggregate each y_col, then sort."""
        valid_y = [c for c in y_cols if c and c in df.columns]
        if not valid_y or x_col not in df.columns:
            return df

        group_keys = [x_col]
        if group_col and group_col in df.columns and group_col != x_col:
            group_keys.append(group_col)

        result = (
            df.group_by(group_keys)
            .agg([self._agg_expr(c, agg) for c in valid_y])
        )

        # Aplicar ordenação
        if sort_by == "x_asc":
            result = result.sort(x_col, descending=False)
        elif sort_by == "x_desc":
            result = result.sort(x_col, descending=True)
        elif sort_by == "value_asc" and valid_y:
            result = result.sort(valid_y[0], descending=False)
        elif sort_by == "value_desc" and valid_y:
            result = result.sort(valid_y[0], descending=True)
        else:
            result = result.sort(x_col)  # padrão: ordem da categoria

        return result

    def _fmt_values(self, values: list) -> List[str]:
        """Format a list of values for chart text labels."""
        out = []
        for v in values:
            if v is None:
                out.append("")
            elif isinstance(v, float):
                out.append(f"{v:,.2f}")
            else:
                out.append(str(v))
        return out

    def _y_cols_from_config(self, config: VisualizationConfig) -> List[str]:
        """Return the effective list of Y columns from config."""
        if config.y_columns:
            return [c for c in config.y_columns if c]
        if config.y_column:
            return [config.y_column]
        return []

    # ─────────────────────────────────────────────────────────────────────────
    # Chart builders
    # ─────────────────────────────────────────────────────────────────────────

    def _create_column_chart(
        self, df: pl.DataFrame, config: VisualizationConfig, sort_by: str = "none"
    ) -> go.Figure:
        """Vertical bar (column) chart – supports multiple Y metrics."""
        y_cols = self._y_cols_from_config(config)
        if not y_cols or not config.x_column:
            return self._create_empty_figure("Selecione as colunas de Categoria e Valor")

        df_plot = self._aggregate(
            df, config.x_column, y_cols, config.aggregation, config.color_column, sort_by
        )
        colors = self._colors(config)
        fig = go.Figure()

        for i, col in enumerate(y_cols):
            values = df_plot[col].to_list()
            fig.add_trace(
                go.Bar(
                    x=df_plot[config.x_column].to_list(),
                    y=values,
                    name=col,
                    marker_color=colors[i % len(colors)],
                    text=self._fmt_values(values) if config.show_values else None,
                    textposition="outside" if config.show_values else "none",
                )
            )

        n_cats = len(df_plot)
        fig.update_layout(
            barmode="group",
            xaxis_title=config.x_column,
            yaxis_title="Valor",
            hovermode="x unified",
        )
        if n_cats > 6:
            fig.update_xaxes(tickangle=-45, automargin=True)
        return fig

    def _create_bar_chart(
        self, df: pl.DataFrame, config: VisualizationConfig, sort_by: str = "none"
    ) -> go.Figure:
        """Horizontal bar chart – supports multiple Y metrics."""
        y_cols = self._y_cols_from_config(config)
        if not y_cols or not config.x_column:
            return self._create_empty_figure("Selecione as colunas de Categoria e Valor")

        df_plot = self._aggregate(df, config.x_column, y_cols, config.aggregation, sort_by=sort_by)
        colors = self._colors(config)
        fig = go.Figure()

        for i, col in enumerate(y_cols):
            values = df_plot[col].to_list()
            fig.add_trace(
                go.Bar(
                    y=df_plot[config.x_column].to_list(),
                    x=values,
                    name=col,
                    orientation="h",
                    marker_color=colors[i % len(colors)],
                    text=self._fmt_values(values) if config.show_values else None,
                    textposition="outside" if config.show_values else "none",
                )
            )

        fig.update_layout(
            barmode="group",
            xaxis_title="Valor",
            yaxis_title=config.x_column,
            hovermode="y unified",
        )
        return fig

    def _create_line_chart(
        self, df: pl.DataFrame, config: VisualizationConfig
    ) -> go.Figure:
        """Line chart with optional aggregation and value labels."""
        x_col = config.x_column
        y_col = config.y_column
        if not x_col or not y_col:
            return self._create_empty_figure("Selecione colunas X e Y")

        df_plot = self._aggregate(df, x_col, [y_col], config.aggregation, config.color_column)
        pdf = df_plot.to_pandas()
        grp = config.color_column if config.color_column and config.color_column in pdf.columns else None

        fig = px.line(
            pdf, x=x_col, y=y_col, color=grp,
            color_discrete_sequence=self._colors(config),
            markers=True,
        )

        if config.show_values:
            fig.update_traces(
                text=pdf[y_col].round(2).astype(str).tolist(),
                textposition="top center",
                mode="lines+markers+text",
            )

        return fig

    def _create_area_chart(
        self, df: pl.DataFrame, config: VisualizationConfig
    ) -> go.Figure:
        """Area chart with optional aggregation and value labels."""
        x_col = config.x_column
        y_col = config.y_column or (config.y_columns[0] if config.y_columns else None)
        if not x_col or not y_col:
            return self._create_empty_figure("Selecione colunas X e Y")

        df_plot = self._aggregate(df, x_col, [y_col], config.aggregation, config.color_column)
        pdf = df_plot.to_pandas()
        grp = config.color_column if config.color_column and config.color_column in pdf.columns else None

        fig = px.area(
            pdf, x=x_col, y=y_col, color=grp,
            color_discrete_sequence=self._colors(config),
        )

        if config.show_values:
            fig.update_traces(
                text=pdf[y_col].round(2).astype(str).tolist(),
                textposition="top center",
                mode="lines+markers+text",
            )

        return fig

    def _create_pie_chart(
        self, df: pl.DataFrame, config: VisualizationConfig, sort_by: str = "none"
    ) -> go.Figure:
        """Pie chart with real aggregation."""
        x_col = config.x_column
        y_col = config.y_column or (config.y_columns[0] if config.y_columns else None)
        if not x_col or not y_col:
            return self._create_empty_figure("Selecione colunas de Categoria e Valor")

        df_plot = self._aggregate(df, x_col, [y_col], config.aggregation, sort_by=sort_by)
        pdf = df_plot.to_pandas()

        fig = px.pie(
            pdf, names=x_col, values=y_col,
            color_discrete_sequence=self._colors(config),
        )
        fig.update_traces(
            textinfo="value+percent+label" if config.show_values else "percent+label"
        )
        return fig

    def _create_scatter_plot(
        self, df: pl.DataFrame, config: VisualizationConfig
    ) -> go.Figure:
        """Scatter plot (raw data, no aggregation)."""
        x_col = config.x_column
        y_col = config.y_column
        if not x_col or not y_col:
            return self._create_empty_figure("Selecione colunas X e Y")

        pdf = df.to_pandas()
        fig = px.scatter(
            pdf, x=x_col, y=y_col,
            color=config.color_column if config.color_column else None,
            size=config.size_column if config.size_column else None,
            color_discrete_sequence=self._colors(config),
            opacity=0.7,
        )

        if config.show_values:
            fig.update_traces(
                text=pdf[y_col].astype(str).tolist(),
                textposition="top center",
            )

        return fig

    def _create_histogram(
        self, df: pl.DataFrame, config: VisualizationConfig
    ) -> go.Figure:
        """Histogram (distribution of one column)."""
        x_col = config.x_column or config.y_column or (config.y_columns[0] if config.y_columns else None)
        if not x_col:
            return self._create_empty_figure("Selecione uma coluna para o histograma")

        pdf = df.to_pandas()
        fig = px.histogram(
            pdf, x=x_col,
            color=config.color_column if config.color_column else None,
            barmode="overlay",
            opacity=0.75,
            color_discrete_sequence=self._colors(config),
        )

        if config.show_values:
            fig.update_traces(texttemplate="%{y}", textposition="outside")

        return fig

    def _create_box_plot(
        self, df: pl.DataFrame, config: VisualizationConfig
    ) -> go.Figure:
        """Box plot (raw data)."""
        y_col = config.y_column
        if not y_col:
            return self._create_empty_figure("Selecione a coluna de valores para o box plot")

        pdf = df.to_pandas()
        fig = px.box(
            pdf,
            x=config.x_column if config.x_column else None,
            y=y_col,
            color=config.color_column if config.color_column else None,
            color_discrete_sequence=self._colors(config),
        )
        return fig

    def _create_heatmap(
        self, df: pl.DataFrame, config: VisualizationConfig
    ) -> go.Figure:
        """Heatmap with pivot aggregation."""
        x_col = config.x_column
        y_col = config.y_column
        if not x_col or not y_col:
            return self._create_empty_figure("Selecione colunas X e Y para o heatmap")

        value_col = config.color_column or y_col
        pivot_pandas = (
            df.group_by([x_col, y_col])
            .agg(self._agg_expr(value_col, config.aggregation).alias("value"))
            .to_pandas()
            .pivot(index=y_col, columns=x_col, values="value")
        )

        fig = px.imshow(
            pivot_pandas,
            color_continuous_scale="Blues",
            aspect="auto",
            text_auto=config.show_values,
        )
        return fig

    # ─────────────────────────────────────────────────────────────────────────
    # Shared utilities
    # ─────────────────────────────────────────────────────────────────────────

    def _create_empty_figure(self, message: str = "Sem dados") -> go.Figure:
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray"),
        )
        fig.update_xaxes(showgrid=False, showticklabels=False)
        fig.update_yaxes(showgrid=False, showticklabels=False)
        return fig

    def _apply_common_style(
        self, fig: go.Figure, config: VisualizationConfig
    ) -> None:
        fig.update_layout(
            title=config.title or "",
            height=self.default_height,
            width=self.default_width,
            showlegend=config.show_legend,
            paper_bgcolor="rgba(255,255,255,1)",
            plot_bgcolor="rgba(248,248,248,1)",
            font=dict(family="Arial, sans-serif", size=12),
            title_font=dict(size=16),
            margin=dict(l=60, r=40, t=60, b=80),
        )

        if config.show_grid:
            fig.update_xaxes(
                showgrid=True, gridwidth=1, gridcolor="rgba(200,200,200,0.5)", automargin=True
            )
            fig.update_yaxes(
                showgrid=True, gridwidth=1, gridcolor="rgba(200,200,200,0.5)", automargin=True
            )
        else:
            fig.update_xaxes(showgrid=False, automargin=True)
            fig.update_yaxes(showgrid=False, automargin=True)
