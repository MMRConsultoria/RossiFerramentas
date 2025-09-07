# app.py
import streamlit as st

st.set_page_config(page_title="Entrada/Saída OS", page_icon="🧰", layout="centered")
import streamlit as st

st.set_page_config(page_title="Painel OS", page_icon="🧰", layout="wide")

# ====== CSS customizado para abas estilo "pill" ======
st.markdown("""
<style>
/* container das abas */
.stTabs [role="tablist"] {
    gap: 10px;
    border-bottom: 1px solid #e5e7eb;
}

/* cada aba */
.stTabs [role="tab"] {
    background: #f3f4f6;
    padding: 8px 20px;
    border-radius: 6px 6px 0 0;
    font-weight: 600;
    color: #374151;
    border: 1px solid transparent;
}

/* aba ativa */
.stTabs [aria-selected="true"] {
    background: #2563eb;  /* azul */
    color: #fff !important;
    border-color: #2563eb;
}

/* hover */
.stTabs [role="tab"]:hover {
    background: #e0e7ff;
    color: #1e3a8a;
}
</style>
""", unsafe_allow_html=True)

# ====== Abas ======
abas = st.tabs([
    "📋 Entrada/Saída OS",
    "📊 Relatório 1 (em desenvolvimento)",
    "📈 Relatório 2 (em desenvolvimento)",
    "⚙️ Configurações (em desenvolvimento)"
])

# ====== Aba 1: Entrada/Saída OS ======
with abas[0]:
    st.markdown("## 🧰 Entrada/Saída OS")
    st.caption("Preencha os dados abaixo para registrar o movimento.")

    with st.form("form_os"):
        os_ = st.text_input("OS", placeholder="Ex.: 9532")
        item = st.number_input("Item", min_value=0, step=1, format="%d")
        qtd = st.number_input("Quantidade", min_value=1, step=1, format="%d")
        maq = st.text_input("Máquina", placeholder="Ex.: 6666666")
        mov = st.selectbox("Movimento", ["Entrada", "Saída"], index=1)

        salvar = st.form_submit_button("💾 Salvar")

    if salvar:
        if not os_ or not maq:
            st.error("⚠️ Preencha **OS** e **Máquina**.")
        else:
            registro = {
                "OS": os_,
                "Item": int(item),
                "Quantidade": int(qtd),
                "Máquina": maq,
                "Movimento": mov,
            }
            st.success("✅ Registro salvo localmente (pronto para enviar ao Google Sheets).")
            st.json(registro)

# ====== Abas genéricas ======
with abas[1]:
    st.info("🚧 Em desenvolvimento...")

with abas[2]:
    st.info("🚧 Em desenvolvimento...")

with abas[3]:
    st.info("🚧 Em desenvolvimento...")
