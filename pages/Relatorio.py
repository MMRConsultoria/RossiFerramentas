# pages/Relatorio_Tempo.py
import streamlit as st
import pandas as pd
import json, gspread
from datetime import datetime, date
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound
from zoneinfo import ZoneInfo

# ========= ACESSO (somente admin) =========
if not st.session_state.get("acesso_liberado"):
    st.stop()
if st.session_state.get("role", "basic") != "admin":
    st.error("🔒 Acesso restrito: apenas administradores podem ver este relatório.")
    st.stop()

st.set_page_config(page_title="Relatórios | Tempo por OS", page_icon="⏱️", layout="wide")
st.title("⏱️ Relatório — Tempo por OS")

# ========= CONFIG PLANILHA =========
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1t82JJfHgiVeANV6fik5ShN6r30UMeDWUqDvlUK0Ok38/edit?gid=0#gid=0"
WORKSHEET_NAME  = "EntradaSaidaOS"
def _spreadsheet_id_from_url(url: str) -> str:
    try:
        return url.split("/d/")[1].split("/")[0]
    except Exception:
        return url
SPREADSHEET_ID = _spreadsheet_id_from_url(SPREADSHEET_URL)

# ========= GSHEETS CLIENT =========
SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
def _get_sa_dict():
    sa_str = st.secrets.get("GOOGLE_SERVICE_ACCOUNT")
    if not sa_str:
        st.error("Secret GOOGLE_SERVICE_ACCOUNT não encontrado.")
        st.stop()
    return json.loads(sa_str)

def _gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(_get_sa_dict(), SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=120)
def load_sheet_df():
    client = _gspread_client()
    ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    rows = ws.get_all_records()  # usa a 1ª linha como cabeçalho
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)

    # Colunas esperadas (do seu cabeçalho):
    # OS | ITEM | QUANTIDADE | AFIACAO/EROSAO | DATA | HORA | OPERADOR | MAQUINA |
    # ENTRADA/SAIDA | OS- Item | Afiação/Erosão | Controle
    # --- normalizações:
    df["OS"]    = pd.to_numeric(df.get("OS"), errors="coerce").astype("Int64")
    df["ITEM"]  = pd.to_numeric(df.get("ITEM"), errors="coerce").astype("Int64")
    df["MOV"]   = df.get("ENTRADA/SAIDA","").astype(str).str.strip()
    df["PROC"]  = df.get("Afiação/Erosão", df.get("AFIACAO/EROSAO","")).astype(str).str.strip()
    df["OS_Item"] = df.get("OS- Item","").astype(str).str.strip()
    # fallback de OS-Item
    mask_empty = df["OS_Item"].eq("") | df["OS_Item"].isna()
    df.loc[mask_empty, "OS_Item"] = df["OS"].astype(str) + "-" + df["ITEM"].astype(str)

    # timestamp
    df["DATA"] = df["DATA"].astype(str)
    df["HORA"] = df["HORA"].astype(str)
    df["TS"]   = pd.to_datetime(df["DATA"] + " " + df["HORA"], dayfirst=True, errors="coerce").dt.tz_localize(ZoneInfo("America/Sao_Paulo"), nonexistent="NaT", ambiguous="NaT")
    # normaliza movimentos
    m = df["MOV"].str.lower()
    df["MOV"] = pd.Series(pd.NA, index=df.index)
    df.loc[m.str.contains("entrada", na=False), "MOV"] = "Entrada"
    df.loc[m.str.contains("saída", na=False) | m.str.contains("saida", na=False), "MOV"] = "Saída"

    # limpa linhas sem timestamp ou movimento
    df = df.dropna(subset=["TS","MOV","OS","ITEM"]).copy()
    df = df.sort_values("TS").reset_index(drop=True)
    return df

