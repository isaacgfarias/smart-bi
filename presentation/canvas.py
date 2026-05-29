"""
Canvas Component - Main slide editing area.
"""

from typing import Optional, List, Callable
import streamlit as st
import polars as pl

from domain.entities import Slide, Visualization, VisualizationConfig, VisualizationType


def render_canvas(
    slide: Optional[Slide],
    data_service,
    analysis_id: str,
    on_update_visualization: Callable,
    on_delete_visualization: Callable,
    on_add_comment: Callable,
    analysis=None,
    on_update_measures: Optional[Callable] = None,
) -> None:
    """Render the main canvas for slide editing."""
    if not slide:
        st.info("👆 Select or create a slide to start editing")
        return

    col1, col2 = st.columns([5, 1])
    with col1:
        new_title = st.text_input(
            "Título do slide", value=slide.title, key=f"slide_title_{slide.id}",
            label_visibility="collapsed", placeholder="Título do slide…",
        )
    with col2:
        st.caption(f"{len(slide.visualizations)} visual{'is' if len(slide.visualizations) != 1 else ''}")

    df = data_service.get_cached_data(analysis_id)
    if df is None:
        st.warning("⚠️ No data loaded. Please upload an XLSX file.")
        return

    # Aplica medidas calculadas ao df base (disponíveis em todos os gráficos)
    measures = getattr(analysis, "measures", None) or []
    if measures:
        try:
            df = data_service.compute_measures(df, measures)
        except Exception:
            pass

    if not slide.visualizations:
        st.markdown(
            """
        <div style='border: 2px dashed #CBD5E1; border-radius: 12px; padding: 64px 32px;
                    text-align: center; color: #94A3B8; margin: 24px 0;
                    background: #F8FAFC;'>
            <div style='font-size: 2.5rem; margin-bottom: 12px;'>📊</div>
            <div style='font-size: 1.1rem; font-weight: 600; color: #64748B; margin-bottom: 6px;'>
                Slide vazio
            </div>
            <div style='font-size: 0.875rem;'>
                Use o painel à direita para adicionar gráficos, tabelas e métricas
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        from infrastructure.chart_factory import ChartFactory

        chart_factory = ChartFactory()

        for idx, viz in enumerate(slide.visualizations):
            render_visualization(
                viz=viz,
                df=df,
                chart_factory=chart_factory,
                index=idx,
                slide_id=slide.id,
                on_update=on_update_visualization,
                on_delete=on_delete_visualization,
                on_add_comment=on_add_comment,
                analysis=analysis,
                on_update_measures=on_update_measures,
            )


def _cast_filter_val(df: pl.DataFrame, col: str, val):
    """Converte o valor do filtro para o dtype da coluna."""
    dtype = df.schema.get(col)
    if dtype in (pl.Float64, pl.Float32):
        try:
            return float(val)
        except (ValueError, TypeError):
            return val
    if dtype in (pl.Int64, pl.Int32, pl.Int16, pl.Int8, pl.UInt64, pl.UInt32):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return val
    return val


def render_viz_filters(viz_id: str, df: pl.DataFrame) -> pl.DataFrame:
    """
    Renderiza o painel de filtros de uma visualização e retorna o df filtrado.
    Os filtros são salvos em st.session_state[f"filters_{viz_id}"].
    """
    key = f"filters_{viz_id}"
    if key not in st.session_state:
        st.session_state[key] = []

    filters: list = st.session_state[key]
    n = len(filters)
    label = f"🔍 Filtros ({n} ativo{'s' if n != 1 else ''})" if n else "🔍 Filtros"

    with st.expander(label, expanded=n > 0):
        if st.button("➕ Adicionar filtro", key=f"add_f_{viz_id}"):
            filters.append({"col": df.columns[0], "op": "eq", "val": ""})
            st.rerun()

        to_remove = []
        for i, f in enumerate(filters):
            c1, c2, c3, c4 = st.columns([3, 2, 4, 1])

            with c1:
                idx = df.columns.index(f["col"]) if f["col"] in df.columns else 0
                col_sel = st.selectbox(
                    "col", df.columns, index=idx,
                    key=f"f_col_{viz_id}_{i}", label_visibility="collapsed",
                )
                filters[i]["col"] = col_sel

            dtype = df.schema.get(col_sel)
            is_numeric = dtype in (
                pl.Float64, pl.Float32, pl.Int64, pl.Int32,
                pl.Int16, pl.Int8, pl.UInt64, pl.UInt32,
            )
            is_date = dtype in (pl.Date, pl.Datetime)

            with c2:
                if is_numeric or is_date:
                    ops = {"eq": "=", "ne": "≠", "gt": ">", "lt": "<",
                           "gte": ">=", "lte": "<=",
                           "is_null": "é nulo", "is_not_null": "não é nulo"}
                else:
                    ops = {"eq": "=", "ne": "≠", "contains": "contém",
                           "in": "está em", "starts_with": "começa com",
                           "is_null": "é nulo", "is_not_null": "não é nulo"}

                cur_op = f["op"] if f["op"] in ops else list(ops)[0]
                op_sel = st.selectbox(
                    "op", list(ops.keys()),
                    index=list(ops.keys()).index(cur_op),
                    format_func=lambda k: ops[k],
                    key=f"f_op_{viz_id}_{i}", label_visibility="collapsed",
                )
                filters[i]["op"] = op_sel

            with c3:
                needs_val = op_sel not in ("is_null", "is_not_null")
                # Key includes col+op so widget type changes don't collide in session state
                val_key = f"f_val_{viz_id}_{i}_{col_sel}_{op_sel}"
                if needs_val:
                    if op_sel == "in":
                        val_input = st.text_input(
                            "val", value=str(f["val"]) if isinstance(f["val"], str) else "",
                            placeholder="val1, val2, val3",
                            key=val_key, label_visibility="collapsed",
                        )
                    elif is_numeric:
                        try:
                            cur_num = float(f["val"]) if not isinstance(f["val"], (list, str)) or (isinstance(f["val"], str) and f["val"] != "") else 0.0
                        except (ValueError, TypeError):
                            cur_num = 0.0
                        val_input = st.number_input(
                            "val", value=cur_num,
                            key=val_key, label_visibility="collapsed",
                        )
                    else:
                        # Categorical: multiselect com valores únicos da coluna
                        unique_vals = df[col_sel].drop_nulls().unique().sort().to_list()
                        cur_sel = f["val"] if isinstance(f["val"], list) else []
                        val_input = st.multiselect(
                            "val", unique_vals, default=[v for v in cur_sel if v in unique_vals],
                            key=val_key, label_visibility="collapsed",
                        )
                    filters[i]["val"] = val_input
                else:
                    st.empty()
                    filters[i]["val"] = ""

            with c4:
                if st.button("❌", key=f"f_rm_{viz_id}_{i}"):
                    to_remove.append(i)

        if to_remove:
            st.session_state[key] = [
                f for j, f in enumerate(filters) if j not in to_remove
            ]
            st.rerun()

    # ── Aplicar filtros ao df ────────────────────────────────────────────────
    result = df
    for f in st.session_state.get(key, []):
        col, op, val = f["col"], f["op"], f["val"]
        if col not in result.columns:
            continue
        # Skip filters without a meaningful value
        if op not in ("is_null", "is_not_null"):
            if isinstance(val, list) and len(val) == 0:
                continue
            if isinstance(val, str) and val.strip() == "":
                continue
        try:
            c = pl.col(col)
            if op == "is_null":
                result = result.filter(c.is_null())
            elif op == "is_not_null":
                result = result.filter(c.is_not_null())
            elif op == "in":
                vals = [v.strip() for v in str(val).split(",") if v.strip()]
                if vals:
                    result = result.filter(c.cast(pl.String).is_in(vals))
            elif op == "contains":
                result = result.filter(c.cast(pl.String).str.contains(str(val), literal=True))
            elif op == "starts_with":
                result = result.filter(c.cast(pl.String).str.starts_with(str(val)))
            elif op == "eq":
                if isinstance(val, list):
                    result = result.filter(c.cast(pl.String).is_in([str(v) for v in val]))
                else:
                    result = result.filter(c == _cast_filter_val(result, col, val))
            elif op == "ne":
                if isinstance(val, list):
                    result = result.filter(c.cast(pl.String).is_in([str(v) for v in val]).not_())
                else:
                    result = result.filter(c != _cast_filter_val(result, col, val))
            elif op == "gt":
                result = result.filter(c > _cast_filter_val(result, col, val))
            elif op == "lt":
                result = result.filter(c < _cast_filter_val(result, col, val))
            elif op == "gte":
                result = result.filter(c >= _cast_filter_val(result, col, val))
            elif op == "lte":
                result = result.filter(c <= _cast_filter_val(result, col, val))
        except Exception as e:
            st.warning(f"Filtro inválido em '{col}': {e}")

    return result


_SORT_OPTS: dict = {
    "none":       "Sem ordenação",
    "x_asc":      "Categoria A→Z",
    "x_desc":     "Categoria Z→A",
    "value_asc":  "Valor ↑",
    "value_desc": "Valor ↓",
}

_SORTABLE = {
    VisualizationType.COLUMN_CHART,
    VisualizationType.BAR_CHART,
    VisualizationType.PIE_CHART,
}

_SEARCHABLE = {
    VisualizationType.COLUMN_CHART,
    VisualizationType.BAR_CHART,
    VisualizationType.PIE_CHART,
    VisualizationType.LINE_CHART,
    VisualizationType.AREA_CHART,
    VisualizationType.SCATTER_PLOT,
    VisualizationType.TABLE,
}


def render_interactive_controls(
    viz_id: str, df: pl.DataFrame, config
) -> tuple:
    """
    Renderiza barra de busca + ordenação acima do gráfico.
    Retorna (df_filtrado_pela_busca, sort_by: str).
    """
    vtype = config.visualization_type
    if vtype not in _SEARCHABLE:
        return df, "none"

    has_sort = vtype in _SORTABLE
    c_search, c_sort = st.columns([5, 3])

    with c_search:
        search = st.text_input(
            "busca",
            placeholder="🔍 Buscar na visualização...",
            key=f"search_{viz_id}",
            label_visibility="collapsed",
        )

    sort_by = "none"
    with c_sort:
        if has_sort:
            sort_by = st.selectbox(
                "ordenar",
                options=list(_SORT_OPTS.keys()),
                format_func=lambda k: _SORT_OPTS[k],
                key=f"sort_{viz_id}",
                label_visibility="collapsed",
            )
        else:
            st.empty()

    # Aplicar busca ao df (pré-agregação)
    if search:
        try:
            if vtype == VisualizationType.TABLE:
                # Busca em todas as colunas string
                str_cols = [
                    c for c in df.columns
                    if df.schema.get(c) in (pl.Utf8, pl.String)
                ]
                if str_cols:
                    mask = pl.lit(False)
                    for col in str_cols:
                        mask = mask | pl.col(col).cast(pl.String).str.to_lowercase().str.contains(
                            search.lower(), literal=True
                        )
                    df = df.filter(mask)
            elif config.x_column and config.x_column in df.columns:
                # Busca nos valores da categoria X
                df = df.filter(
                    pl.col(config.x_column).cast(pl.String).str.to_lowercase()
                    .str.contains(search.lower(), literal=True)
                )
        except Exception:
            pass

    return df, sort_by


def render_measures_panel(
    viz_id: str,
    analysis,
    on_update_measures: Optional[Callable],
    df: Optional[pl.DataFrame] = None,
) -> None:
    """Painel para criar e gerenciar medidas calculadas."""
    measures: list = list(getattr(analysis, "measures", None) or [])
    all_cols: list = list(df.columns) if df is not None else []
    default_col: str = all_cols[0] if all_cols else ""
    _OPS = ["+", "-", "*", "/"]
    parts_key = f"mparts_{viz_id}"

    st.markdown("**📐 Medidas Calculadas**")
    st.caption(
        "Combine colunas com operadores `+  −  ×  ÷`. "
        "As medidas ficam disponíveis como métricas em todos os gráficos."
    )

    # ── Lista das medidas já definidas ────────────────────────────────────────
    to_del = []
    for i, m in enumerate(measures):
        c1, c2, c3 = st.columns([3, 6, 1])
        with c1:
            st.text_input(
                "Nome", value=m.get("name", ""),
                key=f"mname_{viz_id}_{i}", disabled=True, label_visibility="collapsed",
            )
        with c2:
            st.text_input(
                "Expressão", value=m.get("expression", ""),
                key=f"mexpr_{viz_id}_{i}", disabled=True, label_visibility="collapsed",
            )
        with c3:
            if st.button("❌", key=f"mdel_{viz_id}_{i}", help="Remover medida"):
                to_del.append(i)

    if to_del:
        updated = [m for j, m in enumerate(measures) if j not in to_del]
        if on_update_measures:
            on_update_measures(updated)
        st.rerun()

    # ── Formulário de nova medida (estilo filtros) ────────────────────────────
    st.markdown("---")
    st.markdown("**➕ Nova Medida**")

    # Inicializa com 2 campos se ainda não existe
    if parts_key not in st.session_state:
        st.session_state[parts_key] = [
            {"op": "",  "col": default_col},
            {"op": "/", "col": default_col},
        ]

    parts: list = st.session_state[parts_key]

    new_name = st.text_input(
        "Nome da Medida",
        placeholder="ex: Ticket Médio",
        key=f"mnew_name_{viz_id}",
    )

    to_remove_parts = []
    for i, part in enumerate(parts):
        if i == 0:
            c_val, c_rm = st.columns([8, 1])
        else:
            c_op, c_val, c_rm = st.columns([1, 7, 1])
            with c_op:
                cur_op = part["op"] if part["op"] in _OPS else "/"
                parts[i]["op"] = st.selectbox(
                    "op", _OPS,
                    index=_OPS.index(cur_op),
                    key=f"mop_{viz_id}_{i}",
                    label_visibility="collapsed",
                )

        with c_val:
            if all_cols:
                cur_col = part["col"] if part["col"] in all_cols else default_col
                parts[i]["col"] = st.selectbox(
                    "coluna", all_cols,
                    index=all_cols.index(cur_col),
                    key=f"mcol_{viz_id}_{i}",
                    label_visibility="collapsed",
                )
            else:
                st.caption("Sem colunas disponíveis")

        with c_rm:
            if len(parts) > 1:
                if st.button("❌", key=f"mrm_{viz_id}_{i}"):
                    to_remove_parts.append(i)

    if to_remove_parts:
        st.session_state[parts_key] = [p for j, p in enumerate(parts) if j not in to_remove_parts]
        st.rerun()

    if st.button("➕ Adicionar campo", key=f"madd_part_{viz_id}"):
        parts.append({"op": "+", "col": default_col})
        st.session_state[parts_key] = parts
        st.rerun()

    # Monta e exibe a expressão gerada
    tokens = []
    for i, part in enumerate(parts):
        col = part.get("col", "")
        if not col:
            continue
        if i > 0 and tokens:
            tokens.append(part.get("op", "+"))
        tokens.append(f"[{col}]")
    expr = " ".join(tokens)

    if expr:
        st.caption(f"**Expressão:** `{expr}`")

    if st.button("💾 Adicionar Medida", key=f"msave_{viz_id}", type="primary"):
        name = new_name.strip()
        if name and expr:
            measures.append({"name": name, "expression": expr})
            if on_update_measures:
                on_update_measures(measures)
            # Reseta o formulário
            if parts_key in st.session_state:
                del st.session_state[parts_key]
            st.success(f"Medida '{name}' adicionada!")
            st.rerun()
        else:
            st.warning("Preencha o nome e adicione ao menos um campo.")


def render_visualization(
    viz: Visualization,
    df: pl.DataFrame,
    chart_factory,
    index: int,
    slide_id: str,
    on_update: Callable,
    on_delete: Callable,
    on_add_comment: Callable,
    analysis=None,
    on_update_measures: Optional[Callable] = None,
) -> None:
    """Render a single visualization inside a styled card."""
    is_measures = (
        viz.config is not None
        and viz.config.visualization_type == VisualizationType.MEASURES
    )
    title = (
        viz.config.title
        if viz.config and viz.config.title
        else f"Visualização {index + 1}"
    )

    # ── Card wrapper ──────────────────────────────────────────────────────────
    st.markdown('<div class="viz-card">', unsafe_allow_html=True)

    # Header: título + ações
    col_title, col_actions = st.columns([6, 1])
    with col_title:
        st.markdown(
            f'<p class="viz-card-title">{title}</p>',
            unsafe_allow_html=True,
        )
    with col_actions:
        btn_cols = st.columns(2)
        with btn_cols[0]:
            edit_help = "Gerir medidas" if is_measures else "Configurar"
            if st.button("✏️", key=f"edit_{viz.id}", help=edit_help):
                if is_measures:
                    # Abre o dialog de medidas via session_state
                    st.session_state.configuring_new_viz = VisualizationType.MEASURES
                else:
                    st.session_state.editing_viz_id = viz.id
                    st.session_state.editing_slide_id = slide_id
                st.rerun()
        with btn_cols[1]:
            if st.button("🗑", key=f"delete_{viz.id}", help="Excluir"):
                on_delete(slide_id, viz.id)
                st.rerun()

    # ── Conteúdo ──────────────────────────────────────────────────────────────
    if is_measures:
        measures: list = list(getattr(analysis, "measures", None) or [])
        if measures:
            for m in measures:
                name = m.get("name", "")
                expr = m.get("expression", "")
                st.markdown(
                    f"<div style='display:flex;align-items:baseline;gap:8px;"
                    f"padding:4px 0;border-bottom:1px solid rgba(0,0,0,.06);'>"
                    f"<span style='font-size:.82rem;font-weight:600;color:#1E293B;'>{name}</span>"
                    f"<span style='font-size:.75rem;color:#64748B;font-family:monospace;'>{expr}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Nenhuma medida ainda. Clique em ✏️ para adicionar.")

    elif viz.config:
        # Filtros — render_viz_filters já contém o expander próprio com badge
        df_filtered = render_viz_filters(viz.id, df)

        # Busca + ordenação
        df_filtered, sort_by = render_interactive_controls(
            viz.id, df_filtered, viz.config
        )

        # Gráfico / tabela
        try:
            if viz.config.visualization_type == VisualizationType.TABLE:
                render_table(viz, df_filtered)
            elif viz.config.visualization_type == VisualizationType.METRIC_CARD:
                render_metric_card(viz, df_filtered)
            else:
                fig = chart_factory.create_chart(
                    df_filtered, viz.config, sort_by=sort_by
                )
                st.plotly_chart(fig, width='stretch', key=f"chart_{viz.id}")
        except Exception as e:
            st.error(f"Erro ao renderizar: {e}")

        # Comentário
        if viz.comment:
            st.caption(f"💬 {viz.comment}")
        with st.expander("💬 Comentário", expanded=False):
            comment = st.text_area(
                "Comentário", value=viz.comment, key=f"comment_{viz.id}", height=60,
                label_visibility="collapsed",
            )
            if st.button("Salvar", key=f"save_comment_{viz.id}"):
                on_add_comment(slide_id, viz.id, comment)
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_table(viz: Visualization, df: pl.DataFrame) -> None:
    """Render a table visualization."""
    config = viz.config
    if not config:
        return

    # Prioridade: y_columns (lista completa) → campos legados → todas as colunas
    if config.y_columns:
        columns_to_show = [c for c in config.y_columns if c in df.columns]
    elif config.x_column or config.y_column:
        columns_to_show = [
            c for c in [config.x_column, config.y_column, config.color_column]
            if c and c in df.columns
        ]
    else:
        columns_to_show = list(df.columns[:10])

    if not columns_to_show:
        st.warning("Nenhuma coluna válida para exibir.")
        return

    table_df = df.select(columns_to_show)
    st.dataframe(table_df.head(200).to_pandas(), width='stretch', height=300)


def render_metric_card(viz: Visualization, df: pl.DataFrame) -> None:
    """Render a metric card visualization."""
    config = viz.config
    if not config or not config.y_column:
        st.warning("Please select a column for the metric")
        return

    try:
        col = df[config.y_column]

        if config.aggregation == "mean":
            value = col.mean()
            label = "Average"
        elif config.aggregation == "sum":
            value = col.sum()
            label = "Total"
        elif config.aggregation == "count":
            value = col.count()
            label = "Count"
        elif config.aggregation == "min":
            value = col.min()
            label = "Minimum"
        elif config.aggregation == "max":
            value = col.max()
            label = "Maximum"
        else:
            value = col.sum()
            label = "Total"

        if isinstance(value, float):
            if abs(value) >= 1_000_000:
                formatted_value = f"{value / 1_000_000:.2f}M"
            elif abs(value) >= 1_000:
                formatted_value = f"{value / 1_000:.2f}K"
            else:
                formatted_value = f"{value:.2f}"
        else:
            formatted_value = f"{value:,}"

        st.markdown(
            f"""
        <div style='background:linear-gradient(135deg,#3B82F6 0%,#1D4ED8 100%);
                    border-radius:12px;padding:28px 24px;color:white;text-align:center;margin:8px 0;
                    box-shadow:0 4px 16px rgba(59,130,246,.35);'>
            <div style='font-size:2.6rem;font-weight:800;letter-spacing:-1px;margin-bottom:6px;'>
                {formatted_value}
            </div>
            <div style='font-size:.9rem;opacity:.85;font-weight:500;'>
                {config.title or f"{label} — {config.y_column}"}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.error(f"Error calculating metric: {str(e)}")


def render_slide_navigator(
    slides: List[Slide],
    current_slide_id: str,
    on_slide_change: Callable,
    on_add_slide: Callable,
    on_delete_slide: Callable,
) -> None:
    """Barra de navegação de slides em estilo tab bar."""
    st.markdown(
        "<hr style='border:none;border-top:1px solid #E2E8F0;margin:24px 0 12px;'/>",
        unsafe_allow_html=True,
    )

    # Tabs dos slides + botão de adicionar numa linha
    n = len(slides)
    # +1 coluna estreita para o botão "+"
    col_widths = [3] * min(n, 8) + [1]
    cols = st.columns(col_widths)

    for i, slide in enumerate(slides[:8]):
        with cols[i]:
            is_current = slide.id == current_slide_id
            short = slide.title[:14] + "…" if len(slide.title) > 14 else slide.title
            label = f"**{i+1}. {short}**" if is_current else f"{i+1}. {short}"
            if st.button(
                label,
                key=f"nav_slide_{slide.id}",
                width='stretch',
                type="primary" if is_current else "secondary",
            ):
                on_slide_change(slide.id)
                st.rerun()

    with cols[-1]:
        if st.button("＋", width='stretch', help="Novo slide"):
            on_add_slide()
            st.rerun()

    # Botão deletar slide atual (só se houver mais de 1)
    if n > 1:
        _, col_del = st.columns([6, 1])
        with col_del:
            if st.button(
                "🗑 Deletar slide",
                width='stretch',
                help="Remover slide atual",
            ):
                on_delete_slide(current_slide_id)
                st.rerun()
