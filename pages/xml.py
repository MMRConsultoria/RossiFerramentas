# pages/Importar_XML_NFe.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Importar XML NF-e → Excel", layout="wide")

# ========= Helpers e parsing =========
NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

def _txt(el, path):
    """Retorna texto de um subelemento (ou "") já com strip."""
    if el is None:
        return ""
    x = el.find(path, NS)
    return (x.text or "").strip() if x is not None and x.text is not None else ""

def _num(el, path):
    """Converte para float com segurança (ou 0.0)."""
    t = _txt(el, path)
    try:
        return float(t.replace(",", ".")) if t else 0.0
    except Exception:
        return 0.0

def parse_nfe_xml(xml_bytes):
    """
    Lê um XML de NF-e (modelo 55) e retorna:
      header: dict com dados da nota
      items:  list[dict] com os itens
    Lida com namespaces oficiais da NF-e.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None, None, "XML inválido"

    # Pode vir embrulhado com <nfeProc> ou só <NFe>
    nfe = root.find(".//nfe:NFe", NS) or root
    inf = nfe.find(".//nfe:infNFe", NS)
    if inf is None:
        return None, None, "NF-e não encontrada (infNFe ausente)"

    # chave
    chave = (inf.attrib.get("Id", "") or "").replace("NFe", "")

    ide  = inf.find("nfe:ide", NS)
    emit = inf.find("nfe:emit", NS)
    dest = inf.find("nfe:dest", NS)
    total = inf.find("nfe:total/nfe:ICMSTot", NS)
    transp = inf.find("nfe:transp", NS)
    pag = inf.find("nfe:pag", NS)  # em versões novas tem <pag><detPag>...

    # protocolo/autorização (quando presente)
    prot = root.find(".//nfe:protNFe", NS)
    cStat = _txt(prot, "nfe:infProt/nfe:cStat")
    xMotivo = _txt(prot, "nfe:infProt/nfe:xMotivo")

    # ===== Cabeçalho =====
    header = {
        "Chave": chave,
        "Modelo": _txt(ide, "nfe:mod"),
        "Série": _txt(ide, "nfe:serie"),
        "Número": _txt(ide, "nfe:nNF"),
        "Emissão": _txt(ide, "nfe:dhEmi") or _txt(ide, "nfe:dEmi"),
        "Tipo NF (0=Entrada,1=Saída)": _txt(ide, "nfe:tpNF"),
        "Natureza da Operação": _txt(ide, "nfe:natOp"),
        "Município Fato Gerador": _txt(ide, "nfe:cMunFG"),
        "UF Emitente": _txt(emit, "nfe:enderEmit/nfe:UF"),
        # Emitente
        "Emit_CNPJ": _txt(emit, "nfe:CNPJ") or _txt(emit, "nfe:CPF"),
        "Emit_Nome": _txt(emit, "nfe:xNome"),
        "Emit_IE": _txt(emit, "nfe:IE"),
        # Destinatário
        "Dest_CNPJ": _txt(dest, "nfe:CNPJ") or _txt(dest, "nfe:CPF"),
        "Dest_Nome": _txt(dest, "nfe:xNome"),
        "Dest_IE": _txt(dest, "nfe:IE"),
        # Totais
        "vBC": _num(total, "nfe:vBC"),
        "vICMS": _num(total, "nfe:vICMS"),
        "vICMSDeson": _num(total, "nfe:vICMSDeson"),
        "vFCP": _num(total, "nfe:vFCP"),
        "vBCST": _num(total, "nfe:vBCST"),
        "vST": _num(total, "nfe:vST"),
        "vProd": _num(total, "nfe:vProd"),
        "vFrete": _num(total, "nfe:vFrete"),
        "vSeg": _num(total, "nfe:vSeg"),
        "vDesc": _num(total, "nfe:vDesc"),
        "vII": _num(total, "nfe:vII"),
        "vIPI": _num(total, "nfe:vIPI"),
        "vPIS": _num(total, "nfe:vPIS"),
        "vCOFINS": _num(total, "nfe:vCOFINS"),
        "vOutro": _num(total, "nfe:vOutro"),
        "vNF": _num(total, "nfe:vNF"),
        # Transporte
        "modFrete": _txt(transp, "nfe:modFrete"),
        # Pagamento (soma dos detPag)
        "vPag_total": 0.0,
        # Protocolo/Status
        "cStat": cStat,
        "xMotivo": xMotivo,
    }

    # Pagamento: múltiplos <detPag>
    vpag_sum = 0.0
    if pag is not None:
        for det in pag.findall("nfe:detPag", NS):
            vpag_sum += _num(det, "nfe:vPag")
    header["vPag_total"] = vpag_sum

    # ===== Itens =====
    itens_out = []
    for det in inf.findall("nfe:det", NS):
        nItem = det.attrib.get("nItem", "")
        prod = det.find("nfe:prod", NS)

        icms = det.find("nfe:imposto/nfe:ICMS", NS)
        icms_det = None
        icms_cst = ""
        icms_origem = ""
        icms_aliq = 0.0
        if icms is not None and list(icms):
            icms_det = list(icms)[0]  # ICMS00/ICMS10/ICMS20...
            icms_cst = _txt(icms_det, "nfe:CST") or _txt(icms_det, "nfe:CSOSN")
            icms_origem = _txt(icms_det, "nfe:orig")
            icms_aliq = _num(icms_det, "nfe:pICMS")

        pis = det.find("nfe:imposto/nfe:PIS", NS)
        pis_det = None
        pis_cst = ""
        pis_aliq = 0.0
        if pis is not None and list(pis):
            pis_det = list(pis)[0]
            pis_cst = _txt(pis_det, "nfe:CST")
            pis_aliq = _num(pis_det, "nfe:pPIS")

        cofins = det.find("nfe:imposto/nfe:COFINS", NS)
        cof_det = None
        cof_cst = ""
        cof_aliq = 0.0
        if cofins is not None and list(cofins):
            cof_det = list(cofins)[0]
            cof_cst = _txt(cof_det, "nfe:CST")
            cof_aliq = _num(cof_det, "nfe:pCOFINS")

        item_dict = {
            "Chave": chave,
            "nItem": nItem,
            "cProd": _txt(prod, "nfe:cProd"),
            "cEAN": _txt(prod, "nfe:cEAN"),
            "xProd": _txt(prod, "nfe:xProd"),
            "NCM": _txt(prod, "nfe:NCM"),
            "CFOP": _txt(prod, "nfe:CFOP"),
            "uCom": _txt(prod, "nfe:uCom"),
            "qCom": _num(prod, "nfe:qCom"),
            "vUnCom": _num(prod, "nfe:vUnCom"),
            "vProd": _num(prod, "nfe:vProd"),
            "cEANTrib": _txt(prod, "nfe:cEANTrib"),
            "uTrib": _txt(prod, "nfe:uTrib"),
            "qTrib": _num(prod, "nfe:qTrib"),
            "vUnTrib": _num(prod, "nfe:vUnTrib"),
            "vDesc_item": _num(prod, "nfe:vDesc"),
            "indTot": _txt(prod, "nfe:indTot"),
            # Impostos principais
            "ICMS_orig": icms_origem,
            "ICMS_CST_CSOSN": icms_cst,
            "ICMS_pICMS": icms_aliq,
            "PIS_CST": pis_cst,
            "PIS_pPIS": pis_aliq,
            "COFINS_CST": cof_cst,
            "COFINS_pCOFINS": cof_aliq,
        }
        itens_out.append(item_dict)

    return header, itens_out, None


def write_excel(df_notas, df_itens) -> bytes:
    """Gera um Excel com duas abas, formatado."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as xw:
        # Notas
        df_notas.to_excel(xw, index=False, sheet_name="Notas")
        wsN = xw.sheets["Notas"]

        # Itens
        df_itens.to_excel(xw, index=False, sheet_name="Itens")
        wsI = xw.sheets["Itens"]

        wb = xw.book
        fmt_header = wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1})
        fmt_num2 = wb.add_format({"num_format": "#,##0.00"})
        fmt_int = wb.add_format({"num_format": "0"})

        # Autosize (simples): largura baseada no tamanho do header
        for sheet, df in [(wsN, df_notas), (wsI, df_itens)]:
            for col_idx, col in enumerate(df.columns):
                width = max(10, min(50, len(str(col)) + 2))
                sheet.set_column(col_idx, col_idx, width)
            # Header format
            sheet.set_row(0, None, fmt_header)

        # Formatações numéricas mais comuns
        num_cols_notas = ["vBC","vICMS","vICMSDeson","vFCP","vBCST","vST","vProd","vFrete","vSeg","vDesc","vII","vIPI","vPIS","vCOFINS","vOutro","vNF","vPag_total"]
        for c in num_cols_notas:
            if c in df_notas.columns:
                j = df_notas.columns.get_loc(c)
                wsN.set_column(j, j, 14, fmt_num2)

        num_cols_itens = ["qCom","vUnCom","vProd","qTrib","vUnTrib","vDesc_item","ICMS_pICMS","PIS_pPIS","COFINS_pCOFINS"]
        for c in num_cols_itens:
            if c in df_itens.columns:
                j = df_itens.columns.get_loc(c)
                wsI.set_column(j, j, 14, fmt_num2)

        # colunas claramente inteiras
        for c in ["Série", "Número", "nItem"]:
            for ws, df in [(wsN, df_notas), (wsI, df_itens)]:
                if c in df.columns:
                    j = df.columns.get_loc(c)
                    ws.set_column(j, j, 10, fmt_int)

    return output.getvalue()


