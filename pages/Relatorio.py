# pages/Relatorios.py
import streamlit as st
import pandas as pd
import json, gspread
from oauth2client.service_account import ServiceAccountCredentials
from zoneinfo import ZoneInfo
from datetime import datetime

# ---------- acesso: somente admin ----------
if not st.session_state.get("acesso_liberado"):
    st.stop()
if st.session_state.get("role", "basic") != "admin":
    st.error("🔒 Acesso restrito: apenas administradores.")
    st.stop()

st.set_page_config(page_title="Relatórios", page_icon="📑", layout="wide")
st.title("📑 Relatórios")

# ---------- planilha ----------
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1t82JJfHgiVeANV6fik5ShN6r30UMeDWUqDvlUK0Ok38/edit?gid=0#gid=0"
WORKSHEET_NAME  = "EntradaSaidaOS"
def _sheet_id(url: str) -> str:
    try: return url.split("/d/")[1].split("/")[0]
    except: return url
SPREADSHEET_ID = _sheet_id(SPREADSHEET_URL)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
def _client():
    sa = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(sa, SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=180)
def load_df() -> pd.DataFrame:
    ws = _client().open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    rows = ws.get_all_records()     # usa o cabeçalho da 1ª linha
    if not rows: 
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Cabeçalho esperado:
    # OS | ITEM | QUANTIDADE | AFIACAO/EROSAO | DATA | HORA | OPERADOR | MAQUINA |
    # ENTRADA/SAIDA | OS- Item | Afiação/Erosão | Controle
    df["OS"]   = pd.to_numeric(df.get("OS"), errors="coerce").astype("Int64")
    df["ITEM"] = pd.to_numeric(df.get("ITEM"), errors="coerce").astype("Int64")

    # OS-Item (fallback A-B se coluna vier vazia)
    df["OS_Item"] = df.get("OS- Item", "").astype(str).str.strip()
    m = df["OS_Item"].eq("") | df["OS_Item"].isna()
    df.loc[m, "OS_Item"] = df["OS"].astype(str) + "-" + df["ITEM"].astype(str)

    # Processo
    df["PROC"] = df.get("Afiação/Erosão", df.get("AFIACAO/EROSAO", "")).astype(str).str.strip()

    # Movimento normalizado
    mov = df.get("ENTRADA/SAIDA", "").astype(str).str.strip().str.lower()
    df["MOV"] = pd.NA
    df.loc[mov.str.contains("entrada", na=False), "MOV"] = "Entrada"
    df.loc[mov.str.contains("saída", na=False) | mov.str.contains("saida", na=False), "MOV"] = "Saída"

    # Timestamp com fuso São Paulo
    df["TS"] = pd.to_datetime(
        df["DATA"].astype(str) + " " + df["HORA"].astype(str),
        dayfirst=True, errors="coerce"
    )
    tz = ZoneInfo("America/Sao_Paulo")
    df["TS"] = df["TS"].dt.tz_localize(tz, nonexistent="NaT", ambiguous="NaT")

    df = df.dropna(subset=["OS","ITEM","MOV","TS"]).copy()
    df = df.sort_values("TS").reset_index(drop=True)
    return df

def fmt_hms(secs: float) -> str:
    secs = int(round(secs))
    h, r = divmod(secs, 3600); m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# ---------- dados ----------
df = load_df()
if df.empty:
    st.info("Sem dados na planilha.")
    st.stop()

# ---------- filtros ----------
min_d = df["TS"].dt.date.min()
max_d = df["TS"].dt.date.max()
c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1.3])
with c1:
    d_ini, d_fim = st.date_input("Período", (min_d, max_d), min_value=min_d, max_value=max_d)
with c2:
    os_sel = st.multiselect("OS", sorted(df["OS"].dropna().unique().tolist()))
with c3:
    maquina_sel = st.multiselect("Máquina", sorted(df["MAQUINA"].astype(str).unique().tolist()))
with c4:
    parear_por_processo = st.checkbox("Parear por Processo (Afiação/Erosão)", value=False)

mask = (df["TS"].dt.date >= d_ini) & (df["TS"].dt.date <= d_fim)
if os_sel: mask &= df["OS"].isin(os_sel)
if maquina_sel: mask &= df["MAQUINA"].astype(str).isin(maquina_sel)
df_f = df.loc[mask].copy()

# ---------- pareamento Entrada -> Saída (por OS-Item; opcionalmente por Processo) ----------
pairs, entradas_sem_saida, saidas_sem_entrada = [], [], []
key_cols = ["OS_Item"] + (["PROC"] if parear_por_processo else [])
for _, g in df_f.groupby(key_cols, sort=False):
    g = g.sort_values("TS")
    fila = []                        # fila de Entradas
    for _, r in g.iterrows():
        if r["MOV"] == "Entrada":
            fila.append(r)
        else:                        # Saída
            if fila:
                r_in = fila.pop(0)   # pareia na ordem (FIFO)
                dur = (r["TS"] - r_in["TS"]).total_seconds()
                pairs.append({
                    "OS_Item": r["OS_Item"], "OS": r["OS"], "Item": r["ITEM"],
                    "PROC": r["PROC"], "Entrada_TS": r_in["TS"], "Saida_TS": r["TS"],
                    "Dur_s": dur
                })
            else:
                saidas_sem_entrada.append({
                    "OS_Item": r["OS_Item"], "OS": r["OS"], "Item": r["ITEM"],
                    "PROC": r["PROC"], "Saida_TS": r["TS"]
                })
    # tudo que sobrou na fila = Entradas sem Saída
    for r_in in fila:
        entradas_sem_saida.append({
            "OS_Item": r_in["OS_Item"], "OS": r_in["OS"], "Item": r_in["ITEM"],
            "PROC": r_in["PROC"], "Entrada_TS": r_in["TS"]
        })