def fmt_hms(seconds: float) -> str:
    if pd.isna(seconds): return "-"
    seconds = int(round(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

df = load_sheet_df()
if df.empty:
    st.info("Sem dados na planilha.")
    st.stop()

# ========= FILTROS =========
min_date = pd.to_datetime(df["TS"].min()).date()
max_date = pd.to_datetime(df["TS"].max()).date()
col_f1, col_f2, col_f3, col_f4 = st.columns([1.3, 1, 1, 1.2])
with col_f1:
    d_ini, d_fim = st.date_input("Período", (min_date, max_date), min_value=min_date, max_value=max_date)
with col_f2:
    os_sel = st.multiselect("Filtrar OS", sorted(df["OS"].dropna().unique().tolist()))
with col_f3:
    so_com_processo = st.checkbox("Parear considerando Processo", value=True, help="Se marcado, Entrada e Saída só pareiam quando o Processo (Afiação/Erosão) também coincide.")
with col_f4:
    maquina_sel = st.multiselect("Filtrar Máquina", sorted(df["MAQUINA"].astype(str).unique().tolist()))

mask = (df["TS"].dt.date >= d_ini) & (df["TS"].dt.date <= d_fim)
if os_sel:
    mask &= df["OS"].isin(os_sel)
if maquina_sel:
    mask &= df["MAQUINA"].astype(str).isin(maquina_sel)

df_f = df.loc[mask].copy()

# ========= CÁLCULO DOS CICLOS (pareando Entrada -> Saída) =========
pairs = []
entradas_sem_saida = []   # inconsistências
saidas_sem_entrada = []   # inconsistências

group_cols = ["OS_Item"] + (["PROC"] if so_com_processo else [])  # chave de pareamento
for key, g in df_f.groupby(group_cols, sort=False):
    g = g.sort_values("TS")
    stack = []
    for _, r in g.iterrows():
        if r["MOV"] == "Entrada":
            stack.append(r)
        elif r["MOV"] == "Saída":
            if stack:
                r_in = stack.pop(0)
                dur = (r["TS"] - r_in["TS"]).total_seconds()
                pairs.append({
                    "OS": r["OS"], "Item": r["ITEM"],
                    "OS_Item": r["OS_Item"],
                    "PROC": r["PROC"],
                    "Entrada_TS": r_in["TS"], "Saida_TS": r["TS"], "Dur_s": dur,
                })
            else:
                saidas_sem_entrada.append({"OS_Item": r["OS_Item"], "PROC": r["PROC"], "Saida_TS": r["TS"], "OS": r["OS"], "Item": r["ITEM"]})
    # o que sobrar no stack são entradas sem saída
    for r_in in stack:
        entradas_sem_saida.append({"OS_Item": r_in["OS_Item"], "PROC": r_in["PROC"], "Entrada_TS": r_in["TS"], "OS": r_in["OS"], "Item": r_in["ITEM"]})

df_pairs = pd.DataFrame(pairs)
df_e_open = pd.DataFrame(entradas_sem_saida)
df_s_orph = pd.DataFrame(saidas_sem_entrada)

# ========= AGREGADOS =========
if not df_pairs.empty:
    por_os_item = (df_pairs
        .groupby(["OS","Item","OS_Item"] + (["PROC"] if so_com_processo else []), as_index=False)
        .agg(Ciclos=("Dur_s","count"), Segundos=("Dur_s","sum"),
             Primeiro=("Entrada_TS","min"), Ultimo=("Saida_TS","max"))
    )
    por_os_item["HH:MM:SS"] = por_os_item["Segundos"].map(fmt_hms)

    por_os = (por_os_item
        .groupby(["OS"], as_index=False)
        .agg(Ciclos=("Ciclos","sum"), Segundos=("Segundos","sum"))
    )
    por_os["HH:MM:SS"] = por_os["Segundos"].map(fmt_hms)
else:
    por_os_item = pd.DataFrame(columns=["OS","Item","OS_Item","PROC","Ciclos","Segundos","Primeiro","Ultimo","HH:MM:SS"])
    por_os = pd.DataFrame(columns=["OS","Ciclos","Segundos","HH:MM:SS"])

# ========= KPIs =========
k1,k2,k3,k4 = st.columns(4)
with k1: st.metric("Ciclos pareados", int(df_pairs.shape[0]))
with k2: st.metric("Tempo total (HH:MM:SS)", fmt_hms(por_os["Segundos"].sum() if not por_os.empty else 0))
with k3: st.metric("Entradas sem Saída", int(df_e_open.shape[0]))
with k4: st.metric("Saídas sem Entrada", int(df_s_orph.shape[0]))

st.markdown("---")

# ========= TABELAS =========
st.subheader("⏲️ Tempo por OS")
st.dataframe(
    por_os.sort_values("OS"),
    use_container_width=True,
    hide_index=True
)

st.subheader("🧩 Tempo por OS-Item" + (" e Processo" if so_com_processo else ""))
cols_show = ["OS","Item","OS_Item"] + (["PROC"] if so_com_processo else []) + ["Ciclos","HH:MM:SS","Primeiro","Ultimo"]
st.dataframe(
    por_os_item[cols_show].sort_values(["OS","Item","OS_Item"]),
    use_container_width=True,
    hide_index=True
)

st.subheader("⚠️ Inconsistências")
cA, cB = st.columns(2)
with cA:
    st.caption("**Entradas sem Saída (abertos)** — por OS-Item" + (" e Processo" if so_com_processo else ""))
    if df_e_open.empty:
        st.success("Nenhum aberto.")
    else:
        st.dataframe(
            df_e_open.sort_values(["OS","Item","OS_Item","Entrada_TS"]),
            use_container_width=True, hide_index=True
        )
with cB:
    st.caption("**Saídas sem Entrada (órfãos)** — por OS-Item" + (" e Processo" if so_com_processo else ""))
    if df_s_orph.empty:
        st.success("Nenhum órfão.")
    else:
        st.dataframe(
            df_s_orph.sort_values(["OS","Item","OS_Item","Saida_TS"]),
            use_container_width=True, hide_index=True
        )
