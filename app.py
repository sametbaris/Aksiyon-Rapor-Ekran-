import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Fiyat Analizi", page_icon="⚖️", layout="wide")

SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0"
SHEET_NAME = "Guncel"

# ================= MODERN CSS (ESNEK GENİŞLİK & ZARİF TASARIM) =================
st.markdown("""
<style>
    /* Tablo konteynırını yatay kaydırmaya izin verecek hale getirme */
    .table-container {
        width: 100%;
        margin-top: 20px;
        overflow-x: auto; /* Tablo sığmazsa yatay kaydırma çubuğu çıkar */
    }
    
    .custom-table {
        width: 100%;
        table-layout: auto; /* Hücre genişlikleri içeriğe göre otomatik ayarlanır */
        border-collapse: separate;
        border-spacing: 0 4px;
        font-family: 'Inter', sans-serif;
    }
    
    .custom-table th {
        color: #888;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 1px;
        padding: 15px 20px;
        text-align: left;
        white-space: nowrap;
    }
    
    .custom-table td {
        padding: 12px 20px;
        text-align: left;
        background-color: transparent;
        color: #333;
        font-size: 14px;
        border: none;
        /* METİNLERİN ALTA KAYMASINI ENGELLER: */
        white-space: nowrap; 
        transition: background-color 0.2s ease;
    }

    /* KÖŞELİ ÇERÇEVE YERİNE ZARİF ARKA PLAN HOVER */
    .custom-table tr:hover td {
        background-color: #f4f4f4 !important; /* Çok hafif gri bir vurgu */
        cursor: default;
    }

    .stTextInput input {
        border-radius: 12px !important;
        border: 1px solid #eee !important;
        padding: 10px 20px !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= YARDIMCI FONKSİYONLAR =================
def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() == "nan": return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").strip()
    clean = re.sub(r"[^\d.,]", "", val_str)
    if not clean: return None
    if "." in clean and "," in clean: clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean: clean = clean.replace(",", ".")
    try: return float(clean)
    except: return None

@st.cache_data(ttl=60) 
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^Unnamed', case=False)]
        df = df.fillna("")
        return df
    except: return None

# ================= RENDER MOTORU =================
def display_styled_table(df):
    target_cols = ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    
    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for col in df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for col in df.columns:
            val = str(row[col])
            inner_style = "padding: 6px 12px; display: inline-block;"
            
            # Braun Shop Kıyaslama Mantığı
            if col in target_cols:
                ref_val = parse_price(row["Braun Shop"])
                curr_val = parse_price(val)
                if ref_val and curr_val:
                    if curr_val == ref_val:
                        inner_style += 'background-color: #e8f5e9; color: #2e7d32; border-radius: 20px; font-weight: 500;'
                    else:
                        inner_style += 'background-color: #ffebee; color: #c62828; border-radius: 20px; font-weight: 500;'
            
            display_val = val if val.lower() != "nan" else ""
            html += f'<td><span style="{inner_style}">{display_val}</span></td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================= ARAYÜZ =================
st.title("📊 Fiyat Analiz Merkezi")

df = load_data()

if df is not None:
    search = st.text_input("🔍 Listede arama yapın...")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    display_styled_table(df)

    # Excel İndirme
    now = datetime.now().strftime("%d.%m.%Y_%H-%M")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    st.write("<br>", unsafe_allow_html=True)
    st.download_button(
        label="📥 Güncel Verileri Excel'e Aktar",
        data=output.getvalue(),
        file_name=f"Fiyat_Raporu_{now}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.error("Google Sheets'e ulaşılamadı.")
