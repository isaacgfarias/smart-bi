"""
Components Module - Reusable UI components.
"""

from typing import Dict, Any, List, Optional, Callable
import streamlit as st
from datetime import datetime
import os


def render_settings_modal(current_settings: Dict[str, Any], on_save: Callable) -> None:
    """Render the settings modal/dialog."""
    st.markdown("## ⚙️ Definições")

    st.markdown("### Exportação PDF")
    paper_size = st.selectbox(
        "Tamanho do papel",
        ["a4", "letter", "legal"],
        index=["a4", "letter", "legal"].index(
            current_settings.get("paper_size", "a4")
        ),
    )
    include_comments = st.checkbox(
        "Incluir comentários na exportação",
        value=current_settings.get("include_comments", True),
    )

    st.markdown("---")
    if st.button("💾 Salvar", type="primary"):
        new_settings = {
            **current_settings,
            "theme": "light",
            "paper_size": paper_size,
            "include_comments": include_comments,
        }
        on_save(new_settings)
        st.success("Definições salvas!")


def render_analysis_history(
    analyses: List[Dict[str, Any]],
    on_select: Callable,
    on_delete: Callable,
    on_rename: Callable,
) -> None:
    """Render the analysis history list."""
    st.markdown("## 📜 Analysis History")

    if not analyses:
        st.info("No analyses yet. Create a new analysis to get started.")
        return

    for analysis in analyses:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**{analysis.get('name', 'Unnamed')}**")
                st.caption(
                    f"📄 {analysis.get('file_name', 'No file')} | 📊 {analysis.get('slide_count', 0)} slides"
                )

                updated = analysis.get("updated_at", "")
                if updated:
                    try:
                        dt = datetime.fromisoformat(updated)
                        st.caption(f"Updated: {dt.strftime('%Y-%m-%d %H:%M')}")
                    except Exception:
                        pass

            with col2:
                if st.button(
                    "📂 Open", key=f"open_{analysis['id']}", width='stretch'
                ):
                    on_select(analysis["id"])

            with col3:
                if st.button(
                    "🗑️", key=f"delete_{analysis['id']}", help="Delete analysis"
                ):
                    on_delete(analysis["id"])
                    st.rerun()

            st.markdown("---")


