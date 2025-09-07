# app.py
import streamlit as st

st.set_page_config(page_title="Entrada/Saída OS", page_icon="🧰", layout="centered")

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
