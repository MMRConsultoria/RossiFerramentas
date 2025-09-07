# pages/Operacional.py
import streamlit as st

st.set_page_config(page_title="Painel OS", page_icon="🧰", layout="wide")

# ========= Guardas de sessão =========
if not st.session_state.get("acesso_liberado"):
    st.stop()

ROLE = st.session_state.get("role", "basic")

# ========= CSS: abas estilo "pill" + limpeza =========
st.markdown("""
<style>
.stTabs [role="tablist"]{ gap:10px; border-bottom:1px solid #e5e7eb; }
.stTabs [role="tab"]{
  background:#f3f4f6; padding:8px 20px; border-radius:8px 8px 0 0;
  font-weight:600; color:#374151; border:1px solid transparent;
}
.stTabs [aria-selected="true"]{ background:#2563eb; color:#fff!important; border-color:#2563eb; }
.stTabs [role="tab"]:hover{ background:#e0e7ff; color:#1e3a8a; }
.stTabs [role="tablist"] + div:empty { display:none !important; } /* evita "pílula" fantasma */

.box{ padding:12px; border:1px dashed #d1d5db; border-radius:12px; background:#f9fafb; }
.badge{
  display:inline-flex; gap:8px; align-items:center; background:#eff6ff; color:#1d4ed8;
  border:1px solid #bfdbfe; border-radius:999px; padding:6px 12px; font-weight:700;
}
</style>
""", unsafe_allow_html=True)

# ========= JS: Enter = Tab (Shift+Enter volta) =========
st.markdown("""
<script>
(function() {
  function getFocusable() {
    const sel = 'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])';
    return Array.from(document.querySelectorAll(sel)).filter(el => el.offsetParent !== null);
  }
  function nextFocusable(current, forward=true) {
    const inputs = getFocusable();
    const idx = inputs.indexOf(current);
    if (idx === -1) return null;
    let nextIdx = forward ? idx + 1 : idx - 1;
    if (nextIdx >= inputs.length) nextIdx = 0;
    if (nextIdx < 0) nextIdx = inputs.length - 1;
    return inputs[nextIdx] || null;
  }
  document.addEventListener('keydown', function(e) {
    if (e.key !== 'Enter') return;
    const el = document.activeElement;
    if (!el) return;
    if (el.tagName === 'BUTTON' || el.type === 'submit') return;
    if (el.tagName === 'TEXTAREA' && e.shiftKey) return;
    e.preventDefault(); e.stopPropagation();
    const target = nextFocusable(el, !e.shiftKey);
    if (target) { target.focus(); try { target.select && target.select(); } catch(_) {} }
  }, true);
})();
</script>
""", unsafe_allow_html=True)

# ========= Tabs (admin vê todas, demais só a 1ª) =========
ALL_TABS = [
    "📋 Entrada/Saída OS",
    "📊 Relatório 1 (em desenvolvimento)",
    "📈 Relatório 2 (em desenvolvimento)",
    "⚙️ Configurações (em desenvolvimento)"
]
tabs = st.tabs(ALL_TABS if ROLE == "admin" else [ALL_TABS[0]])

# ========= Helpers =========
def campos_validos():
    os_ok   = st.session_state.get("os", 0) > 0
    maq_ok  = bool((st.session_state.get("maq") or "").strip())
    qtd_ok  = st.session_state.get("qtd", 0) >= 1
    mov_ok  = st.session_state.get("mov") in ("Entrada", "Saída")
    return os_ok and maq_ok and qtd_ok and mov_ok

def assinatura_atual():
    return (
        st.session_state.get("os"),
        st.session_state.get("item"),
        st.session_state.get("qtd"),
        (st.session_state.get("maq") or "").strip(),
        st.session_state.get("mov"),
    )

def montar_registro():
    return {
        "OS": int(st.session_state["os"]),
        "Item": int(st.session_state["item"]),
        "Quantidade": int(st.session_state["qtd"]),
        "Máquina": st.session_state["maq"].strip(),
        "Movimento": st.session_state["mov"],
    }

def processar_salvar(auto=False):
    registro = montar_registro()
    st.session_state["last_saved_sig"] = assinatura_atual()
    msg = "✅ Registro **auto-salvo**." if auto else "✅ Registro salvo."
    st.success(msg)
    st.markdown('<div class="box">', unsafe_allow_html=True)
    st.json(registro)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="badge">Movimento: <b>{registro["Movimento"]}</b></div>', unsafe_allow_html=True)

# ========= Aba 1: Entrada/Saída OS =========
with tabs[0]:
    with st.container(border=True):
        st.subheader("💼 Entrada/Saída OS")
        st.caption("Preencha os dados. O sistema pode **salvar automaticamente** ao concluir.")

        # Toggle de auto-salvar
        st.checkbox("Salvar automaticamente ao concluir", value=True, key="auto_save")

        # Linha 1: OS | Item | Máquina
        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input("🔑 OS", min_value=0, step=1, format="%d", key="os")
        with c2:
            st.number_input("Item", min_value=0, step=1, format="%d", key="item")
        with c3:
            st.text_input("Máquina", placeholder="Ex.: 6666666", key="maq")

        # Linha 2: Quantidade (esq) + Movimento (dir, sem seleção inicial)
        qcol, mcol = st.columns([0.8, 1.2])
        with qcol:
            st.number_input("Quantidade", min_value=1, step=1, format="%d", key="qtd")
        with mcol:
            # tenta criar radio sem seleção; se a sua versão não aceitar index=None,
            # use fallback com placeholder (tratado no except)
            try:
                st.radio("Movimento", ["Entrada", "Saída"], index=None, horizontal=True, key="mov")
            except TypeError:
                escolha = st.radio("Movimento", ["Selecione...", "Entrada", "Saída"], index=0, horizontal=True, key="mov")
                if escolha == "Selecione...":
                    st.session_state["mov"] = None

        # Botões
        col_a, col_b = st.columns([1, 1])
        salvar = col_a.button(
            "💾 Salvar",
            use_container_width=True,
            disabled=not campos_validos()
        )
        limpar = col_b.button("🧹 Limpar", use_container_width=True)

        # --- Ações ---
        if limpar:
            for k in ("os", "item", "maq", "qtd", "mov", "last_saved_sig"):
                st.session_state.pop(k, None)
            st.rerun()

        if salvar and campos_validos():
            processar_salvar(auto=False)

        # --- Auto-salvar quando todos os campos ficarem válidos ---
        if st.session_state.get("auto_save", True) and campos_validos():
            sig = assinatura_atual()
            if st.session_state.get("last_saved_sig") != sig:
                processar_salvar(auto=True)

# ========= Abas extras (somente admin) =========
if ROLE == "admin" and len(tabs) > 1:
    with tabs[1]:
        st.info("🚧 Relatório 1 em desenvolvimento...")
    with tabs[2]:
        st.info("🚧 Relatório 2 em desenvolvimento...")
    with tabs[3]:
        st.info("🚧 Configurações em desenvolvimento...")
