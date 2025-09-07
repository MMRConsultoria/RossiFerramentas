# pages/Operacional.py
import streamlit as st
import json
import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from zoneinfo import ZoneInfo
import traceback

st.set_page_config(page_title="Painel OS", page_icon="💎", layout="wide")

# ========= Guarda de sessão =========
if not st.session_state.get("acesso_liberado"):
    st.stop()

ROLE            = st.session_state.get("role", "basic")
USUARIO_LOGADO  = st.session_state.get("usuario_logado", "")
EMPRESA         = st.session_state.get("empresa", "")

# ========= Planilha / Aba =========
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1t82JJfHgiVeANV6fik5ShN6r30UMeDWUqDvlUK0Ok38/edit?gid=0#gid=0"
WORKSHEET_NAME  = "EntradaSaidaOS"

def _spreadsheet_id_from_url(url: str) -> str:
    try:
        return url.split("/d/")[1].split("/")[0]
    except Exception:
        return url

SPREADSHEET_ID = _spreadsheet_id_from_url(SPREADSHEET_URL)

# ========= UI (abas + Enter = Tab) =========
st.markdown("""
<style>
.stTabs [role="tablist"]{ gap:10px; border-bottom:1px solid #e5e7eb; }
.stTabs [role="tab"]{
  background:#f3f4f6; padding:8px 20px; border-radius:8px 8px 0 0;
  font-weight:600; color:#374151; border:1px solid transparent;
}
.stTabs [aria-selected="true"]{ background:#2563eb; color:#fff!important; border-color:#2563eb; }
.stTabs [role="tab"]:hover{ background:#e0e7ff; color:#1e3a8a; }
.stTabs [role="tablist"] + div:empty { display:none !important; }
.box{ padding:12px; border:1px dashed #d1d5db; border-radius:12px; background:#f9fafb; }
.badge{ display:inline-flex; gap:8px; align-items:center; background:#eff6ff; color:#1d4ed8;
  border:1px solid #bfdbfe; border-radius:999px; padding:6px 12px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<script>
(function(){
  function F(){const s='input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])';
    return Array.from(document.querySelectorAll(s)).filter(el=>el.offsetParent!==null);}
  function N(cur,fwd){const a=F(),i=a.indexOf(cur); if(i===-1) return null;
    let j=fwd?i+1:i-1; if(j>=a.length) j=0; if(j<0) j=a.length-1; return a[j]||null;}
  document.addEventListener('keydown', function(e){
    if(e.key!=='Enter') return; const el=document.activeElement; if(!el) return;
    if(el.tagName==='BUTTON'||el.type==='submit') return; if(el.tagName==='TEXTAREA'&&e.shiftKey) return;
    e.preventDefault(); e.stopPropagation(); const t=N(el,!e.shiftKey); if(t){t.focus(); try{t.select&&t.select();}catch(_){}}}, true);
})();
</script>
""", unsafe_allow_html=True)

# ========= Cabeçalho e índice da coluna Controle =========
HEADERS = [
    "OS", "ITEM", "QUANTIDADE", "DATA", "HORA",
    "OPERADOR", "MAQUINA", "ENTRADA/SAIDA",
    "OS- Item", "Planilha", "Controle"              # <- alterado aqui
]
IDX_CONTROLE = 11  # 1-based

# ========= Helpers de erro/diagnóstico =========
def _show_error(msg: str, exc: Exception | None = None, extra: dict | None = None):
    if exc:
        st.error(f"{msg}: {exc}")
        with st.expander("Detalhes do erro (diagnóstico)"):
            st.code(traceback.format_exc())
    else:
        st.error(msg)
    if extra:
        with st.expander("Informações úteis"):
            for k, v in extra.items():
                st.write(f"**{k}:** {v}")

# ========= Credenciais & Google Sheets =========
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def _get_sa_dict():
    sa_str = st.secrets.get("GOOGLE_SERVICE_ACCOUNT", None)
    if not sa_str:
        _show_error("Secret GOOGLE_SERVICE_ACCOUNT não encontrado.")
        st.stop()
    try:
        return json.loads(sa_str)
    except Exception as e:
        _show_error("GOOGLE_SERVICE_ACCOUNT inválido (não é STRING JSON escapada)", e)
        st.stop()

def _gspread_client():
    sa_dict = _get_sa_dict()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_dict, SCOPES)
    client = gspread.authorize(creds)
    return client, sa_dict.get("client_email", "desconhecido@sa")

def _open_or_prepare_ws(client):
    sh = client.open_by_key(SPREADSHEET_ID)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=2000, cols=len(HEADERS))
    # garante cabeçalho
    values = ws.get_all_values()
    if not values or values[0] != HEADERS:
        ws.resize(rows=1, cols=len(HEADERS))
        ws.update("A1", [HEADERS])
    return ws

# ========= Chaves (OS-Item e Controle) =========
def os_item_key(os_: int, item_: int) -> str:
    return f"{os_}-{item_}"

def controle_key(os_: int, item_: int, mov: str) -> str:
    # Controle: OS-Item&Entrada ou OS-Item&Saida (sem acento)
    mov_label = "Entrada" if mov == "Entrada" else "Saida"
    return f"{os_item_key(os_, item_)}&{mov_label}"

