import streamlit as st

st.set_page_config(page_title="Painel OS", page_icon="🧰", layout="wide")

# ========= Guardas de sessão =========
if not st.session_state.get("acesso_liberado"):
    st.stop()

ROLE = st.session_state.get("role", "basic")
TABS_PERMITIDAS = st.session_state.get("tabs_permitidas", ["entrada_saida_os"])

# ========= CSS (abas estilo pill + cartão) =========
st.markdown("""
<style>
.stTabs [role="tablist"]{ gap:10px; border-bottom:1px solid #e5e7eb; }
.stTabs [role="tab"]{
  background:#f3f4f6; padding:8px 20px; border-radius:8px 8px 0 0;
  font-weight:600; color:#374151; border:1px solid transparent;
}
.stTabs [aria-selected="true"]{ background:#2563eb; color:#fff!important; border-color:#2563eb; }
.stTabs [role="tab"]:hover{ background:#e0e7ff; color:#1e3a8a; }

.wrapper{ max-width:980px; margin:10px auto; }
.card{
  background:#ffffff; border:1px solid #e5e7eb; border-radius:14px;
  box-shadow:0 12px 24px rgba(0,0,0,.06); padding:18px 18px 20px;
}
.h2{ font-weight:800; color:#0f172a; margin:0 0 6px; }
.caption{ color:#6b7280; margin-bottom:14px; }

.row{ display:grid; grid-template-columns: 1fr 1fr 1fr; gap:12px; }
.row2{ display:grid; grid-template-columns: 1fr; gap:12px; }

.box{ padding:12px; border:1px dashed #d1d5db; border-radius:12px; background:#f9fafb; }
.badge{
  display:inline-flex; gap:8px; align-items:center; background:#eff6ff; color:#1d4ed8;
  border:1px solid #bfdbfe; border-radius:999px; padding:6px 12px; font-weight:700;
}
.user-chip{
  position:fixed; top:10px; right:12px; z-index:9999;
  background:#ecfeff; border:1px solid #a5f3fc; color:#155e75;
  padding:6px 10px; border-radius:999px; font-weight:700; font-size:.9rem;
}
</style>
""", unsafe_allow_html=True)

# badge do usuário
st.markdown(f'<div class="user-chip">👤 {st.session_state.get("usuario_logado","")} · {ROLE}</div>', unsafe_allow_html=True)

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

# ========= Abas conforme permissão =========
ALL_TABS = [
    "📋 Entrada/Saída OS",
    "📊 Relatório 1 (em desenvolvimento)",
    "📈 Relatório 2 (em desenvolvimento)",
    "⚙️ Configurações (em desenvolvimento)"
]
if ROLE == "admin" and ("all" in TABS_PERMITIDAS):
    tab_labels = ALL_TABS
else:
    tab_labels = [ALL_TABS[0]]

tabs = st.tabs(tab_labels)

# ========= Aba 1: Entrada/Saída OS (sempre visível) =========
with tabs[0]:
    st.markdown('<div class="wrapper"><div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="h2">🧰 Entrada/Saída OS</div>', unsafe_allow_html=True)
    #st.markdown('<div class="caption">Preencha os dados da OS e selecione o tipo do movimento.</div>', unsafe_allow_html=True)

    with st.form("form_os"):
        # Linha 1: OS | Item | Máquina
        st.markdown('<div class="row">', unsafe_allow_html=True)
        os_  = st.number_input("OS", min_value=0, step=1, format="%d", key="os")
        item = st.number_input("Item", min_value=0, step=1, format="%d", key="item")
        maq  = st.text_input("Máquina", placeholder="Ex.: 6666666", key="maq")
        st.markdown('</div>', unsafe_allow_html=True)

        # Linha 2: Quantidade
        st.markdown('<div class="row2">', unsafe_allow_html=True)
        qtd  = st.number_input("Quantidade", min_value=1, step=1, format="%d", key="qtd")
        st.markdown('</div>', unsafe_allow_html=True)

        # Movimento (radio obrigatório)
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
        if mov == "Selecione...":
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
            st.success("✅ Registro salvo localmente (UI pronta — integração com Google Sheets vem depois).")
            st.markdown('<div class="box">', unsafe_allow_html=True)
            st.json(registro)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="badge">Movimento: <b>{st.session_state["mov"]}</b></div>', unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

# ========= Abas extras (apenas admin) =========
if ROLE == "admin" and ("all" in TABS_PERMITIDAS) and len(tabs) > 1:
    with tabs[1]:
        st.info("🚧 Relatório 1 em desenvolvimento...")
    with tabs[2]:
        st.info("🚧 Relatório 2 em desenvolvimento...")
    with tabs[3]:
        st.info("🚧 Configurações em desenvolvimento...")
