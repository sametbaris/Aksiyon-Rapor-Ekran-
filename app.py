import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
import requests

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Fiyat Analizi", page_icon="⚖️", layout="wide")

SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0"
SHEET_NAME = "Guncel"

# ================= ULTRA MODERN CSS (HAP ODAKLI) =================
st.markdown("""
<style>
    .table-container { width: 100%; margin-top: 20px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 10px; font-family: 'Inter', sans-serif; border: none; }
    .custom-table th { color: #aaa; font-weight: 500; text-transform: uppercase; font-size: 11px; letter-spacing: 1.5px; padding: 10px 20px; text-align: left; border: none; }
    .custom-table td { padding: 8px 20px; text-align: left; border: none; white-space: nowrap; }

    /* HÜCRE İÇİNDEKİ HAP (SPAN) TASARIMI */
    .data-pill {
        padding: 6px 14px;
        display: inline-block;
        border-radius: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: 2px solid transparent; /* Normalde görünmez çerçeve */
    }

    /* SADECE HAP ÜZERİNE GELİNDİĞİNDE TETİKLENEN EFEKT */
    .data-pill:hover {
        transform: scale(1.1); /* Sadece hap %10 büyür */
        box-shadow: 0px 6px 15px rgba(0,0,0,0.1);
        cursor: pointer;
        filter: brightness(0.95); /* Hafif belirginleşme */
        z-index: 10;
    }

    .update-badge {
        text-align: right; color: #7f8c8d; font-size: 12px;
        background: #f8f9fa; padding: 6px 16px; border-radius: 30px;
        display: inline-block; float: right; border: 1px solid #eee;
    }
    .stTextInput input { border-radius: 50px !important; padding: 12px 25px !important; }
</style>
""", unsafe_allow_html=True)

# ================= FONKSİYONLAR =================
def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", ""]: return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").replace(".", "").replace(",", ".").strip()
    clean = re.sub(r"[^\d.]", "", val_str)
    try: return float(clean)
    except: return None

@st.cache_data(ttl=60)
def get_last_update():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&range=N1"
    try:
        response = requests.get(url)
        return response.text.replace('"', '').strip()
    except: return "Bilinmiyor"

@st.cache_data(ttl=60) 
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}&range=A:M"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^Unnamed', case=False)]
        blacklist = ["Pazaryeri", "Son Güncelleme"]
        df = df.drop(columns=[c for c in blacklist if c in df.columns])
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
            display_val = "" if val.lower() in ["nan", "none", ""] else val
            
            # Dinamik Stil Belirleme
            pill_style = ""
            if col in target_cols and "Braun Shop" in df.columns:
                ref_val = parse_price(row["Braun Shop"])
                curr_val = parse_price(display_val)
                if ref_val and curr_val:
                    if curr_val == ref_val:
                        pill_style = 'background-color: #e8f5e9; color: #2e7d32; font-weight: 600;'
                    else:
                        pill_style = 'background-color: #ffebee; color: #c62828; font-weight: 600;'
            
            # Veri boş değilse ama renklendirilmemişse (Standart veri)
            if not pill_style and display_val != "":
                pill_style = 'background-color: #f8f9fa; color: #333;'

            html += f'<td><span class="data-pill" style="{pill_style}">{display_val}</span></td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================= ÜST PANEL VE ANA İÇERİK =================
col_title, col_update = st.columns([2, 1])
with col_title: st.title("📊 Fiyat Analiz Merkezi")
with col_update:
    last_update = get_last_update()
    st.markdown(f'<div class="update-badge">🔄 Son Güncelleme: {last_update}</div>', unsafe_allow_html=True)

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