@st.dialog("📤 Exportar PDF", width="large")
def render_export_dialog(analysis, on_export: Callable) -> None:
    """Modal de exportação para PDF (usando @st.dialog)."""
    total_vizs = sum(
        1 for s in analysis.slides
        for v in s.visualizations
        if v.config
    )

    st.markdown(
        f"<p style='color:#64748B;font-size:.88rem;margin:0 0 16px;'>"
        f"<b>{analysis.name}</b> · {len(analysis.slides)} slide(s) · "
        f"{total_vizs} visualização(ões)</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        paper_size = st.selectbox("Tamanho do papel", ["A4", "Letter", "Legal"], index=0)
    with col2:
        orientation = st.selectbox("Orientação", ["Portrait", "Landscape"], index=0)

    file_name = st.text_input(
        "Nome do arquivo",
        value=analysis.name,
        placeholder="Nome do PDF…",
    )
    subtitle = st.text_input(
        "Subtítulo / Descrição (opcional)",
        placeholder="Ex: Relatório mensal de vendas…",
    )

    col3, col4 = st.columns(2)
    with col3:
        include_comments = st.checkbox("Incluir comentários", value=True)
    with col4:
        st.caption("Filtros ativos são aplicados automaticamente no PDF.")

    footer_text = st.text_input("Rodapé (opcional)", placeholder="Texto do rodapé…")

    st.markdown("---")

    col_btn, col_cancel = st.columns([1, 1])
    with col_btn:
        gerar = st.button("📤 Gerar PDF", type="primary", width='stretch')
    with col_cancel:
        if st.button("✗ Cancelar", width='stretch'):
            st.rerun()

    if gerar:
        with st.spinner("Gerando PDF…"):
            export_options = {
                "format": "pdf",
                "paper_size": paper_size.lower(),
                "orientation": orientation.lower(),
                "include_comments": include_comments,
                "footer_text": footer_text,
                "file_name": file_name.strip() or analysis.name,
                "subtitle": subtitle.strip(),
            }
            result = on_export(analysis, export_options)

        if result:
            try:
                with open(result, "rb") as f:
                    file_data = f.read()
                st.success("PDF gerado!")
                st.download_button(
                    label="📥 Baixar PDF",
                    data=file_data,
                    file_name=os.path.basename(result),
                    mime="application/pdf",
                    width='stretch',
                )
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {str(e)}")


def render_toolbar(
    current_slide_idx: int,
    total_slides: int,
    on_prev: Callable,
    on_next: Callable,
    on_add_slide: Callable,
    on_export: Callable,
) -> None:
    """Render the main toolbar."""
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

    with col1:
        if st.button("⬅️", help="Previous Slide", disabled=current_slide_idx == 0):
            on_prev()

    with col2:
        st.markdown(
            f"<div style='text-align: center; padding-top: 8px;'>{current_slide_idx + 1} / {total_slides}</div>",
            unsafe_allow_html=True,
        )

    with col3:
        if st.button("➕ Add Slide", width='stretch'):
            on_add_slide()

    with col4:
        if st.button(
            "➡️", help="Next Slide", disabled=current_slide_idx >= total_slides - 1
        ):
            on_next()

    with col5:
        if st.button("📤 Export", type="primary", width='stretch'):
            on_export()


def render_welcome_screen(on_new_analysis: Callable) -> None:
    """Tela de boas-vindas com hero e cards de features."""
    # Hero
    st.markdown(
        """
        <div style='text-align:center;padding:48px 16px 32px;'>
            <div style='font-size:3rem;margin-bottom:12px;'>📊</div>
            <h1 style='font-size:2rem;font-weight:800;color:#1E293B;margin:0 0 8px;'>
                Smart BI
            </h1>
            <p style='font-size:1.05rem;color:#64748B;max-width:420px;margin:0 auto 28px;'>
                Crie dashboards interativos a partir das suas planilhas Excel em minutos.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, col_btn, _ = st.columns([2, 3, 2])
    with col_btn:
        if st.button(
            "📂  Carregar planilha Excel",
            type="primary",
            width='stretch',
        ):
            on_new_analysis()

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # Feature cards
    features = [
        ("📊", "10 tipos de gráfico", "Colunas, Barras, Linhas, Pizza, Área, Dispersão, Histograma, Box, Heatmap e mais"),
        ("🔍", "Filtros por visual", "Filtre cada gráfico de forma independente sem afetar os demais"),
        ("📐", "Medidas calculadas", "Crie KPIs customizados como Ticket Médio, Margem % e Crescimento"),
        ("📤", "Exportação em PDF", "Gere relatórios prontos para apresentação com um clique"),
    ]

    cols = st.columns(len(features))
    for col, (icon, title, desc) in zip(cols, features):
        with col:
            st.markdown(
                f"""
                <div style='background:#FAF9F6;border:1px solid #DDD8D0;border-radius:10px;
                            padding:20px 16px;text-align:center;height:100%;'>
                    <div style='font-size:1.8rem;margin-bottom:10px;'>{icon}</div>
                    <div style='font-size:.88rem;font-weight:600;color:#2C2B28;margin-bottom:6px;'>{title}</div>
                    <div style='font-size:.78rem;color:#7A7870;line-height:1.4;'>{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_notification(message: str, type: str = "info") -> None:
    """Render a notification message."""
    if type == "info":
        st.info(message)
    elif type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)


def render_confirmation_dialog(
    title: str, message: str, on_confirm: Callable, on_cancel: Callable
) -> None:
    """Render a confirmation dialog."""
    st.markdown(f"### {title}")
    st.markdown(message)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✓ Confirm", type="primary", width='stretch'):
            on_confirm()

    with col2:
        if st.button("✗ Cancel", width='stretch'):
            on_cancel()
