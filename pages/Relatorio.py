# pages/Relatorio_OSItem.py
import streamlit as st
import pandas as pd
import json, gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound
from datetime import datetime
from zoneinfo import ZoneInfo

# ===== Acesso: somente admin =====
if not st.session_state.get("acesso_liberado"):
    st.stop()
if st.session_state.get("role", "basic") != "admin":
    st.error("🔒 Acesso restrito: apenas administradores.")
    st.stop()

st.set_page_config(page_title="Relatório | OS-Item", page_icon="⏱️", layout="wide")
st.title("⏱️ Relatório — Tempo por OS-Item")

# ===== Planilha =====
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1t82JJfHgiVeANV6fik5ShN6r30UMeDWUqDvlUK0Ok38/edit?gid=0#gid=0"
WORKSHEET_NAME  = "EntradaSaidaOS"
def _sheet_id(url: str) -> str:
    try: return url.split("/d/")[1].split("/")[0]
    except: return url
SPREADSHEET_ID = _sheet_id(SPREADSHEET_URL)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
def _client():
    sa = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(sa, SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=180)
def load_df() -> pd.DataFrame:
    ws = _client().open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    rows = ws.get_all_records()
    if not rows: return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Cabeçalho esperado:
    # OS | ITEM | QUANTIDADE | AFIACAO/EROSAO | DATA | HORA | OPERADOR | MAQUINA |
    # ENTRADA/SAIDA | OS- Item | Afiação/Erosão | Controle

    df["OS"]   = pd.to_numeric(df.get("OS"), errors="coerce").astype("Int64")
    df["ITEM"] = pd.to_numeric(df.get("ITEM"), errors="coerce").astype("Int64")
    df["PROC"] = df.get("Afiação/Erosão", df.get("AFIACAO/EROSAO","")).astype(str).str.strip()

    # OS-Item (fallback A-B)
    df["OS_Item"] = df.get("OS- Item","").astype(str).str.strip()
    m = df["OS_Item"].eq("") | df["OS_Item"].isna()
    df.loc[m, "OS_Item"] = df["OS"].astype(str) + "-" + df["ITEM"].astype(str)

    # Movimento normalizado
    mov = df.get("ENTRADA/SAIDA","").astype(str).str.strip().str.lower()
    df["MOV"] = pd.NA
    df.loc[mov.str.contains("entrada", na=False), "MOV"] = "Entrada"
    df.loc[mov.str.contains("saída", na=False) | mov.str.contains("saida", na=False), "MOV"] = "Saída"

    # Timestamp (fuso São Paulo)
    df["TS"] = pd.to_datetime(df["DATA"].astype(str) + " " + df["HORA"].astype(str),
                              dayfirst=True, errors="coerce")
    tz = ZoneInfo("America/Sao_Paulo")
    df["TS"] = df["TS"].dt.tz_localize(tz, nonexistent="NaT", ambiguous="NaT")

    df = df.dropna(subset=["OS","ITEM","MOV","TS"]).copy()
    df = df.sort_values("TS").reset_index(drop=True)
    return df

df = load_df()
if df.empty:
    st.info("Sem dados.")
    st.stop()

# ===== Filtros =====
min_d = df["TS"].dt.date.min()
max_d = df["TS"].dt.date.max()
c1,c2,c3,c4 = st.columns([1.2,1,1,1.2])
with c1:
    d_ini, d_fim = st.date_input("Período", (min_d, max_d), min_value=min_d, max_value=max_d)
with c2:
    os_sel = st.multiselect("OS", sorted(df["OS"].dropna().unique().tolist()))
with c3:
    parear_por_processo = st.checkbox("Parear por Processo", value=True,
        help="Se marcado, Entrada e Saída só pareiam quando o Processo (Afiação/Erosão) também coincide.")
with c4:
    maq_sel = st.multiselect("Máquina", sorted(df["MAQUINA"].astype(str).unique().tolist()))

mask = (df["TS"].dt.date >= d_ini) & (df["TS"].dt.date <= d_fim)
if os_sel: mask &= df["OS"].isin(os_sel)
if maq_sel: mask &= df["MAQUINA"].astype(str).isin(maq_sel)
df_f = df.loc[mask].copy()

