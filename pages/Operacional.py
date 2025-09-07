# pages/Operacional.py
import streamlit as st
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Painel OS", page_icon="🧰", layout="wide")

# ========= Guarda de sessão (login feito na sua página de acesso) =========
if not st.session_state.get("acesso_liberado"):
    st.stop()

ROLE = st.session_state.get("role", "basic")
USUARIO_LOGADO = st.session_state.get("usuario_logado", "")
EMPRESA = st.session_state.get("empresa", "")

# ========= Alvos do Google Sheets =========
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1t82JJfHgiVeANV6fik5ShN6r30UMeDWUqDvlUK0Ok38/edit?gid=0#gid=0"
WORKSHEET_NAME  = "EntradaSaidaOS"

def _extract_spreadsheet_id(url: str) -> str:
    try:
        return url.split("/d/")[1].split("/")[0]
    except Exception:
        return url

SPREADSHEET_ID = _extract_spreadsheet_id(SPREADSHEET_URL)

# ========= Estilo e navegação com Enter =========
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

# ========= Helpers do Google Sheets =========
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

HEADERS = [
    "OS", "ITEM", "QUANTIDADE", "DATA", "HORA",
    "OPERADOR", "MAQUINA", "ENTRADA/SAIDA",
    "Verificação", "Planilha", "Controle"
]
IDX_CONTROLE = 11  # posição da coluna "Controle" (1-based)

def _gspread_client():
    sa_str = st.secrets.get("GOOGLE_SERVICE_ACCOUNT")
    if not sa_str:
        st.error("Secret GOOGLE_SERVICE_ACCOUNT não encontrado. Adicione-o em `.streamlit/secrets.toml` ou no painel de Secrets.")
        st.stop()
    try:
        sa_dict = json.loads(sa_str)
    except Exception as e:
        st.error(f"GOOGLE_SERVICE_ACCOUNT inválido: {e}")
        st.stop()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_dict, SCOPES)
    return gspread.authorize(creds)

def _open_or_prepare_ws(client):
    sh = client.open_by_key(SPREADSHEET_ID)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(HEADERS))
    # Garante o cabeçalho na ordem exata
    existing = ws.get_all_values()
    if not existing:
        ws.resize(rows=1, cols=len(HEADERS))
        ws.update("A1", [HEADERS])
    else:
        # Se a primeira linha não bate, atualiza
        if existing[0] != HEADERS:
            ws.resize(rows=1, cols=len(HEADERS))
            ws.update("A1", [HEADERS])
    return ws

def _chave_controle(os_: int, item_: int, mov: str) -> str:
    # mov em lowercase e sem acento, conforme pedido: "entrada" ou "saida"
    mov_key = "entrada" if mov == "Entrada" else "saida"
    return f"{os_}&{item_}%{mov_key}"

def _ja_existe_controle(ws, chave: str) -> bool:
    try:
        # Lê a coluna Controle (IDX_CONTROLE) inteira
        controles = ws.col_values(IDX_CONTROLE)
        # Remove o cabeçalho
        controles = [c for c in controles[1:] if c]
        return chave in set(controles)
    except Exception:
        # Se falhar a leitura por algum motivo, assume que não existe (para não travar a operação)
        return False

