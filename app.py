import streamlit as st
import pandas as pd
import re
import requests
import base64
import os
import io
from datetime import datetime

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Fiyat Analiz Merkezi", page_icon="⚖️", layout="wide")

# Bilgiler
SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0"
MAPPING_FILE = "Aksiyon_Mapping.xlsx"

# ================= LOGO YÜKLEME =================
def get_base64_logo(file_name):
    file_path = os.path.join("logos", file_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except: return None
    return None

LOGOS = {
    "Media Markt": get_base64_logo("mediamarkt.png"),
    "Teknosa": get_base64_logo("teknosa.png"),
    "Vatan": get_base64_logo("vatan.png"),
    "Trendyol": get_base64_logo("trendyol.png"),
    "Hepsiburada": get_base64_logo("hepsiburada.png"),
    "Amazon": get_base64_logo("amazon.png"),
    "Braun Shop": get_base64_logo("braunshop.png")
}

# ================= CSS =================
st.markdown("""
<style>
    :root { --text-main: inherit; --header-color: #888; --pill-default-bg: rgba(128, 128, 128, 0.1); }
    .table-container { width: 100%; margin-top: 20px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 10px; font-family: 'Inter', sans-serif; border: none; }
    .header-logo { height: 28px; width: auto; max-width: 120px; object-fit: contain; }
    .custom-table th { color: var(--header-color); font-weight: 500; text-transform: uppercase; font-size: 11px; padding: 10px 20px; text-align: center; }
    .custom-table td { padding: 8px 20px; text-align: center; border: none; white-space: nowrap; color: var(--text-main); }
    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s ease; }
    .data-pill:hover { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
    .update-badge { text-align: right; color: var(--header-color); font-size: 12px; background: var(--pill-default-bg); padding: 6px 16px; border-radius: 30px; display: inline-block; float: right; }
    .stTextInput input { border-radius: 50px !important; }
</style>
""", unsafe_allow_html=True)

# ================= VERİ YÜKLEME =================
def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", ""]: return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").replace(".", "").replace(",", ".").strip()
    clean = re.sub(r"[^\d.]", "", val_str)
    try: return float(clean)
    except: return None

@st.cache_data(ttl=60)
def load_and_merge_data():
    fiyat_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Guncel&range=A:M"
    try:
        df_fiyat = pd.read_csv(fiyat_url)
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        df_fiyat["Barkod"] = df_fiyat["Barkod"].astype(str).str.split('.').str[0]

        # MAPPING DOSYASI KONTROLÜ
        if os.path.exists(MAPPING_FILE):
            try:
                df_map = pd.read_excel(MAPPING_FILE, engine='openpyxl')
                df_map.columns = [c.strip() for c in df_map.columns]
                
                if "Ürün Barkodu" in df_map.columns:
                    df_map = df_map.rename(columns={"Ürün Barkodu": "Barkod"})
                
                df_map["Barkod"] = df_map["Barkod"].astype(str).str.split('.').str[0]
                link_cols = ["Barkod", "TY", "HB", "AMZ", "MM", "TKNS", "VTN"]
                df_map = df_map[[c for c in link_cols if c in df_map.columns]]
                
                df_final = pd.merge(df_fiyat, df_map, on="Barkod", how="left")
                return df_final.fillna("")
            except Exception as e:
                st.warning(f"Mapping dosyası okunamadı (Linkler devre dışı): {e}")
                return df_fiyat.fillna("")
        else:
            st.info("Aksiyon_Mapping.xlsx bulunamadı. Sadece fiyatlar gösteriliyor.")
            return df_fiyat.fillna("")
            
    except Exception as e:
        st.error(f"Google Sheets bağlantı hatası: {e}")
        return None

# ================= RENDER =================
def display_styled_table(df):
    display_cols = ["Marka", "Ürün Adı", "Barkod", "Ürün Kodu", "Alt Grup", "Aksiyon", "Braun Shop", 
                    "Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    
    link_mapping = {"Media Markt": "MM", "Teknosa": "TKNS", "Vatan": "VTN", "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ"}

    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for col in display_cols:
        if col in df.columns:
            logo = LOGOS.get(col)
            html += f'<th><img src="{logo}" class="header-logo"></th>' if logo else f'<th>{col}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for col in display_cols:
            if col not in df.columns: continue
            val = str(row[col])
            display_val = "" if val.lower() in ["nan", "none", ""] else val
            pill_style = ""
            
            if col in link_mapping.keys() and "Braun Shop" in df.columns:
                ref_val = parse_price(row["Braun Shop"])
                curr_val = parse_price(display_val)
                if ref_val and curr_val:
                    if curr_val == ref_val: pill_style = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                    else: pill_style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
            
            if not pill_style and display_val != "":
                if any(x in col.lower() for x in ["barkod", "kodu", "grup", "marka"]): pill_style = 'background-color: transparent;'
                else: pill_style = 'background-color: var(--pill-default-bg);'

            link_col = link_mapping.get(col)
            url = str(row.get(link_col, ""))
            
            if url and url not in ["", "nan", "None"] and display_val:
                cell = f'<td><a href="{url}" target="_blank" class="data-link"><span class="data-pill" style="{pill_style}">{display_val}</span></a></td>'
            else:
                cell = f'<td><span class="data-pill" style="{pill_style}">{display_val}</span></td>'
            html += cell
        html += '</tr>'
    
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================= MAIN =================
df = load_and_merge_data()

col_t, col_u = st.columns([2, 1])
with col_t: st.title("📊 Fiyat Analiz Merkezi")
with col_u:
    url_u = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&range=N1"
    try: 
        up_time = requests.get(url_u).text.replace('"', '').strip()
        st.markdown(f'<div class="update-badge">🔄 {up_time}</div>', unsafe_allow_html=True)
    except: pass

if df is not None:
    search = st.text_input("🔍 Hızlı arama...")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    display_styled_table(df)
