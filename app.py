"""
Dashboard Builder - Main Application Entry Point
A Streamlit application for building dashboards from Excel data.

This application follows Clean Architecture principles:
- Domain Layer: Core business entities and value objects
- Use Cases Layer: Application services and business logic
- Infrastructure Layer: External services and implementations
- Presentation Layer: Streamlit UI components
"""

import streamlit as st
import polars as pl
from typing import Optional, Dict, Any
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import application components
from domain.entities import (
    Analysis,
    Slide,
    Visualization,
    VisualizationConfig,
    VisualizationType,
    ColumnType,  # Adicionado para suportar a Task de Validação de Tipagem
    User,
)
from domain.value_objects import ExportOptions
from use_cases.analysis_service import AnalysisService, FileAnalysisRepository
from use_cases.data_service import DataService
from use_cases.export_service import ExportService
from infrastructure.auth import JWTHandler
from infrastructure.database import get_database, init_database
from infrastructure.repositories import (
    UserRepositoryImpl,
    FileRepositoryImpl,
    DashboardRepositoryImpl,
)
from infrastructure.storage import get_s3_client
from infrastructure.chart_factory import ChartFactory
from infrastructure.pdf_generator import PDFGenerator
from utils.session_state import (
    SessionStateManager,
    init_session_state,
    get_state,
    set_state,
)

# Import presentation components
from presentation.sidebar import render_sidebar, render_secondary_sidebar
from presentation.canvas import render_canvas, render_slide_navigator
from presentation.widgets import (
    render_widget_palette,
    # render_visualization_config,
    render_data_preview,
    render_column_mapper, # Adicionado para suportar a Task de Renomeação
)
from presentation.components import (
    render_settings_modal,
    render_analysis_history,
    render_export_dialog,
    render_welcome_screen,
    render_notification,
)
from presentation.login import render_login_page, render_user_menu
from use_cases.auth_service import AuthService

# Configure Streamlit page
st.set_page_config(
    page_title="Dashboard Builder",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Dashboard Builder - Create beautiful dashboards from Excel data",
    },
)

