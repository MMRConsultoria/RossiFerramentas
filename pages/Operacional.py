# pages/Operacional.py
import streamlit as st

st.set_page_config(page_title="Painel OS", page_icon="🧰", layout="wide")

# ========= Guardas de sessão =========
if not st.session_state.get("acesso_liberado"):
    st.stop()

ROLE = st.session_state.get("role", "basic")

# ========= CSS: abas estilo "pill" + limpeza de elementos vazios =========
st.markdown("""
<style>
.stTabs [role="tablist"]{ gap:10px; border-bottom:1px solid #e5e7eb; }
.stTabs [role="tab"]{
  background:#f3f4f6; padding:8px 20px; border-radius:8px 8px 0 0;
  font-weight:600; color:#374151; border:1px solid transparent;
}
.stTabs [aria-selected="true"]{ background:#2563eb; color:#fff!important; border-color:#2563eb; }
.stTabs [role="tab"]:hover{ background:#e0e7ff; color:#1e3a8a; }

/* Remover qualquer bloco vazio logo abaixo das abas */
.stTabs [role="tablist"] + div:empty { display:none !important; }

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

# ========= Aba 1: Entrada/Saída OS =========
with tabs[0]:
    with st.container(border=True):
        st.subheader("💼 Entrada/Saída OS")
        st.caption("Preencha os dados da OS e selecione o tipo do movimento.")

        with st.form("form_os"):
            # Linha 1: OS | Item | Máquina
            c1, c2, c3 = st.columns(3)
            with c1:
                os_  = st.number_input("🔑 OS", min_value=0, step=1, format="%d", key="os")
            with c2:
                item = st.number_input("Item", min_value=0, step=1, format="%d", key="item")
            with c3:
                maq  = st.text_input("Máquina", placeholder="Ex.: 6666666", key="maq")

            # Linha 2: Quantidade (à esquerda) + Movimento (à direita)
            qcol, mcol = st.columns([0.8, 1.2])
            with qcol:
                qtd  = st.number_input("Quantidade", min_value=1, step=1, format="%d", key="qtd")
            with mcol:
                mov = st.radio(
                    "Movimento",
                    options=["Entrada", "Saída"],
                    index=0, horizontal=True, key="mov"
                )

            col_a, col_b = st.columns([1,1])
            salvar = col_a.form_submit_button("💾 Salvar", use_container_width=True)
            limpar = col_b.form_submit_button("🧹 Limpar", use_container_width=True)

        if limpar:
            for k in ("os","item","maq","qtd","mov"):
                st.session_state.pop(k, None)
            st.rerun()

        if salvar:
            erros = []
            if os_ == 0: erros.append("Informe a **OS** (valor maior que zero).")
            if not st.session_state.get("maq") or not st.session_state["maq"].strip():
                erros.append("Informe a **Máquina**.")
            if st.session_state.get("mov") == "Selecione...":
                erros.append("Selecione **Entrada** ou **Saída**.")
            if erros:
                for e in erros: st.error(e)
            else:
                registro = {
                    "OS": int(st.session_state["os"]),
                    "Item": int(st.session_state["item"]),
                    "Quantidade": int(st.session_state["qtd"]),
                    "Máquina": st.session_state["maq"].strip(),
                    "Movimento": st.session_state["mov"],
                }
                st.success("✅ Registro salvo localmente.")
                st.markdown('<div class="box">', unsafe_allow_html=True)
                st.json(registro)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="badge">Movimento: <b>{st.session_state["mov"]}</b></div>', unsafe_allow_html=True)

# ========= Abas extras (somente admin) =========
if ROLE == "admin" and len(tabs) > 1:
    with tabs[1]:
        st.info("🚧 Relatório 1 em desenvolvimento...")
    with tabs[2]:
        st.info("🚧 Relatório 2 em desenvolvimento...")
    with tabs[3]:
        st.info("🚧 Configurações em desenvolvimento...")
