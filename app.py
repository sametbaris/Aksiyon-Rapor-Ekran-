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

# Google Sheets Bilgileri
SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0"
MAPPING_FILE = "Aksiyon_Mapping.xlsx" # GitHub'a yükleyeceğin dosya adı

# ================= LOGO YÜKLEME SİHRİBAZI =================
def get_base64_logo(file_name):
    """logos klasöründeki resimleri base64 formatına çevirir."""
    file_path = os.path.join("logos", file_name)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
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

# ================= ULTRA MODERN CSS =================
st.markdown("""
<style>
    :root { --text-main: inherit; --header-color: #888; --pill-default-bg: rgba(128, 128, 128, 0.1); }
    .table-container { width: 100%; margin-top: 20px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 10px; font-family: 'Inter', sans-serif; border: none; }
    
    .header-logo { height: 28px; width: auto; max-width: 120px; object-fit: contain; }
    
    .custom-table th { color: var(--header-color); font-weight: 500; text-transform: uppercase; font-size: 11px; letter-spacing: 1.5px; padding: 10px 20px; text-align: center; }
    .custom-table td { padding: 8px 20px; text-align: center; border: none; white-space: nowrap; color: var(--text-main); }
    
    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    
    .data-pill:hover { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
    
    .update-badge { text-align: right; color: var(--header-color); font-size: 12px; background: var(--pill-default-bg); padding: 6px 16px; border-radius: 30px; display: inline-block; float: right; border: 1px solid rgba(128, 128, 128, 0.1); }
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
def get_update_time():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&range=N1"
    try:
        res = requests.get(url)
        return res.text.replace('"', '').strip()
    except: return "Bilinmiyor"

@st.cache_data(ttl=60)
def load_and_merge_data():
    # 1. Google Sheets'ten Canlı Fiyatları Al
    fiyat_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Guncel&range=A:M"
    
    try:
        df_fiyat = pd.read_csv(fiyat_url)
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        
        # 2. GitHub'daki Excel'den Mapping'i (Linkleri) Al
        if os.path.exists(MAPPING_FILE):
            df_map = pd.read_excel(MAPPING_FILE, sheet_name="Sayfa1")
            df_map.columns = [c.strip() for c in df_map.columns]
            
            # Sütun isimlerini standartlaştır (Mapping'de 'Ürün Barkodu' ise 'Barkod' yap)
            if "Ürün Barkodu" in df_map.columns:
                df_map = df_map.rename(columns={"Ürün Barkodu": "Barkod"})
            
            # Barkodları eşleşme için string yap
            df_fiyat["Barkod"] = df_fiyat["Barkod"].astype(str).str.split('.').str[0]
            df_map["Barkod"] = df_map["Barkod"].astype(str).str.split('.').str[0]
            
            # Link kolonlarını seç (Senin dosyandaki TY, HB, AMZ, MM, TKNS, VTN)
            link_cols = ["Barkod", "TY", "HB", "AMZ", "MM", "TKNS", "VTN"]
            df_map = df_map[[c for c in link_cols if c in df_map.columns]]
            
            # Barkod üzerinden birleştir
            df_final = pd.merge(df_fiyat, df_map, on="Barkod", how="left")
            return df_final.fillna("")
        
        return df_fiyat.fillna("")
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return None

# ================= RENDER MOTORU =================
def display_styled_table(df):
    # Ekranda gösterilecek ana kolonlar
    display_cols = ["Marka", "Ürün Adı", "Barkod", "Ürün Kodu", "Alt Grup", "Aksiyon", "Braun Shop", 
                    "Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    
    # Mağaza Başlığı -> Mapping Link Sütunu Eşleşmesi
    link_mapping = {
        "Media Markt": "MM", "Teknosa": "TKNS", "Vatan": "VTN",
        "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ"
    }

    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for col in display_cols:
        if col in df.columns:
            logo = LOGOS.get(col)
            html += f'<th><img src="{logo}" class="header-logo" title="{col}"></th>' if logo else f'<th>{col}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for col in display_cols:
            if col not in df.columns: continue
            
            val = str(row[col])
            display_val = "" if val.lower() in ["nan", "none", ""] else val
            pill_style = ""
            
            # Fiyat Renklendirme
            if col in link_mapping.keys() and "Braun Shop" in df.columns:
                ref_val = parse_price(row["Braun Shop"])
                curr_val = parse_price(display_val)
                if ref_val and curr_val:
                    if curr_val == ref_val: pill_style = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                    else: pill_style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
            
            # Şeffaflık ve Stil
            if not pill_style and display_val != "":
                if any(x in col.lower() for x in ["barkod", "kodu", "grup", "marka"]): pill_style = 'background-color: transparent;'
                else: pill_style = 'background-color: var(--pill-default-bg);'

            # LINK GÖMME
            link_col_name = link_mapping.get(col)
            url = str(row.get(link_col_name, ""))
            
            if url and url != "" and display_val != "":
                cell_html = f'<td><a href="{url}" target="_blank" class="data-link"><span class="data-pill" style="{pill_style}">{display_val}</span></a></td>'
            else:
                cell_html = f'<td><span class="data-pill" style="{pill_style}">{display_val}</span></td>'
                
            html += cell_html
        html += '</tr>'
    
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================= ANA PANEL =================
col_title, col_update = st.columns([2, 1])
with col_title: st.title("📊 Fiyat Analiz Merkezi")
with col_update:
    st.markdown(f'<div class="update-badge">🔄 {get_update_time()}</div>', unsafe_allow_html=True)

df_final = load_and_merge_data()
if df_final is not None:
    search = st.text_input("🔍 Ürün adı veya barkod ile hızlı arama...")
    if search:
        df_final = df_final[df_final.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    
    display_styled_table(df_final)

    # Excel İndir (Link kolonlarını temizleyip sadece ilk 13 kolonu verir)
    st.write("<br>", unsafe_allow_html=True)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_final[df_final.columns[:13]].to_excel(writer, index=False)
    
    st.download_button(label="📥 Verileri Excel Olarak İndir", data=output.getvalue(), file_name="Rapor.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