df_pairs = pd.DataFrame(pairs)
df_open  = pd.DataFrame(entradas_sem_saida)
df_orph  = pd.DataFrame(saidas_sem_entrada)

# agregado só por OS-Item (como você pediu)
if not df_pairs.empty:
    cols_group = ["OS_Item"] + (["PROC"] if parear_por_processo else [])
    tempo_os_item = (df_pairs
        .groupby(cols_group, as_index=False)
        .agg(Ciclos=("Dur_s","count"),
             Segundos=("Dur_s","sum"),
             Primeiro=("Entrada_TS","min"),
             Ultimo=("Saida_TS","max"))
    )
    tempo_os_item["HH:MM:SS"] = tempo_os_item["Segundos"].map(fmt_hms)
else:
    tempo_os_item = pd.DataFrame(columns=["OS_Item","PROC","Ciclos","Segundos","Primeiro","Ultimo","HH:MM:SS"])

# ---------- ABAS: Relatório | Gráficos ----------
tab_rel, tab_graf = st.tabs(["📄 Relatório", "📈 Gráficos"])

# ======== RELATÓRIO ========
with tab_rel:
    filtro_rel = st.radio(
        "Mostrar", 
        ["Tempo por OS-Item", "Sem Saída (Entradas abertas)", "Sem Entrada (Saídas órfãs)"],
        horizontal=True
    )
    if filtro_rel == "Tempo por OS-Item":
        cols = ["OS_Item"] + (["PROC"] if parear_por_processo else []) + ["Ciclos","HH:MM:SS","Primeiro","Ultimo"]
        st.dataframe(tempo_os_item[cols].sort_values(["OS_Item"]), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Baixar CSV (Tempo por OS-Item)",
            data=tempo_os_item.to_csv(index=False).encode("utf-8"),
            file_name="tempo_por_os_item.csv",
            mime="text/csv"
        )
    elif filtro_rel == "Sem Saída (Entradas abertas)":
        if df_open.empty:
            st.success("Nenhuma Entrada aberta.")
        else:
            now = datetime.now(ZoneInfo("America/Sao_Paulo"))
            x = df_open.copy()
            x["Aberto_hh:mm:ss"] = (now - x["Entrada_TS"]).dt.total_seconds().map(fmt_hms)
            cols = ["OS_Item"] + (["PROC"] if parear_por_processo else []) + ["Entrada_TS","Aberto_hh:mm:ss"]
            st.dataframe(x[cols].sort_values(["OS_Item","Entrada_TS"]), use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Baixar CSV (Entradas sem Saída)",
                data=x[cols].to_csv(index=False).encode("utf-8"),
                file_name="entradas_sem_saida.csv",
                mime="text/csv"
            )
    else:  # Sem Entrada
        if df_orph.empty:
            st.success("Nenhuma Saída órfã.")
        else:
            cols = ["OS_Item"] + (["PROC"] if parear_por_processo else []) + ["Saida_TS"]
            st.dataframe(df_orph[cols].sort_values(["OS_Item","Saida_TS"]), use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Baixar CSV (Saídas sem Entrada)",
                data=df_orph[cols].to_csv(index=False).encode("utf-8"),
                file_name="saidas_sem_entrada.csv",
                mime="text/csv"
            )

# ======== GRÁFICOS ========
with tab_graf:
    st.caption("Tempo total por **OS-Item** (somente ciclos pareados).")
    if tempo_os_item.empty:
        st.info("Sem dados pareados para o período/filtros selecionados.")
    else:
        # top N
        n_top = st.slider("Mostrar Top N OS-Item por tempo total", 5, 50, 15)
        top_df = tempo_os_item.sort_values("Segundos", ascending=False).head(n_top).copy()
        top_df["Horas"] = top_df["Segundos"] / 3600.0

        # bar chart
        st.bar_chart(
            data=top_df.set_index("OS_Item")["Horas"],
            use_container_width=True,
            height=420
        )

        # série temporal por dia (soma de durações terminadas no dia)
        st.caption("Série diária do tempo total (baseado no horário da **Saída**).")
        serie = (df_pairs.assign(Dia=df_pairs["Saida_TS"].dt.date)
                        .groupby("Dia", as_index=False)["Dur_s"].sum())
        if not serie.empty:
            serie["Horas"] = serie["Dur_s"] / 3600.0
            st.line_chart(serie.set_index("Dia")["Horas"], use_container_width=True, height=320)
