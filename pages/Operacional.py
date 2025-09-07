# app.py
# ---------------------------------------------------------
# Painel "Entrada/Saída OS" (somente UI – sem Sheets por enquanto)
# ---------------------------------------------------------
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Entrada/Saída OS", page_icon="🧾", layout="centered")

# ---------- Tema / CSS ----------
st.markdown("""
<style>
:root{
  --bg:#eaf2ff;
  --card:#ffffff;
  --accent:#2563eb;      /* azul */
  --accent-2:#f59e0b;    /* laranja */
  --danger:#ef4444;      /* vermelho */
  --border:#e5e7eb;
  --text:#0f172a;
  --muted:#6b7280;
}
html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg);
}
.card{
  width: 760px; max-width: 100%;
  margin: 18px auto 36px auto;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 18px;
  box-shadow: 0 10px 24px rgba(0,0,0,.06);
  overflow: hidden;
}
.card__header{
  display:flex; align-items:center; justify-content:space-between;
  padding: 18px 20px;
  background: linear-gradient(135deg, var(--accent) 0%, #60a5fa 100%);
  color: #fff; font-weight: 700; letter-spacing:.3px;
}
.header__title{
  display:flex; gap:12px; align-items:center; font-size: 1.05rem;
}
.header__actions{
  display:flex; gap:8px;
}
.icon-btn{
  display:inline-flex; align-items:center; gap:10px;
  border: 0; cursor: pointer; padding: 8px 12px;
  border-radius: 12px; font-weight:700; font-size:.9rem;
  box-shadow: 0 4px 10px rgba(0,0,0,.07);
}
.save{ background:#fff; color:#0f172a; }
.cancel{ background: #fff0f0; color: var(--danger); }
.icon{ font-size: 1.05rem; }
.card__body{ padding: 16px 20px 22px; }
.row{ display:grid; grid-template-columns: 220px 1fr; align-items:center; gap: 12px; margin: 8px 0; }
.label{ font-weight:700; color: var(--text); }
.hint{ color: var(--muted); font-size:.86rem; margin-top:-4px; }
.divider{ height:1px; background:var(--border); margin:14px 0 8px; }
.success{
  margin: 8px 0 0; padding: 10px 12px; border-radius:12px;
  border:1px solid #d1fae5; background:#ecfdf5; color:#065f46; font-weight:600;
}
.error{
  margin: 8px 0 0; padding: 10px 12px; border-radius:12px;
  border:1px solid #fee2e2; background:#fef2f2; color:#991b1b; font-weight:600;
}
.preview{
  margin-top: 6px; font-size:.94rem; color:var(--muted);
}
</style>
""", unsafe_allow_html=True)

# ---------- Estado / helpers ----------
def reset_form():
    for k in ["os", "item", "qtd", "data_ctrl", "operador", "maquina", "mov"]:
        if k in st.session_state: del st.session_state[k]

def validate(data: dict):
    errs = []
    if not data["os"]: errs.append("Informe o número da **OS**.")
    if data["item"] is None: errs.append("Informe o **Item**.")
    if data["qtd"] is None or data["qtd"] <= 0: errs.append("**Quantidade** deve ser maior que zero.")
    if not data["operador"]: errs.append("Informe o **Operador**.")
    if not data["maquina"]: errs.append("Informe a **Máquina**.")
    return errs

# ---------- Conteúdo ----------
st.markdown('<div class="card">', unsafe_allow_html=True)

# Cabeçalho com botões (funcionais)
col1, col2 = st.columns([1,1])
with col1:
    st.markdown("""
    <div class="card__header">
      <div class="header__title">🧰 ENTRADA/SAÍDA OS</div>
      <div class="header__actions">
        <!-- Botões são apenas visuais; os de verdade estão abaixo -->
      </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    # espaço vazio só para manter grade responsiva
    st.write("")

st.markdown('<div class="card__body">', unsafe_allow_html=True)

# Formulário
with st.form(key="form_os"):
    # Linhas – usamos widgets Streamlit, mas “alinhamos” com CSS acima
    st.markdown('<div class="row"><div class="label">OS</div><div>', unsafe_allow_html=True)
    os_num = st.text_input("", key="os", placeholder="Ex.: 9532")
    st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="row"><div class="label">Item</div><div>', unsafe_allow_html=True)
    item = st.number_input("", step=1, min_value=0, key="item", placeholder="Ex.: 2", format="%d")
    st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="row"><div class="label">Quantidade</div><div>', unsafe_allow_html=True)
    qtd = st.number_input("", step=1, min_value=0, key="qtd", placeholder="Ex.: 7", format="%d")
    st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="row"><div class="label">Data controle</div><div>', unsafe_allow_html=True)
    data_ctrl = st.datetime_input("", value=datetime.now(), key="data_ctrl")
    st.markdown('<div class="hint">preenchido automaticamente (edite se precisar)</div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="row"><div class="label">Operador</div><div>', unsafe_allow_html=True)
    operador = st.text_input("", key="operador", placeholder="Ex.: 27")
    st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="row"><div class="label">Máquina</div><div>', unsafe_allow_html=True)
    maquina = st.text_input("", key="maquina", placeholder="Ex.: 6666666")
    st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="row"><div class="label">Movimento</div><div>', unsafe_allow_html=True)
    mov = st.selectbox("", ["Entrada", "Saída"], index=1, key="mov")
    st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,1,6])
    submit = c1.form_submit_button("💾 Salvar", use_container_width=True)
    cancel = c2.form_submit_button("✖️ Cancelar", use_container_width=True)

# Lógica dos botões
if 'last_payload' not in st.session_state:
    st.session_state.last_payload = None

if 'just_cleared' not in st.session_state:
    st.session_state.just_cleared = False

if cancel:
    reset_form()
    st.session_state.just_cleared = True

if submit:
    payload = {
        "os": (os_num or "").strip(),
        "item": item if item is not None else None,
        "qtd": qtd if qtd is not None else None,
        "data_controle": data_ctrl.isoformat() if data_ctrl else None,
        "operador": (operador or "").strip(),
        "maquina": (maquina or "").strip(),
        "movimento": mov,
        "ts_submit": datetime.now().isoformat()
    }
    errors = validate(payload)
    if errors:
        for e in errors:
            st.markdown(f'<div class="error">❌ {e}</div>', unsafe_allow_html=True)
    else:
        st.session_state.last_payload = payload
        st.markdown('<div class="success">✅ Registro preparado! (ainda não enviamos para o Google Sheets)</div>', unsafe_allow_html=True)
        # Aqui no futuro: enviar_para_google_sheets(payload)

# Preview do último registro válido
if st.session_state.just_cleared:
    st.session_state.just_cleared = False
else:
    if st.session_state.last_payload:
        p = st.session_state.last_payload
        st.markdown(
            f"""
            <div class="preview">
              <b>Prévia:</b> OS {p['os']} · Item {p['item']} · Qtd {p['qtd']} · {p['movimento']}
              · Operador {p['operador']} · Máquina {p['maquina']} · Data {p['data_controle']}
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown('</div></div>', unsafe_allow_html=True)

# Rodapé leve
st.caption("UI pronta para integração — depois conectamos ao Google Sheets com gspread.")