def salvar_linha(ws, registro: dict) -> tuple[bool, str | None]:
    try:
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        data = now.strftime("%d/%m/%Y")  # DATA
        hora = now.strftime("%H:%M:%S")  # HORA

        # Monta linha na ordem do cabeçalho
        linha = [
            registro["OS"],                      # OS
            registro["Item"],                    # ITEM
            registro["Quantidade"],              # QUANTIDADE
            data,                                # DATA
            hora,                                # HORA
            USUARIO_LOGADO,                      # OPERADOR
            registro["Máquina"],                 # MAQUINA
            registro["Movimento"],               # ENTRADA/SAIDA
            "",                                  # Verificação (deixe para sua planilha usar fórmula/regra)
            WORKSHEET_NAME,                      # Planilha
            _chave_controle(registro["OS"], registro["Item"], registro["Movimento"]),  # Controle
        ]

        # Duplicidade pelo Controle
        chave = linha[-1]
        if _ja_existe_controle(ws, chave):
            return False, f"Duplicado: **{chave}** já existe na coluna Controle."

        ws.append_row(linha, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e:
        return False, str(e)

# ========= Tabs (admin vê todas; demais só a 1ª) =========
ALL_TABS = [
    "📋 Entrada/Saída OS",
    "📊 Relatório 1 (em desenvolvimento)",
    "📈 Relatório 2 (em desenvolvimento)",
    "⚙️ Configurações (em desenvolvimento)"
]
tabs = st.tabs(ALL_TABS if ROLE == "admin" else [ALL_TABS[0]])

def campos_validos(os_, maq, qtd, mov):
    return (os_ > 0) and bool(maq.strip()) and (qtd >= 1) and (mov in ("Entrada", "Saída"))

# ========= Aba 1: Entrada/Saída OS =========
with tabs[0]:
    with st.container(border=True):
        st.subheader("💼 Entrada/Saída OS")
        st.caption("Preencha os dados e clique em **Salvar**. O sistema checa **duplicidade** pela coluna **Controle** (OS&ITEM%entrada|saida).")

        # Linha 1
        c1, c2, c3 = st.columns(3)
        with c1:
            os_  = st.number_input("🔑 OS", min_value=0, step=1, format="%d", key="os")
        with c2:
            item = st.number_input("Item", min_value=0, step=1, format="%d", key="item")
        with c3:
            maq  = st.text_input("Máquina", placeholder="Ex.: 6666666", key="maq")

        # Linha 2 (Quantidade à esquerda; Movimento à direita SEM seleção inicial)
        qcol, mcol = st.columns([0.8, 1.2])
        with qcol:
            qtd  = st.number_input("Quantidade", min_value=1, step=1, format="%d", key="qtd")
        with mcol:
            try:
                mov = st.radio("Movimento", ["Entrada", "Saída"], index=None, horizontal=True, key="mov")
            except TypeError:
                # Fallback se sua versão de Streamlit não suporta index=None:
                escolha = st.radio("Movimento", ["Selecione...", "Entrada", "Saída"], index=0, horizontal=True, key="mov")
                mov = None if escolha == "Selecione..." else escolha

        col_a, col_b = st.columns([1, 1])
        salvar = col_a.button(
            "💾 Salvar",
            use_container_width=True,
            disabled=not campos_validos(os_, maq, qtd, mov)
        )
        limpar = col_b.button("🧹 Limpar", use_container_width=True)

        if limpar:
            for k in ("os", "item", "maq", "qtd", "mov"):
                st.session_state.pop(k, None)
            st.rerun()

        if salvar:
            if not campos_validos(os_, maq, qtd, mov):
                st.error("Preencha todos os campos corretamente e escolha o movimento.")
            else:
                # Monta o registro (para exibir e salvar)
                registro = {
                    "OS": int(os_),
                    "Item": int(item),
                    "Quantidade": int(qtd),
                    "Máquina": maq.strip(),
                    "Movimento": mov,
                }

                # Conecta e garante worksheet/cabeçalho
                try:
                    client = _gspread_client()
                    ws = _open_or_prepare_ws(client)
                except Exception as e:
                    st.error(f"Erro de credencial/planilha: {e}")
                    st.stop()

                ok, err = salvar_linha(ws, registro)
                if ok:
                    st.success("✅ Registro salvo na planilha (aba **EntradaSaidaOS**).")
                    st.markdown('<div class="box">', unsafe_allow_html=True)
                    st.json({
                        **registro,
                        "DATA": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y"),
                        "HORA": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%H:%M:%S"),
                        "OPERADOR": USUARIO_LOGADO,
                        "Controle": _chave_controle(registro["OS"], registro["Item"], registro["Movimento"]),
                    })
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="badge">Movimento: <b>{mov}</b></div>', unsafe_allow_html=True)
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