# Apply custom CSS
st.markdown(
    """
<style>
    /* ── Hide Streamlit Cloud host icon / toolbar ───────────────────────────── */
    [data-testid="stToolbar"]              {display: none !important;}
    [data-testid="stDecoration"]           {display: none !important;}
    [data-testid="stHeader"]               {display: none !important;}
    [data-testid="stFooter"]               {display: none !important;}
    [data-testid="stToolbarActionButton"]  {display: none !important;}
    #MainMenu                              {display: none !important;}
    header                                 {display: none !important;}
    footer                                 {display: none !important;}
    [class*="viewerBadge"]                 {display: none !important;}
    [class*="styles_viewerBadge"]          {display: none !important;}

    /* ── Design tokens — pastel palette ────────────────────────────────────── */
    :root {
        --primary:      #7BAFC8;
        --primary-dark: #5B8FA8;
        --surface:      #FAF9F6;
        --surface-alt:  #F0EDE8;
        --border:       #DDD8D0;
        --text-main:    #2C2B28;
        --text-muted:   #7A7870;
        --success:      #80B498;
        --danger:       #C4806A;
        --warning:      #C4A460;
        --radius:       10px;
        --radius-sm:    6px;
        --shadow-sm:    0 1px 3px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.03);
        --shadow-md:    0 4px 12px rgba(0,0,0,.07), 0 2px 4px rgba(0,0,0,.03);
    }

    /* ── Layout ────────────────────────────────────────────────────────────── */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
        background-color: var(--surface);
    }
    [data-testid="stAppViewContainer"] {
        background-color: var(--surface);
    }

    /* ── Sidebar ───────────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2E2C2A 0%, #1C1B18 100%);
    }
    section[data-testid="stSidebar"] * {
        color: #C8C4BC !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #EDE9E3 !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,.06);
        border: 1px solid rgba(255,255,255,.10);
        color: #C8C4BC !important;
        border-radius: var(--radius-sm);
        transition: background .15s;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,.11);
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: rgba(255,255,255,.04);
        border: 1px dashed rgba(255,255,255,.18);
        border-radius: var(--radius-sm);
    }

    /* ── Buttons ───────────────────────────────────────────────────────────── */
    .stButton > button {
        border-radius: var(--radius-sm);
        font-weight: 500;
        transition: all .15s ease;
        border: 1px solid var(--border);
        background: white;
        color: var(--text-main) !important;
        font-size: 0.83rem;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow-sm);
        background: var(--surface-alt);
    }
    .stButton > button[kind="primary"] {
        background: var(--primary);
        border-color: var(--primary-dark);
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--primary-dark);
        box-shadow: 0 4px 12px rgba(91,143,168,.30);
    }

    /* ── Inputs & Selects ──────────────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stNumberInput > div > div > input {
        border-radius: var(--radius-sm) !important;
        border-color: var(--border) !important;
        background-color: white !important;
        color: var(--text-main) !important;
        font-size: 0.875rem;
    }
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(123,175,200,.18) !important;
    }

    /* ── Expanders (Filtros / Comentários) ─────────────────────────────────── */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 0.82rem;
        color: var(--text-muted) !important;
        background: var(--surface-alt);
        border-radius: var(--radius-sm);
        border: 1px solid var(--border);
        padding: 6px 10px !important;
    }
    .streamlit-expanderHeader:hover {
        background: var(--border);
    }
    .streamlit-expanderContent {
        border: 1px solid var(--border);
        border-top: none;
        border-radius: 0 0 var(--radius-sm) var(--radius-sm);
        background: white;
        padding: 10px 12px !important;
    }

    /* ── Visualization card wrapper ─────────────────────────────────────────── */
    .viz-card {
        background: #FEFEFE;
        border: 1px solid var(--border);
        border-radius: var(--radius);
        box-shadow: var(--shadow-sm);
        padding: 16px 18px 12px;
        margin-bottom: 18px;
        transition: box-shadow .2s;
    }
    .viz-card:hover {
        box-shadow: var(--shadow-md);
        border-color: #C8C4BC;
    }
    .viz-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    .viz-card-title {
        font-size: 0.88rem;
        font-weight: 600;
        color: var(--text-main);
        margin: 0;
        letter-spacing: -0.01em;
    }

    /* ── Metric card ───────────────────────────────────────────────────────── */
    .stMetric > div {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1rem 1.25rem;
        box-shadow: var(--shadow-sm);
    }

    /* ── Dataframe ─────────────────────────────────────────────────────────── */
    .stDataFrame {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }

    /* ── Plotly chart ───────────────────────────────────────────────────────── */
    .stPlotlyChart {
        border-radius: var(--radius);
        overflow: hidden;
    }

    /* ── Tabs ──────────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 3px;
        background: var(--surface-alt);
        border-radius: var(--radius-sm);
        padding: 4px;
        border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm);
        font-weight: 500;
        font-size: 0.83rem;
        color: var(--text-muted);
        padding: 5px 12px;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: var(--primary-dark) !important;
        box-shadow: var(--shadow-sm);
    }

    /* ── Alerts / Info boxes ────────────────────────────────────────────────── */
    .stAlert {
        border-radius: var(--radius-sm);
        border: none;
        font-size: 0.875rem;
    }

    /* ── Captions & labels ──────────────────────────────────────────────────── */
    .stCaption, small {
        color: var(--text-muted) !important;
        font-size: 0.78rem;
    }

    /* ── Dividers ───────────────────────────────────────────────────────────── */
    hr {
        border: none;
        border-top: 1px solid var(--border);
        margin: 1rem 0;
    }

    /* ── Toast / Notification ───────────────────────────────────────────────── */
    [data-testid="stToast"] {
        border-radius: var(--radius);
        font-size: 0.875rem;
    }

    /* ── Scrollbar ──────────────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--surface-alt); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #94A3B8; }

    /* ── Hide Streamlit chrome ──────────────────────────────────────────────── */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    [data-testid="stToolbar"] { display: none; }

    /* ── Custom sidebar open button ─────────────────────────────────────────── */
    #_sidebar_open_btn {
        display: none;
        position: fixed;
        top: 0.6rem;
        left: 0.6rem;
        z-index: 999999;
        background: #2E2C2A;
        color: #EDE9E3;
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 1.1rem;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        transition: background .15s;
    }
    #_sidebar_open_btn:hover { background: #3D3B38; }
</style>
""",
    unsafe_allow_html=True,
)

import streamlit.components.v1 as _components

