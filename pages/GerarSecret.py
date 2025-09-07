import streamlit as st
import json

st.set_page_config(page_title="Gerar Secret Google", page_icon="🔐")

st.title("🔐 Gerar STRING de credencial (Google Service Account)")
st.caption("Cole abaixo o JSON **exatamente** como o Google fornece (com múltiplas linhas).")

raw = st.text_area("JSON original do Google", height=260, placeholder='{\n  "type": "service_account",\n  ...\n}')

if st.button("Gerar STRING do secret", type="primary"):
    try:
        # 1) Valida o JSON
        obj = json.loads(raw)
        # 2) Converte para uma STRING escapada (um-liner, com \\n e \")
        secret_string = json.dumps(obj)
        st.success("Pronto! Copie a STRING abaixo para o seu secrets.")
        st.code(f'GOOGLE_SERVICE_ACCOUNT = {json.dumps(secret_string)}', language="python")
        st.caption("Dica: Se quiser outro nome (ex.: GOOGLE_SERVICE_ACCOUNT_ACESSOS), troque no lado esquerdo do =.")
    except Exception as e:
        st.error(f"JSON inválido: {e}")