# ===== Pareamento Entrada -> Saída =====
pairs = []
entradas_sem_saida = []
saidas_sem_entrada = []

key_cols = ["OS_Item"] + (["PROC"] if parear_por_processo else [])
for key, g in df_f.groupby(key_cols, sort=False):
    g = g.sort_values("TS")
    stack = []  # fila de entradas
    for _, r in g.iterrows():
        if r["MOV"] == "Entrada":
            stack.append(r)
        else:  # Saída
            if stack:
                r_in = stack.pop(0)
                dur = (r["TS"] - r_in["TS"]).total_seconds()
                pairs.append({
                    "OS": r["OS"], "Item": r["ITEM"], "OS_Item": r["OS_Item"],
                    "PROC": r["PROC"], "Entrada_TS": r_in["TS"], "Saida_TS": r["TS"],
                    "Dur_s": dur
                })
            else:
                saidas_sem_entrada.append({
                    "OS": r["OS"], "Item": r["ITEM"], "OS_Item": r["OS_Item"],
                    "PROC": r["PROC"], "Saida_TS": r["TS"]
                })
    # o que sobrar são entradas sem saída
    for r_in in stack:
        entradas_sem_saida.append({
            "OS": r_in["OS"], "Item": r_in["ITEM"], "OS_Item": r_in["OS_Item"],
            "PROC": r_in["PROC"], "Entrada_TS": r_in["TS"]
        })

df_pairs = pd.DataFrame(pairs)
df_open  = pd.DataFrame(entradas_sem_saida)
df_orph  = pd.DataFrame(saidas_sem_entrada)

def fmt_hms(x):
    secs = int(round(x))
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# Tempo por OS-Item (somente pareados)
if not df_pairs.empty:
    grp_cols = ["OS","Item","OS_Item"] + (["PROC"] if parear_por_processo else [])
    tempo_os_item = (df_pairs.groupby(grp_cols, as_index=False)
                     .agg(Ciclos=("Dur_s","count"),
                          Segundos=("Dur_s","sum"),
                          Primeiro=("Entrada_TS","min"),
                          Ultimo=("Saida_TS","max")))
    tempo_os_item["HH:MM:SS"] = tempo_os_item["Segundos"].map(fmt_hms)
else:
    tempo_os_item = pd.DataFrame(columns=["OS","Item","OS_Item","PROC","Ciclos","Segundos","Primeiro","Ultimo","HH:MM:SS"])

# ===== Interface: tabs só com OS-Item =====
t1, t2, t3 = st.tabs(["⏱️ Tempo por OS-Item", "⚠️ Sem Saída", "⚠️ Sem Entrada"])

with t1:
    st.caption("Somente ciclos pareados **Entrada→Saída** (agregado por **OS-Item**" + (" e Processo" if parear_por_processo else "") + ").")
    cols = ["OS","Item","OS_Item"] + (["PROC"] if parear_por_processo else []) + ["Ciclos","HH:MM:SS","Primeiro","Ultimo"]
    st.dataframe(tempo_os_item[cols].sort_values(["OS","Item","OS_Item"]),
                 use_container_width=True, hide_index=True)

with t2:
    st.caption("Registros com **Entrada** sem **Saída** (abertos).")
    if df_open.empty:
        st.success("Nenhum aberto.")
    else:
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        df_o = df_open.copy()
        df_o["Aberto_hh:mm:ss"] = (now - df_o["Entrada_TS"]).dt.total_seconds().map(fmt_hms)
        cols = ["OS","Item","OS_Item"] + (["PROC"] if parear_por_processo else []) + ["Entrada_TS","Aberto_hh:mm:ss"]
        st.dataframe(df_o[cols].sort_values(["OS","Item","OS_Item","Entrada_TS"]),
                     use_container_width=True, hide_index=True)

with t3:
    st.caption("Registros com **Saída** sem **Entrada** (órfãos).")
    if df_orph.empty:
        st.success("Nenhum órfão.")
    else:
        cols = ["OS","Item","OS_Item"] + (["PROC"] if parear_por_processo else []) + ["Saida_TS"]
        st.dataframe(df_orph[cols].sort_values(["OS","Item","OS_Item","Saida_TS"]),
                     use_container_width=True, hide_index=True)