# Inject sidebar toggle button via an invisible iframe component.
# st.markdown strips <script> tags; st.components.v1.html runs inside an
# iframe with full script support and can write into window.parent.document.
_components.html(
    """
<script>
(function () {
    var p = window.parent.document;

    // Remove any stale instance from a previous rerun
    var old = p.getElementById('_sb_open_btn');
    if (old) old.remove();

    // Create the ☰ button and inject it into the parent page
    var btn = p.createElement('button');
    btn.id = '_sb_open_btn';
    btn.title = 'Abrir barra lateral';
    btn.textContent = '\\u2630';          // ☰
    btn.style.cssText = [
        'display:none',
        'position:fixed',
        'top:0.6rem',
        'left:0.6rem',
        'z-index:999999',
        'background:#2E2C2A',
        'color:#EDE9E3',
        'border:1px solid rgba(255,255,255,0.15)',
        'border-radius:6px',
        'padding:5px 10px',
        'font-size:1.1rem',
        'cursor:pointer',
        'box-shadow:0 2px 8px rgba(0,0,0,0.4)',
    ].join(';');
    btn.onmouseover = function () { this.style.background = '#3D3B38'; };
    btn.onmouseout  = function () { this.style.background = '#2E2C2A'; };
    btn.onclick = function () {
        // Try the known Streamlit collapsed-control selectors in order
        var toggle =
            p.querySelector('[data-testid="stSidebarCollapsedControl"] button') ||
            p.querySelector('[data-testid="stSidebarNavCollapseIcon"]')          ||
            p.querySelector('section[data-testid="stSidebar"] button');
        if (toggle) toggle.click();
    };
    p.body.appendChild(btn);

    // Poll the sidebar width every 300 ms and show/hide our button
    setInterval(function () {
        var sidebar = p.querySelector('section[data-testid="stSidebar"]');
        if (!sidebar) return;
        var collapsed = sidebar.offsetWidth < 10 ||
                        sidebar.getAttribute('aria-expanded') === 'false';
        btn.style.display = collapsed ? 'block' : 'none';
    }, 300);

    // Hide Streamlit Cloud branding injected after page load
    var HIDE_SELECTORS = [
        '[data-testid="stToolbar"]',
        '[data-testid="stDecoration"]',
        '[data-testid="stHeader"]',
        '[data-testid="stFooter"]',
        '[data-testid="stToolbarActionButton"]',
        '[data-testid="stStatusWidget"]',
        '#MainMenu',
        'header',
        'footer',
    ];
    function hideBreanding() {
        HIDE_SELECTORS.forEach(function(sel) {
            p.querySelectorAll(sel).forEach(function(el) {
                el.style.setProperty('display', 'none', 'important');
            });
        });
        // Hide any element whose class contains 'viewerBadge' or 'badge'
        p.querySelectorAll('[class*="viewerBadge"],[class*="BadgeContainer"],[class*="badge_container"]').forEach(function(el) {
            el.style.setProperty('display', 'none', 'important');
        });
    }
    hideBreanding();
    // Re-run whenever Streamlit Cloud injects new nodes
    new MutationObserver(hideBreanding).observe(p.body, { childList: true, subtree: true });
}());
</script>
""",
    height=0,
    scrolling=False,
)