# ========= UI =========
st.title("📦 Importar milhares de XML NF-e → 📊 Excel")
st.markdown(
    """
    **Como usar:**  
    1) Comprima a pasta de XML em um arquivo **.zip** (ou selecione vários `.xml`).  
    2) Anexe aqui.  
    3) Clique em **Processar** para gerar o Excel com as abas **Notas** e **Itens**.
    """
)

arquivos = st.file_uploader(
    "Anexe um .zip com XML ou selecione múltiplos .xml",
    type=["zip", "xml"],
    accept_multiple_files=True,
)

colA, colB = st.columns([1, 2])
with colA:
    processar = st.button("🚀 Processar")

# ========= Processamento =========
if processar:
    if not arquivos:
        st.warning("Anexe ao menos um arquivo .zip ou .xml.")
        st.stop()

    headers = []
    itens = []
    erros = []

    total_xmls = 0

    progress = st.progress(0, text="Lendo arquivos...")

    # Coleta todos os XML bytes a partir dos uploads
    xml_blobs = []

    for f in arquivos:
        name = f.name.lower()
        if name.endswith(".zip"):
            try:
                z = zipfile.ZipFile(f)
                for info in z.infolist():
                    if info.filename.lower().endswith(".xml") and not info.is_dir():
                        with z.open(info) as zf:
                            xml_blobs.append(zf.read())
            except zipfile.BadZipFile:
                erros.append((name, "ZIP corrompido"))
        elif name.endswith(".xml"):
            xml_blobs.append(f.read())

    total_xmls = len(xml_blobs)
    if total_xmls == 0:
        st.error("Nenhum XML encontrado dentro dos arquivos enviados.")
        st.stop()

    for i, xml_bytes in enumerate(xml_blobs, start=1):
        header, itens_out, err = parse_nfe_xml(xml_bytes)
        if err:
            erros.append((f"xml_{i}", err))
        else:
            headers.append(header)
            itens.extend(itens_out)

        progress.progress(i / total_xmls, text=f"Processando XML {i}/{total_xmls}...")

    progress.empty()

    if not headers:
        st.error("Não foi possível extrair nenhuma NF-e válida dos arquivos.")
        if erros:
            with st.expander("Erros de leitura"):
                for nome, msg in erros:
                    st.write(f"• {nome}: {msg}")
        st.stop()

    # ===== DataFrames finais =====
    df_notas = pd.DataFrame(headers)
    df_itens = pd.DataFrame(itens)

    # Remove duplicadas por chave (mantém a última lida)
    if "Chave" in df_notas.columns:
        df_notas = df_notas.drop_duplicates(subset=["Chave"], keep="last")

    # Preview
    st.success(f"Extraídas **{len(df_notas)} notas** e **{len(df_itens)} itens** de **{total_xmls} XML**.")
    st.subheader("Amostra — Notas")
    st.dataframe(df_notas.head(20), use_container_width=True, hide_index=True)
    st.subheader("Amostra — Itens")
    st.dataframe(df_itens.head(20), use_container_width=True, hide_index=True)

    # Excel para download
    bin_xlsx = write_excel(df_notas, df_itens)
    st.download_button(
        label="💾 Baixar Excel (Notas + Itens)",
        data=bin_xlsx,
        file_name="XML_NFe_Importados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if erros:
        with st.expander("⚠️ XMLs com erro (clique para ver)"):
            for nome, msg in erros:
                st.write(f"• {nome}: {msg}")

# ===== Rodapé/observações =====
with st.expander("ℹ️ Campos extraídos / Observações"):
    st.markdown(
        """
- **Notas (cabeçalho)**: Chave, Modelo, Série, Número, Emissão, tpNF, Natureza da Operação, cMunFG, UF Emitente,  
  Emit_CNPJ/CPF, Emit_Nome, Emit_IE, Dest_CNPJ/CPF, Dest_Nome, Dest_IE, **Totais** (vBC, vICMS, vST, vProd, vFrete, vDesc, vNF, etc.), **vPag_total**, modFrete, cStat, xMotivo.
- **Itens**: Chave, nItem, cProd, xProd, NCM, CFOP, uCom, qCom, vUnCom, vProd, (uTrib, qTrib, vUnTrib), vDesc_item, indTot,  
  ICMS (origem, CST/CSOSN, pICMS), PIS (CST, pPIS), COFINS (CST, pCOFINS).
- O parser usa o namespace oficial da **NF-e**. Ele ignora eventos/CC-e; lê **NFe/NFeProc** padrão SEFAZ.
- Para **milhares de XML**, recomendo anexar um **.zip** (fica bem mais rápido e estável no navegador).
- Se quiser, dá para acrescentar outras tags (ex.: IPI por item, informação de **canc**/denegada via cStat), é só me falar quais.
        """
    )
