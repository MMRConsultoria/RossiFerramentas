import streamlit as st
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

st.set_page_config(page_title="Login | MMR Consultoria")

# =====================================
# CSS para esconder barra de botões do canto superior direito
# =====================================
st.markdown("""
    <style>
        [data-testid="stToolbar"] {
            visibility: hidden;
            height: 0%;
            position: fixed;
        }
    </style>
""", unsafe_allow_html=True)

# ✅ Captura segura dos parâmetros da URL
params = st.query_params
codigo_param = (params.get("codigo") or "").strip()
empresa_param = (params.get("empresa") or "").strip().lower()

# ✅ Bloqueia acesso direto sem parâmetros
if not codigo_param or not empresa_param:
    st.markdown("""
        <meta charset="UTF-8">
        <style>
        #MainMenu, header, footer, .stSidebar, .stToolbar, .block-container { display: none !important; }
        body {
          background-color: #ffffff;
          font-family: Arial, sans-serif;
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100vh;
          margin: 0;
        }
        </style>
        <div style="text-align: center;">
            <h2 style="color:#555;">🚫 Acesso Negado</h2>
            <p style="color:#888;">Você deve acessar pelo <strong>portal oficial da MMR Consultoria</strong>.</p>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# ========= Usuários (exemplo) =========
# Adicione 'role': 'admin' ou 'basic'
USUARIOS = [
    {"codigo": "3377", "Usuario": "João Fabio",             "senha": "1825$", "role": "basic"},
    {"codigo": "3377", "Usuario": "Mario Ricardo",          "senha": "1838*", "role": "basic"},
    {"codigo": "3377", "Usuario": "maricelisrossi@gmail.com","senha": "1825", "role": "admin"},
]

# ✅ Se já estiver logado, redireciona
if st.session_state.get("acesso_liberado"):
    st.switch_page("pages/Operacional.py")

# 🧾 Tela de login
st.title("🔐 Acesso Restrito")
st.markdown("Informe o código da empresa, Usuário e senha.")

codigo = st.text_input("Código da Empresa:")
Usuario = st.text_input("Usuário:")
senha = st.text_input("Senha:", type="password")

def autenticar(codigo: str, usuario: str, senha: str):
    for u in USUARIOS:
        if u["codigo"] == codigo and u["Usuario"] == usuario and u["senha"] == senha:
            return u
    return None

# ✅ Botão de login
if st.button("Entrar", type="primary"):
    usuario_encontrado = autenticar(codigo, Usuario, senha)

    if usuario_encontrado:
        st.session_state["acesso_liberado"] = True
        st.session_state["empresa"] = codigo
        st.session_state["usuario_logado"] = Usuario
        st.session_state["role"] = usuario_encontrado.get("role", "basic")

        # Permissões centralizadas: admin vê tudo, demais só a aba Entrada/Saída OS
        st.session_state["tabs_permitidas"] = (
            ["all"] if st.session_state["role"] == "admin" else ["entrada_saida_os"]
        )

        st.switch_page("pages/Operacional.py")
    else:
        st.error("❌ Código, Usuário ou senha incorretos.")