class DashboardBuilderApp:
    """
    Main application class.
    Coordinates between UI components and services.
    """

    def __init__(self):
        """Initialize the application."""
        # Initialize session state
        self._init_session_state()

        # Initialize services
        self._init_services()

        # Initialize chart factory
        self.chart_factory = ChartFactory()

    def _init_session_state(self) -> None:
        """Initialize Streamlit session state with default values."""
        # Run the original session state initializer first
        init_session_state()

        # Ensure auth-specific keys are present
        auth_defaults = {
            "user": None,
            "_services_ready": False,
        }
        for key, value in auth_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def _init_services(self) -> None:
        """
        Initialize application services once per Streamlit session and reuse
        them across reruns. Services are cached in st.session_state to avoid
        re-running DB init (Base.metadata.create_all) on every button click.
        """
        if not st.session_state.get("_services_ready"):
            db_ok = False
            try:
                init_database()
                db_ok = True
            except Exception as e:
                st.warning(f"Database connection issue: {e}")

            user_repo = UserRepositoryImpl()
            jwt_handler = JWTHandler()

            st.session_state.auth_service = AuthService(user_repo, None, jwt_handler)
            st.session_state._db_auth_ok = db_ok
            st.session_state._services_ready = True

        self.auth_service = st.session_state.auth_service

        user = st.session_state.get("user")
        current_user_id = str(user.user_id) if user else None

        # Build (or rebuild) analysis_service whenever:
        # - it hasn't been created yet, OR
        # - the logged-in user changed (e.g. after login the pre-login
        #   "anonymous" service is still cached and must be replaced)
        cached_uid = st.session_state.get("_analysis_service_user_id")
        if "analysis_service" not in st.session_state or cached_uid != current_user_id:
            from infrastructure.repositories.analysis_repository import (
                SupabaseAnalysisRepository,
            )
            # Only connect to Supabase when we have a real UUID user_id.
            # Without a user, analyses are ephemeral (in-memory only).
            repository = SupabaseAnalysisRepository(user_id=current_user_id or "")

            st.session_state.analysis_service = AnalysisService(repository)
            st.session_state._analysis_service_user_id = current_user_id
            st.session_state.analysis_service.initialize_session(
                get_state("session_data")
            )
            # Hydrate the in-memory session from Supabase
            if current_user_id:
                saved = repository.list_all()
                session = st.session_state.analysis_service.get_session()
                existing_ids = {a.id for a in session.analyses}
                for analysis in saved:
                    if analysis.id not in existing_ids:
                        session.analyses.append(analysis)

        if "data_service" not in st.session_state:
            st.session_state.data_service = DataService()

        if "export_service" not in st.session_state:
            st.session_state.export_service = ExportService()

        if "pdf_generator" not in st.session_state:
            st.session_state.pdf_generator = PDFGenerator()

    @property
    def analysis_service(self) -> AnalysisService:
        return st.session_state.analysis_service

    @property
    def data_service(self) -> DataService:
        return st.session_state.data_service

    @property
    def export_service(self) -> ExportService:
        return st.session_state.export_service

    @property
    def pdf_generator(self) -> PDFGenerator:
        return st.session_state.pdf_generator

    def _render_login_flow(self) -> None:
        """Render the login/registration flow."""

        def on_login_success(user: User, session: Any) -> None:
            st.session_state.user = user
            # Force analysis_service to be recreated with the real user_id.
            # It was built before login with user_id="anonymous", so every
            # save/load was a no-op.  Clearing it here causes _init_services
            # to rebuild it with the authenticated user on the next rerun.
            st.session_state.pop("analysis_service", None)

        render_login_page(self.auth_service, on_login_success)

    def run(self) -> None:
        """Run the main application."""
        # Check authentication before rendering the app
        if not st.session_state.user:
            self._render_login_flow()
            return

        # 1. Renderizar Sidebar com a ligação correta para o processamento
        render_sidebar(
            analysis_service=self.analysis_service,
            on_new_analysis=self._on_new_analysis,
            on_select_analysis=self._on_select_analysis,
            on_settings_click=lambda: set_state("show_settings", True),
            on_upload=self._process_uploaded_file,
            on_delete_analysis=self._on_delete_analysis,
        )

        # 2. Renderizar cabeçalho
        self._render_header()

        # 3. Verificar o estado atual para decidir o que mostrar
        current_analysis = self.analysis_service.get_current_analysis()

        if get_state("show_column_mapper"):
            # Mostra a tela de mapeamento (Task 2)
            self._render_mapping_screen()
        elif not current_analysis:
            # Mostra tela de boas-vindas
            render_welcome_screen(self._on_new_analysis)
            self._render_uploader_dialog()
        else:
            # Mostra o layout principal
            self._render_main_layout()

        # Modais de interface
        if get_state("show_settings"):
            self._render_settings_modal()

        if get_state("show_export"):
            self._render_export_dialog()
            set_state("show_export", False)

        # Notificações do sistema
        self._handle_notifications()

    def _render_header(self) -> None:
        """Topbar com nome da análise editável e ações."""
        current_analysis = self.analysis_service.get_current_analysis()

        col_name, col_save, col_export = st.columns([5, 1, 1])

        with col_name:
            if current_analysis:
                new_name = st.text_input(
                    "nome",
                    value=current_analysis.name,
                    label_visibility="collapsed",
                    key=f"analysis_name_{current_analysis.id}",
                    placeholder="Nome da análise…",
                )
                if new_name and new_name != current_analysis.name:
                    self.analysis_service.rename_analysis(current_analysis.id, new_name)
                    st.rerun()
            else:
                st.markdown(
                    "<span style='font-size:1.1rem;font-weight:700;color:#1E293B;'>"
                    "📊 Smart BI</span>",
                    unsafe_allow_html=True,
                )

        with col_save:
            if current_analysis:
                if st.button("💾 Salvar", width='stretch'):
                    self.analysis_service.save_current_analysis()
                    st.toast("Análise salva!", icon="✅")

        with col_export:
            if current_analysis:
                if st.button("📤 Exportar", type="primary", width='stretch'):
                    set_state("show_export", True)
                    st.rerun()

        st.markdown(
            "<hr style='border:none;border-top:1px solid #E2E8F0;margin:8px 0 16px;'/>",
            unsafe_allow_html=True,
        )

    def _render_main_layout(self) -> None:
        """Render the main application layout."""
        current_analysis = self.analysis_service.get_current_analysis()
        if not current_analysis:
            return

        current_slide = self.analysis_service.get_current_slide()

        col_main, col_widgets = st.columns([3, 1])

        with col_widgets:
            self._render_widget_sidebar(current_analysis)

        with col_main:
            # ── Canvas ───────────────────────────────────────────────────────
            render_canvas(
                slide=current_slide,
                data_service=self.data_service,
                analysis_id=current_analysis.id,
                on_update_visualization=self._on_update_visualization,
                on_delete_visualization=self._on_delete_visualization,
                on_add_comment=self._on_add_comment,
                analysis=current_analysis,
                on_update_measures=self._on_update_measures,
            )

            # ── Slide navigator ───────────────────────────────────────────────
            if current_analysis.slides:
                render_slide_navigator(
                    slides=current_analysis.slides,
                    current_slide_id=current_slide.id if current_slide else None,
                    on_slide_change=self._on_slide_change,
                    on_add_slide=self._on_add_slide,
                    on_delete_slide=self._on_delete_slide,
                )

    def _render_mapping_screen(self) -> None:
        """Tela de Mapeamento de Colunas com design em cards."""
        st.markdown(
            "<h2 style='color:#1E293B;font-weight:700;margin-bottom:4px;'>🛠️ Configurar Colunas</h2>"
            "<p style='color:#64748B;margin-bottom:24px;'>Confirme ou ajuste os tipos detectados automaticamente.</p>",
            unsafe_allow_html=True,
        )
        df = get_state("temp_df")
        schema = get_state("temp_schema")

        if df is not None:
            mapping = render_column_mapper(df, schema=schema)

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            if st.button("✓  Validar e continuar", type="primary", width='stretch'):
                _tipo_map = {
                    "Numérico": ColumnType.NUMERIC,
                    "Data/Hora": ColumnType.DATETIME,
                    "Categoria": ColumnType.CATEGORICAL,
                    "Texto": ColumnType.TEXT,
                }
                tipos_alvo = {k: _tipo_map[v] for k, v in mapping.items() if v in _tipo_map}
                df_final = self.data_service.validate_and_cast_types(df, tipos_alvo)

                # Criar análise e gerar schema a partir do DataFrame já tipado
                name = get_state("pending_upload_name")
                analysis = self.analysis_service.create_analysis(name)

                from domain.entities import DataSchema
                analysis.data_schema = DataSchema.from_polars(df_final)

                # Attach S3 storage_path so the repository can reload the
                # XLSX automatically on future cold-cache misses.
                storage_path = get_state("temp_storage_path")
                if storage_path:
                    analysis.file_path = storage_path

                # Salvar dados no cache + Parquet local + Supabase
                self.data_service.store_data(analysis.id, df_final)
                self.analysis_service.save_current_analysis()

                # Limpeza de estado e retorno ao Dashboard
                set_state("show_column_mapper", False)
                set_state("temp_df", None)
                set_state("temp_schema", None)
                set_state("temp_storage_path", None)
                st.success("Dados validados! Os gráficos foram liberados.")
                st.rerun()

    def _render_widget_sidebar(self, current_analysis) -> None:
        """Painel direito com palette vertical de visuais + preview de dados."""
        if not current_analysis or not current_analysis.data_schema:
            return

        st.markdown(
            "<div style='font-size:.70rem;font-weight:600;letter-spacing:.08em;"
            "color:#B0ABA4;text-transform:uppercase;margin-bottom:10px;'>Adicionar visual</div>",
            unsafe_allow_html=True,
        )

        from presentation.widgets import render_widget_palette
        render_widget_palette(
            current_analysis.data_schema,
            self._start_visualization_config,
            measures=list(getattr(current_analysis, "measures", None) or []),
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        df = self.data_service.get_cached_data(current_analysis.id)
        if df is not None:
            with st.expander("📋 Dados", expanded=False):
                render_data_preview(current_analysis.data_schema, df)

        # Modais de config (abrem sobre o canvas via @st.dialog)
        if get_state("configuring_new_viz"):
            self._render_config_dialog()

        if get_state("editing_viz_id"):
            self._render_edit_config_dialog()

    def _render_uploader_dialog(self) -> None:
        """Render file uploader dialog."""
        if get_state("show_uploader"):
            with st.expander("📂 Upload XLSX File", expanded=True):
                uploaded_file = st.file_uploader(
                    "Select an Excel file",
                    type=["xlsx", "xls"],
                    help="Upload an Excel file to start a new analysis",
                )

                if uploaded_file is not None:
                    name_input = st.text_input(
                        "Analysis Name", value=uploaded_file.name.rsplit(".", 1)[0]
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                            "📁 Load File", type="primary", width='stretch'
                        ):
                            self._process_uploaded_file(uploaded_file, name_input)

                    with col2:
                        if st.button("✗ Cancel", width='stretch'):
                            set_state("show_uploader", False)
                            st.rerun()

    def _render_settings_modal(self) -> None:
        """Render settings modal."""
        with st.expander("⚙️ Settings", expanded=True):
            render_settings_modal(
                current_settings=self.analysis_service.get_settings(),
                on_save=self._on_save_settings,
            )
            if st.button("Close Settings"):
                set_state("show_settings", False)
                st.rerun()

    def _render_export_dialog(self) -> None:
        """Abre o modal @st.dialog de exportação para PDF."""
        current_analysis = self.analysis_service.get_current_analysis()
        if current_analysis:
            render_export_dialog(
                analysis=current_analysis,
                on_export=self._on_export,
            )

    def _handle_notifications(self) -> None:
        """Exibe notificações via st.toast e limpa o estado."""
        notification = get_state("notification")
        if notification:
            message, level = notification
            icon_map = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
            st.toast(message, icon=icon_map.get(level, "ℹ️"))
            set_state("notification", None)

    # Callback methods

    def _on_new_analysis(self) -> None:
        """Handle new analysis creation."""
        set_state("show_uploader", True)

    def _process_uploaded_file(self, uploaded_file, name: str) -> None:
        try:
            file_bytes = uploaded_file.getvalue()
            schema, df = self.data_service.load_excel_from_bytes(
                file_bytes, uploaded_file.name, "temp_id"
            )

            # Upload to S3 immediately so the file survives after the column
            # mapper confirmation step and is available for future cold-cache
            # reloads.  Fail gracefully — local-only mode still works.
            storage_path = None
            user_id = getattr(st.session_state.get("user"), "user_id", "local")
            try:
                from infrastructure.storage import get_s3_client
                s3 = get_s3_client()
                storage_path = s3.upload_file(
                    file_data=file_bytes,
                    filename=uploaded_file.name,
                    user_id=str(user_id),
                )
            except Exception as s3_err:
                import logging
                logging.getLogger(__name__).warning(f"S3 upload skipped: {s3_err}")

            set_state("temp_df", df)
            set_state("temp_schema", schema)
            set_state("temp_storage_path", storage_path)
            set_state("show_column_mapper", True)
            set_state("pending_upload_name", name)
            set_state("pending_file_name", uploaded_file.name)

            st.rerun()
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

    def _on_select_analysis(self, analysis_id: str) -> None:
        """Handle analysis selection; pre-warms the data cache from S3 if needed."""
        self.analysis_service.set_current_analysis(analysis_id)

        # If data not in any local cache, try to reload from S3 immediately so
        # the canvas doesn't show "No data loaded" on the first render.
        if self.data_service.get_cached_data(analysis_id) is None:
            storage_path = None
            repo = self.analysis_service.repository
            if hasattr(repo, "get_storage_path"):
                storage_path = repo.get_storage_path(analysis_id)
            elif hasattr(repo, "_db"):
                # FileAnalysisRepository — check analysis.file_path directly
                analysis = self.analysis_service.get_current_analysis()
                if analysis:
                    storage_path = getattr(analysis, "file_path", None)
            if storage_path:
                self.data_service.get_cached_data(analysis_id, storage_path=storage_path)

        st.rerun()

    def _on_delete_analysis(self, analysis_id: str) -> None:
        """Delete an analysis and reset current selection if it was active."""
        current = self.analysis_service.get_current_analysis()
        self.analysis_service.delete_analysis(analysis_id)
        if current and current.id == analysis_id:
            st.session_state.pop("current_analysis_id", None)
        st.rerun()

    def _on_save_settings(self, settings: Dict[str, Any]) -> None:
        """Handle settings save."""
        self.analysis_service.update_settings(settings)

    def _start_visualization_config(self, viz_type: VisualizationType) -> None:
        """Start configuration for a new visualization."""
        set_state("configuring_new_viz", viz_type)

    def _render_config_dialog(self) -> None:
        """Abre o modal @st.dialog para criar uma NOVA visualização."""
        viz_type = get_state("configuring_new_viz")
        current_analysis = self.analysis_service.get_current_analysis()

        if not viz_type or not current_analysis or not current_analysis.data_schema:
            return

        # Limpa o trigger ANTES de abrir o dialog — assim o X fecha sem reabrir
        set_state("configuring_new_viz", None)

        # MEASURES → abre o dialog dedicado (não cria card no slide)
        if viz_type == VisualizationType.MEASURES:
            from presentation.widgets import render_measures_dialog
            measures = list(getattr(current_analysis, "measures", None) or [])
            all_cols = (
                [c.name for c in current_analysis.data_schema.columns]
                if current_analysis.data_schema else []
            )

            def on_save_measures(updated: list):
                self._on_update_measures(updated)
                st.rerun()

            def on_cancel_measures():
                st.rerun()

            render_measures_dialog(
                measures=measures,
                all_cols=all_cols,
                on_save=on_save_measures,
                on_cancel=on_cancel_measures,
            )
            return

        from presentation.widgets import render_visualization_config_dialog

        def on_save(config):
            self._create_visualization_with_config(viz_type, config)
            st.rerun()

        def on_cancel():
            st.rerun()

        render_visualization_config_dialog(
            viz_type=viz_type,
            data_schema=self._get_effective_schema(current_analysis),
            on_save=on_save,
            on_cancel=on_cancel,
            is_new=True,
        )

    def _render_edit_config_dialog(self) -> None:
        """Abre o modal @st.dialog para editar uma visualização existente."""
        viz_id = get_state("editing_viz_id")
        slide_id = get_state("editing_slide_id")

        if not viz_id:
            return

        current_analysis = self.analysis_service.get_current_analysis()
        if not current_analysis or not current_analysis.data_schema:
            return

        viz = None
        for slide in current_analysis.slides:
            for v in slide.visualizations:
                if v.id == viz_id:
                    viz = v
                    break

        if not viz or not viz.config:
            set_state("editing_viz_id", None)
            set_state("editing_slide_id", None)
            return

        # Limpa o trigger ANTES de abrir o dialog — assim o X fecha sem reabrir
        set_state("editing_viz_id", None)
        set_state("editing_slide_id", None)

        from presentation.widgets import render_visualization_config_dialog

        def on_save(new_config):
            self.analysis_service.update_visualization(
                slide_id, viz_id, config=new_config
            )
            self.analysis_service.save_current_analysis()
            st.toast("✓ Visualização atualizada!")
            st.rerun()

        def on_cancel():
            st.rerun()

        render_visualization_config_dialog(
            viz_type=viz.config.visualization_type,
            data_schema=self._get_effective_schema(current_analysis),
            existing_config=viz.config,
            on_save=on_save,
            on_cancel=on_cancel,
            is_new=False,
        )

    def _create_visualization_with_config(
        self, viz_type: VisualizationType, config: VisualizationConfig
    ) -> None:
        """Create a visualization with the specified configuration."""
        current_slide = self.analysis_service.get_current_slide()
        current_analysis = self.analysis_service.get_current_analysis()

        if not current_slide or not current_analysis:
            return

        # Add visualization with the config
        viz = self.analysis_service.add_visualization(current_slide.id, config)

        if viz:
            # Store data snapshot for tables
            df = self.data_service.get_cached_data(current_analysis.id)
            if df is not None and viz_type == VisualizationType.TABLE:
                all_cols = current_analysis.data_schema.get_column_names()
                data = df.head(100).to_pandas().to_dict(orient="records")
                viz.data_snapshot = {"data": data, "columns": all_cols[:10]}

            self.analysis_service.save_current_analysis()

        # Clear config state
        set_state("configuring_new_viz", None)
        st.success(f"✓ Added {viz_type.value.replace('_', ' ').title()}")
        st.rerun()

    def _cancel_config(self) -> None:
        """Cancel the configuration dialog."""
        set_state("configuring_new_viz", None)
        set_state("editing_viz_id", None)
        set_state("editing_slide_id", None)
        st.rerun()

    def _on_add_visualization(self, viz_type: VisualizationType) -> None:
        """Start adding a new visualization - shows config dialog."""
        set_state("configuring_new_viz", viz_type)

    def _on_update_visualization(
        self, slide_id: str, viz_id: str, config: VisualizationConfig
    ) -> None:
        """Handle visualization update."""
        self.analysis_service.update_visualization(slide_id, viz_id, config=config)

    def _on_delete_visualization(self, slide_id: str, viz_id: str) -> None:
        """Handle visualization deletion."""
        self.analysis_service.delete_visualization(slide_id, viz_id)
        st.success("Visualization deleted")
        st.rerun()

    def _on_add_comment(self, slide_id: str, viz_id: str, comment: str) -> None:
        """Handle adding a comment."""
        self.analysis_service.update_visualization(slide_id, viz_id, comment=comment)

    def _on_update_measures(self, measures: list) -> None:
        """Atualiza as medidas calculadas da análise corrente e salva."""
        current_analysis = self.analysis_service.get_current_analysis()
        if current_analysis:
            current_analysis.measures = measures
            self.analysis_service.save_current_analysis()

    def _get_effective_schema(self, analysis):
        """Retorna o DataSchema da análise enriquecido com as medidas como colunas NUMERIC."""
        schema = analysis.data_schema
        if not schema:
            return schema
        measures = getattr(analysis, "measures", None) or []
        if not measures:
            return schema
        existing_names = {c.name for c in schema.columns}
        extra = []
        for m in measures:
            name = (m.get("name") or "").strip()
            if name and name not in existing_names:
                from domain.entities import Column
                extra.append(Column(name=name, data_type=ColumnType.NUMERIC))
        if not extra:
            return schema
        from domain.entities import DataSchema
        return DataSchema(
            columns=list(schema.columns) + extra,
            row_count=schema.row_count,
            file_name=schema.file_name,
            file_size=schema.file_size,
        )

    def _on_slide_change(self, slide_id: str) -> None:
        """Handle slide change."""
        self.analysis_service.set_current_slide(slide_id)

    def _on_add_slide(self) -> None:
        """Handle adding a new slide."""
        slide = self.analysis_service.add_slide()
        if slide:
            st.success(f"Added {slide.title}")
            st.rerun()

    def _on_delete_slide(self, slide_id: str) -> None:
        """Handle slide deletion."""
        self.analysis_service.delete_slide(slide_id)
        st.success("Slide deleted")
        st.rerun()

    def _apply_filters_to_df(self, df: pl.DataFrame, viz_id: str) -> pl.DataFrame:
        """Aplica os filtros salvos em session_state para a visualização ao df."""
        filters = st.session_state.get(f"filters_{viz_id}", [])
        result = df
        for f in filters:
            col, op, val = f.get("col"), f.get("op"), f.get("val")
            if not col or col not in result.columns:
                continue
            try:
                c = pl.col(col)
                dtype = result.schema.get(col)
                numeric_types = (
                    pl.Float64, pl.Float32, pl.Int64, pl.Int32,
                    pl.Int16, pl.Int8, pl.UInt64, pl.UInt32,
                )

                def _cast(v):
                    if dtype in (pl.Float64, pl.Float32):
                        try: return float(v)
                        except: return v
                    if dtype in (pl.Int64, pl.Int32, pl.Int16, pl.Int8, pl.UInt64, pl.UInt32):
                        try: return int(float(v))
                        except: return v
                    return v

                if op == "is_null":
                    result = result.filter(c.is_null())
                elif op == "is_not_null":
                    result = result.filter(c.is_not_null())
                elif op == "in":
                    vals = [v.strip() for v in str(val).split(",") if v.strip()]
                    result = result.filter(c.cast(pl.String).is_in(vals))
                elif op == "contains":
                    result = result.filter(c.cast(pl.String).str.contains(str(val), literal=True))
                elif op == "starts_with":
                    result = result.filter(c.cast(pl.String).str.starts_with(str(val)))
                elif op == "eq":
                    if isinstance(val, list):
                        result = result.filter(c.cast(pl.String).is_in([str(v) for v in val]))
                    else:
                        result = result.filter(c == _cast(val))
                elif op == "ne":
                    result = result.filter(c != _cast(val))
                elif op == "gt":
                    result = result.filter(c > _cast(val))
                elif op == "lt":
                    result = result.filter(c < _cast(val))
                elif op == "gte":
                    result = result.filter(c >= _cast(val))
                elif op == "lte":
                    result = result.filter(c <= _cast(val))
            except Exception:
                pass
        return result

    def _on_export(self, analysis: Analysis, options: Dict[str, Any]) -> Optional[str]:
        """Exporta a análise para PDF aplicando filtros e medidas como estão na tela."""
        try:
            df_base = self.data_service.get_cached_data(analysis.id)
            if df_base is None:
                st.error("Sem dados carregados para exportar.")
                return None

            # Aplica medidas calculadas
            measures = getattr(analysis, "measures", None) or []
            if measures:
                try:
                    df_base = self.data_service.compute_measures(df_base, measures)
                except Exception:
                    pass

            chart_images: Dict[str, bytes] = {}
            table_data: Dict[str, Dict] = {}
            metric_data: Dict[str, Dict] = {}

            for slide in analysis.slides:
                for viz in slide.visualizations:
                    if not viz.config:
                        continue
                    vtype = viz.config.visualization_type

                    # Painel de medidas não vai para o PDF
                    if vtype == VisualizationType.MEASURES:
                        continue

                    # Aplica filtros da sessão específicos desta viz
                    df_viz = self._apply_filters_to_df(df_base, viz.id)

                    if vtype == VisualizationType.TABLE:
                        config = viz.config
                        if config.y_columns:
                            cols = [c for c in config.y_columns if c in df_viz.columns]
                        elif config.x_column or config.y_column:
                            cols = [
                                c for c in [config.x_column, config.y_column, config.color_column]
                                if c and c in df_viz.columns
                            ]
                        else:
                            cols = list(df_viz.columns[:10])
                        if cols:
                            tdf = df_viz.select(cols).head(100)
                            table_data[viz.id] = {
                                "columns": cols,
                                "data": tdf.to_pandas().to_dict(orient="records"),
                                "title": config.title or "Tabela",
                            }

                    elif vtype == VisualizationType.METRIC_CARD:
                        config = viz.config
                        if config.y_column and config.y_column in df_viz.columns:
                            col = df_viz[config.y_column]
                            agg = config.aggregation or "sum"
                            if agg == "mean":
                                val = col.mean()
                            elif agg == "count":
                                val = col.count()
                            elif agg == "min":
                                val = col.min()
                            elif agg == "max":
                                val = col.max()
                            else:
                                val = col.sum()
                            metric_data[viz.id] = {
                                "value": val,
                                "column": config.y_column,
                                "agg": agg,
                                "title": config.title or config.y_column,
                            }

                    else:
                        try:
                            fig = self.chart_factory.create_chart(df_viz, viz.config)
                            try:
                                img_bytes = self.chart_factory.export_figure_to_bytes(
                                    fig, format="png", scale=2.0
                                )
                            except Exception:
                                img_bytes = self.chart_factory.render_to_image_bytes(
                                    df_viz, viz.config
                                )
                            chart_images[viz.id] = img_bytes
                        except Exception as e:
                            print(f"Erro ao gerar imagem para {viz.id}: {e}")

            export_options = ExportOptions(
                format=options.get("format", "pdf"),
                paper_size=options.get("paper_size", "a4"),
                orientation=options.get("orientation", "portrait"),
                include_comments=options.get("include_comments", True),
                footer_text=options.get("footer_text", ""),
                file_name=options.get("file_name", ""),
                subtitle=options.get("subtitle", ""),
            )

            output_path = self.pdf_generator.generate_pdf(
                analysis,
                export_options,
                chart_images,
                table_data=table_data,
                metric_data=metric_data,
            )
            return output_path

        except Exception as e:
            st.error(f"Erro na exportação: {str(e)}")
            return None


def main():
    """Main entry point."""
    app = DashboardBuilderApp()
    app.run()


if __name__ == "__main__":
    main()
