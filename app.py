import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
import requests
import base64
import os

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Fiyat Analizi", page_icon="⚖️", layout="wide")

SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0"
SHEET_NAME = "Guncel"

# ================= LOGO YÜKLEME SİHRİBAZI =================
def get_base64_logo(file_name):
    """Logos klasöründeki resimleri base64 formatına çevirir."""
    # Dosya yolunu oluştur (Klasör adının 'logos' olduğundan emin ol)
    file_path = os.path.join("logos", file_name)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    return None

# Sütun isimlerini dosya isimleriyle eşleştiriyoruz
# Not: Resim dosyalarının isimleri tam olarak buradakilerle (küçük harf) aynı olmalı.
LOGOS = {
    "Media Markt": get_base64_logo("mediamarkt.png"),
    "Teknosa": get_base64_logo("teknosa.png"),
    "Vatan": get_base64_logo("vatan.png"),
    "Trendyol": get_base64_logo("trendyol.png"),
    "Hepsiburada": get_base64_logo("hepsiburada.png"),
    "Amazon": get_base64_logo("amazon.png"),
    "Braun Shop": get_base64_logo("braunshop.png")
}

# ================= SMART DARK/LIGHT CSS =================
st.markdown("""
<style>
    :root { --header-color: #888; --pill-default-bg: rgba(128, 128, 128, 0.1); }
    .table-container { width: 100%; margin-top: 20px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 10px; font-family: 'Inter', sans-serif; border: none; }
    
    /* Logo Boyutu ve Zarifliği */
    .header-logo { 
        height: 28px; 
        width: auto; 
        max-width: 120px; 
        object-fit: contain; 
        filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.1));
    }
    
    .custom-table th { 
        color: var(--header-color); font-weight: 500; text-transform: uppercase; 
        font-size: 11px; letter-spacing: 1.5px; padding: 10px 20px; text-align: center; 
    }
    .custom-table td { padding: 8px 20px; text-align: center; border: none; white-space: nowrap; }
    
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s ease; }
    .data-pill:hover { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
    
    .update-badge { 
        text-align: right; color: var(--header-color); font-size: 12px; 
        background: var(--pill-default-bg); padding: 6px 16px; border-radius: 30px; 
        display: inline-block; float: right; border: 1px solid rgba(128, 128, 128, 0.1); 
    }
    .stTextInput input { border-radius: 50px !important; }
</style>
""", unsafe_allow_html=True)

# ================= YARDIMCI FONKSİYONLAR =================
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
        logo_data = LOGOS.get(col)
        if logo_data:
            html += f'<th><img src="{logo_data}" class="header-logo" title="{col}"></th>'
        else:
            html += f'<th>{col}</th>'
    
    html += '</tr></thead><tbody>'
    for _, row in df.iterrows():
        html += '<tr>'
        for col in df.columns:
            val = str(row[col])
            display_val = "" if val.lower() in ["nan", "none", ""] else val
            pill_style = ""
            if col in target_cols and "Braun Shop" in df.columns:
                ref_val = parse_price(row["Braun Shop"])
                curr_val = parse_price(display_val)
                if ref_val and curr_val:
                    if curr_val == ref_val: pill_style = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                    else: pill_style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
            
            if not pill_style and display_val != "":
                if any(x in col.lower() for x in ["barkod", "kodu", "grup", "marka", "ürün adı"]): pill_style = 'background-color: transparent;'
                else: pill_style = 'background-color: var(--pill-default-bg);'
            html += f'<td><span class="data-pill" style="{pill_style}">{display_val}</span></td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================= ÜST PANEL VE AKIŞ =================
col_title, col_update = st.columns([2, 1])
with col_title: st.title("📊 Fiyat Analiz Merkezi")
with col_update:
    last_update = get_last_update()
    st.markdown(f'<div class="update-badge">🔄 Son Güncelleme: {last_update}</div>', unsafe_allow_html=True)

df = load_data()
if df is not None:
    search = st.text_input("🔍 Hızlı arama (Ürün, Barkod, SKU)...")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    display_styled_table(df)
    
    now = datetime.now().strftime("%d.%m.%Y_%H-%M")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.write("<br>", unsafe_allow_html=True)
    st.download_button(label="📥 Verileri Excel Olarak İndir", data=output.getvalue(), file_name=f"Rapor_{now}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