def ja_existe_controle(ws, chave: str) -> bool:
    try:
        col = ws.col_values(IDX_CONTROLE)
        return chave in set([c for c in col[1:] if c])
    except Exception:
        # em caso de erro de leitura, não travar; considerar não-duplicado
        return False

def salvar_no_sheets(registro: dict) -> tuple[bool, str | None]:
    try:
        client, sa_email = _gspread_client()
        ws = _open_or_prepare_ws(client)

        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        data = now.strftime("%d/%m/%Y")
        hora = now.strftime("%H:%M:%S")

        os_i  = registro["OS"]
        item_ = registro["Item"]
        mov   = registro["Movimento"]

        chave_os_item = os_item_key(os_i, item_)
        chave_ctrl    = controle_key(os_i, item_, mov)

        if ja_existe_controle(ws, chave_ctrl):
            return False, f"⚠️ Duplicidade: **{chave_ctrl}** já existe na coluna *Controle*."

        linha = [
            os_i,                       # OS
            item_,                      # ITEM
            registro["Quantidade"],     # QUANTIDADE
            data,                       # DATA
            hora,                       # HORA
            USUARIO_LOGADO,             # OPERADOR
            registro["Máquina"],        # MAQUINA
            mov,                        # ENTRADA/SAIDA
            chave_os_item,              # OS- Item
            WORKSHEET_NAME,             # Planilha
            chave_ctrl,                 # Controle
        ]
        ws.append_row(linha, value_input_option="USER_ENTERED")
        return True, None
    except APIError as e:
        _show_error(
            "Falha de acesso ao Google Sheets (verifique API ativa e compartilhamento com o Service Account)",
            e,
            {"spreadsheet_id": SPREADSHEET_ID, "worksheet": WORKSHEET_NAME}
        )
        return False, str(e)
    except Exception as e:
        _show_error("Erro ao salvar na planilha", e, {"spreadsheet_id": SPREADSHEET_ID, "worksheet": WORKSHEET_NAME})
        return False, str(e)

# ========= Abas =========
ALL_TABS = [
    "📋 Entrada/Saída OS",
    "📊 Relatório 1 (em desenvolvimento)",
    "📈 Relatório 2 (em desenvolvimento)",
    "⚙️ Configurações (em desenvolvimento)"
]
tabs = st.tabs(ALL_TABS if ROLE == "admin" else [ALL_TABS[0]])

def campos_validos(os_, maq, qtd, mov):
    return (os_ > 0) and bool(maq.strip()) and (qtd >= 1) and (mov in ("Entrada", "Saída"))

# ========= Aba 1 =========
with tabs[0]:
    with st.container(border=True):
        st.subheader("💎 Entrada/Saída OS")
        st.caption("Preencha e **Salvar**. Duplicidade checada em **Controle** (OS-Item&Entrada|Saida).")

        # Linha 1
        c1, c2, c3 = st.columns(3)
        with c1:
            os_  = st.number_input("🔑 OS", min_value=0, step=1, format="%d", key="os")
        with c2:
            item = st.number_input("Item", min_value=0, step=1, format="%d", key="item")
        with c3:
            maq  = st.text_input("Máquina", placeholder="Ex.: 6666666", key="maq")

        # Linha 2
        qcol, mcol = st.columns([0.8, 1.2])
        with qcol:
            qtd  = st.number_input("Quantidade", min_value=1, step=1, format="%d", key="qtd")
        with mcol:
            try:
                mov = st.radio("Movimento", ["Entrada", "Saída"], index=None, horizontal=True, key="mov")
            except TypeError:
                opt = st.radio("Movimento", ["Selecione...", "Entrada", "Saída"], index=0, horizontal=True, key="mov")
                mov = None if opt == "Selecione..." else opt

        col_a, col_b = st.columns([1, 1])
        salvar = col_a.button(
            "💾 Salvar",
            use_container_width=True,
            disabled=not campos_validos(os_, maq, qtd, mov)
        )
        limpar = col_b.button("🧹 Limpar", use_container_width=True)

        if limpar:
            for k in ("os","item","maq","qtd","mov"):
                st.session_state.pop(k, None)
            st.rerun()

        if salvar:
            if not campos_validos(os_, maq, qtd, mov):
                st.error("Preencha todos os campos corretamente e escolha o movimento.")
            else:
                registro = {
                    "OS": int(os_),
                    "Item": int(item),
                    "Quantidade": int(qtd),
                    "Máquina": maq.strip(),
                    "Movimento": mov,
                }

                ok, err = salvar_no_sheets(registro)
                if ok:
                    chave_ctrl = controle_key(registro["OS"], registro["Item"], registro["Movimento"])
                    st.success(f"✅ Registro salvo. Controle: **{chave_ctrl}**")
                    st.markdown('<div class="box">', unsafe_allow_html=True)
                    st.json({
                        **registro,
                        "DATA": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y"),
                        "HORA": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%H:%M:%S"),
                        "OPERADOR": USUARIO_LOGADO,
                        "OS- Item": os_item_key(registro["OS"], registro["Item"]),
                        "Controle": chave_ctrl,
                    })
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error(err)

# ========= Abas extras (somente admin) =========
if ROLE == "admin" and len(tabs) > 1:
    with tabs[1]:
        st.info("🚧 Relatório 1 em desenvolvimento...")
    with tabs[2]:
        st.info("🚧 Relatório 2 em desenvolvimento...")
    with tabs[3]:
        st.info("⚙️ Configurações em desenvolvimento...")
