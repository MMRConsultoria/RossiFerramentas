# app.py
import streamlit as st

st.set_page_config(page_title="Painel OS", page_icon="🧰", layout="wide")

# ========= CSS: abas estilo "pill" + inputs estilosos =========
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
.h2{ font-weight:800; color:#0f172a; margin: 0 0 4px; }
.caption{ color:#6b7280; margin-bottom:14px; }

.field{ margin-bottom:10px; }
.field label{ font-size:.92rem; color:#334155; font-weight:700; margin-bottom:6px; display:block; }
.input{
  border:1px solid #e5e7eb; border-radius:10px; padding:8px 10px; background:#f9fafb;
}
.row{ display:grid; grid-template-columns: 1.3fr .7fr 1fr; gap:12px; }
.row2{ display:grid; grid-template-columns: 1fr; gap:12px; }

.box{
  padding:12px; border:1px dashed #d1d5db; border-radius:12px; background:#f9fafb;
}
.badge{
  display:inline-flex; gap:8px; align-items:center; background:#eff6ff; color:#1d4ed8;
  border:1px solid #bfdbfe; border-radius:999px; padding:6px 12px; font-weight:700;
}
.btns{ display:flex; gap:10px; }
</style>
""", unsafe_allow_html=True)

# ========= abas =========
abas = st.tabs([
    "📋 Entrada/Saída OS",
    "📊 Relatório 1 (em desenvolvimento)",
    "📈 Relatório 2 (em desenvolvimento)",
    "⚙️ Configurações (em desenvolvimento)"
])

# ========= estado / callbacks p/ checkboxes exclusivas =========
def marcar_entrada():
    st.session_state.saida = False

def marcar_saida():
    st.session_state.entrada = False

# ========= ABA 1 =========
with abas[0]:
    st.markdown('<div class="wrapper"><div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="h2">🧰 Entrada/Saída OS</div>', unsafe_allow_html=True)
    st.markdown('<div class="caption">Preencha os campos e selecione o tipo do movimento.</div>', unsafe_allow_html=True)

    # form
    with st.form("form_os"):
        # —— linha 1: OS | Item | Máquina
        st.markdown('<div class="row">', unsafe_allow_html=True)
        os_ = st.text_input("OS", key="os", placeholder="Ex.: 9532")
        item = st.number_input("Item", key="item", min_value=0, step=1, format="%d")
        maq  = st.text_input("Máquina", key="maq", placeholder="Ex.: 6666666")
        st.markdown('</div>', unsafe_allow_html=True)

        # —— linha 2: Quantidade
        st.markdown('<div class="row2">', unsafe_allow_html=True)
        qtd = st.number_input("Quantidade", key="qtd", min_value=1, step=1, format="%d")
        st.markdown('</div>', unsafe_allow_html=True)

        # —— linha 3: Movimento (duas checkboxes exclusivas, ambas iniciam False)
        c1, c2 = st.columns([1,1])
        with c1:
            entrada = st.checkbox("Entrada", key="entrada", value=False, on_change=marcar_entrada)
        with c2:
            saida = st.checkbox("Saída", key="saida", value=False, on_change=marcar_saida)

        st.markdown('<div class="btns">', unsafe_allow_html=True)
        salvar = st.form_submit_button("💾 Salvar", use_container_width=False)
        limpar = st.form_submit_button("🧹 Limpar", use_container_width=False)
        st.markdown('</div>', unsafe_allow_html=True)

    # ações
    if limpar:
        for k in ("os","item","maq","qtd","entrada","saida"):
            if k in st.session_state: del st.session_state[k]
        st.experimental_rerun()

    if salvar:
        erros = []
        if not os_ or not os_.strip(): erros.append("Informe a **OS**.")
        if not maq or not maq.strip(): erros.append("Informe a **Máquina**.")
        if not (entrada or saida): erros.append("Selecione **Entrada** ou **Saída** (obrigatório).")

        if erros:
            for e in erros: st.error(e)
        else:
            movimento = "Entrada" if entrada else "Saída"
            registro = {
                "OS": os_.strip(),
                "Item": int(item),
                "Quantidade": int(qtd),
                "Máquina": maq.strip(),
                "Movimento": movimento
            }
            st.success("✅ Registro salvo localmente (pronto para integrar ao Google Sheets).")
            st.markdown('<div class="box">', unsafe_allow_html=True)
            st.json(registro)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="badge">Movimento selecionado: <b>{movimento}</b></div>',
                unsafe_allow_html=True
            )

    st.markdown('</div></div>', unsafe_allow_html=True)

# ========= abas placeholder =========
with abas[1]:
    st.info("🚧 Em desenvolvimento...")

with abas[2]:
    st.info("🚧 Em desenvolvimento...")

with abas[3]:
    st.info("🚧 Em desenvolvimento...")
