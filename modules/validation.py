"""Sistema de validacao por etapas com botoes red->green.

Cada etapa do fluxo guarda um flag booleano em st.session_state:
- study_config_validated
- map_step_validated
- imports_step_validated
- pois_step_validated
- od_step_validated
- scenarios_step_validated

Quando o usuario clica no botao de validacao da etapa, o flag vira True
e o botao vermelho 'pendente' e substituido por uma badge verde.
Se o usuario altera algo da etapa depois, deve-se chamar invalidate()
para resetar o flag.
"""
from __future__ import annotations

import streamlit as st


STEPS = [
    ("study_config_validated", "Configuracao do estudo"),
    ("map_step_validated",     "Mapa"),
    ("imports_step_validated", "Importar arquivos"),
    ("pois_step_validated",    "Pontos de interesse"),
    ("od_step_validated",      "Matriz O-D"),
    ("scenarios_step_validated","Cenarios"),
]


def is_validated(key: str) -> bool:
    return bool(st.session_state.get(key, False))


def invalidate(key: str) -> None:
    """Reseta o status validado de uma etapa (volta para vermelho)."""
    if st.session_state.get(key, False):
        st.session_state[key] = False


def render_validation_button(
    state_key: str,
    pending_label: str,
    done_message: str,
    next_step_label: str = "",
    button_help: str = "",
) -> bool:
    """Botao vermelho (pendente) -> verde (validado).

    Retorna True na execucao em que o usuario validou nesta chamada.
    """
    validated = is_validated(state_key)

    # CSS injection para reforcar a cor vermelha do botao pendente
    # (alguns temas pintam type='primary' em laranja ao inves de vermelho).
    st.markdown(
        f"""
        <style>
        div[data-testid="stButton"] button[data-pending-key="{state_key}"] {{
            background-color: #D32F2F !important;
            border-color: #B71C1C !important;
            color: #FFFFFF !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    just_clicked = False
    if not validated:
        # botao vermelho
        col_btn, col_badge = st.columns([4, 1])
        with col_btn:
            if st.button(
                f"🔴  {pending_label}",
                type="primary",
                use_container_width=True,
                key=f"btn_validate_{state_key}",
                help=button_help or None,
            ):
                st.session_state[state_key] = True
                just_clicked = True
                st.rerun()
        with col_badge:
            st.markdown(
                "<div style='background:#FFCDD2;color:#B71C1C;padding:8px 12px;"
                "border-radius:6px;text-align:center;font-weight:700;"
                "border:1px solid #EF9A9A;'>⏳ PENDENTE</div>",
                unsafe_allow_html=True,
            )
    else:
        # estado verde
        col_msg, col_badge = st.columns([4, 1])
        with col_msg:
            full_msg = done_message
            if next_step_label:
                full_msg += f" **Próxima etapa: {next_step_label}.**"
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#C8E6C9 0%,#E8F5E9 100%);"
                f"border-left:5px solid #2E7D32;color:#1B5E20;padding:12px 16px;"
                f"border-radius:8px;font-weight:500;'>🟢 {full_msg}</div>",
                unsafe_allow_html=True,
            )
        with col_badge:
            st.markdown(
                "<div style='background:#C8E6C9;color:#1B5E20;padding:8px 12px;"
                "border-radius:6px;text-align:center;font-weight:700;"
                "border:1px solid #81C784;'>✅ VALIDADO</div>",
                unsafe_allow_html=True,
            )
        if st.button(
            "↩️ Reabrir esta etapa para alterar",
            key=f"btn_reopen_{state_key}",
            help="Volta a etapa para pendente. Use se quiser modificar algo.",
        ):
            st.session_state[state_key] = False
            st.rerun()

    return just_clicked


def progress_counts() -> tuple[int, int]:
    total = len(STEPS)
    done = sum(1 for key, _ in STEPS if is_validated(key))
    return done, total


def render_progress_bar(compact: bool = False) -> None:
    """Renderiza barra de progresso global.

    compact=True: versao curta para sidebar/topo.
    """
    done, total = progress_counts()
    if total == 0:
        return
    pct = done / total
    if compact:
        st.markdown(
            f"<div style='font-size:0.85rem;color:#555;'>"
            f"📋 <b>Progresso do estudo:</b> {done} de {total} etapas validadas"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.progress(pct)
    else:
        st.markdown("### 📋 Progresso do estudo")
        cols = st.columns(total)
        for i, (key, label) in enumerate(STEPS):
            with cols[i]:
                ok = is_validated(key)
                color = "#2E7D32" if ok else "#9E9E9E"
                bg = "#E8F5E9" if ok else "#F5F5F5"
                icon = "✅" if ok else "⏳"
                st.markdown(
                    f"<div style='text-align:center;background:{bg};"
                    f"border:1px solid {color};border-radius:8px;padding:6px;"
                    f"color:{color};font-size:0.78rem;font-weight:600;'>"
                    f"{icon}<br>{i+1}. {label}</div>",
                    unsafe_allow_html=True,
                )
        st.progress(pct)
        st.caption(f"**{done} de {total}** etapas validadas")
