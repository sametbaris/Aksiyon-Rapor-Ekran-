import streamlit as st
import pandas as pd
import re
import requests
import base64
import os

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Fiyat Analiz Merkezi", page_icon="⚖️", layout="wide")
SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0"

# ================= LOGO YÜKLEME =================
def get_base64_logo(file_name):
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

# ================= MODERN CSS =================
st.markdown("""
<style>
    :root { --text-main: inherit; --header-color: #888; --pill-default-bg: rgba(128, 128, 128, 0.1); }
    .table-container { width: 100%; margin-top: 20px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 10px; font-family: 'Inter', sans-serif; border: none; }
    .header-logo { height: 28px; width: auto; max-width: 120px; object-fit: contain; }
    .custom-table th { color: var(--header-color); font-weight: 500; text-transform: uppercase; font-size: 11px; padding: 10px 20px; text-align: center; }
    .custom-table td { padding: 8px 20px; text-align: center; border: none; white-space: nowrap; color: var(--text-main); }
    
    /* Hücre Link Yapısı */
    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s ease; }
    .data-pill:hover { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
    .stTextInput input { border-radius: 50px !important; }
    
    .update-badge { text-align: right; color: var(--header-color); font-size: 12px; background: var(--pill-default-bg); padding: 6px 16px; border-radius: 30px; display: inline-block; float: right; }
</style>
""", unsafe_allow_html=True)

# ================= VERİ YÜKLEME VE MERGE (BİRLEŞTİRME) =================
@st.cache_data(ttl=60)
def load_data():
    # 1. Guncel sayfasını çek (Fiyatlar)
    fiyat_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Guncel&range=A:M"
    # 2. Mapping sayfasını çek (Linkler)
    mapping_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Sayfa1" # Lokal kodunda 'Sayfa1' olarak geçiyor
    
    try:
        df_fiyat = pd.read_csv(fiyat_url)
        df_map = pd.read_csv(mapping_url)
        
        # Kolon isimlerini temizle
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        df_map.columns = [c.strip() for c in df_map.columns]
        
        # Eşleşme için Barkod sütunlarını ayarla
        # Senin Mapping dosyasında "Ürün Barkodu", Guncel sayfasında "Barkod" olabilir.
        if "Ürün Barkodu" in df_map.columns:
            df_map = df_map.rename(columns={"Ürün Barkodu": "Barkod"})
            
        df_fiyat["Barkod"] = df_fiyat["Barkod"].astype(str).str.split('.').str[0]
        df_map["Barkod"] = df_map["Barkod"].astype(str).str.split('.').str[0]
        
        # Sadece ihtiyacımız olan link kolonlarını alalım (Lokal kodundaki isimler)
        link_cols = ["Barkod", "TY", "HB", "AMZ", "MM", "TKNS", "VTN"]
        df_map = df_map[[c for c in link_cols if c in df_map.columns]]
        
        # İki tabloyu Barkod üzerinden birleştir
        df_final = pd.merge(df_fiyat, df_map, on="Barkod", how="left")
        return df_final.fillna("")
    except Exception as e:
        st.error(f"Veri hatası: {e}")
        return None

@st.cache_data(ttl=60)
def get_update_time():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&range=N1"
    try: return requests.get(url).text.replace('"', '').strip()
    except: return "Bilinmiyor"

# ================= RENDER MOTORU =================
def display_styled_table(df):
    # Ekranda gösterilecek teknik ve pazar kolonları
    display_cols = ["Marka", "Ürün Adı", "Barkod", "Ürün Kodu", "Alt Grup", "Aksiyon", "Braun Shop", 
                    "Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    
    # Eşleşme Haritası: Pazar Kolonu -> Mapping Dosyasındaki Link Sütunu
    link_map = {
        "Media Markt": "MM", "Teknosa": "TKNS", "Vatan": "VTN",
        "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ"
    }

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
            
            # Renklendirme (Braun Shop kıyaslaması)
            if col in link_map.keys() and "Braun Shop" in df.columns:
                try:
                    ref = float(str(row["Braun Shop"]).replace(".","").replace(",","."))
                    curr = float(display_val.replace(".","").replace(",","."))
                    if curr == ref: pill_style = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                    else: pill_style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
                except: pill_style = 'background-color: var(--pill-default-bg);'
            elif any(x in col.lower() for x in ["barkod", "kodu", "grup", "marka"]):
                pill_style = 'background-color: transparent;'
            else:
                pill_style = 'background-color: var(--pill-default-bg);'

            # LİNK GÖMME (Mapping'den gelen TY, HB, MM vb. kullanılarak)
            link_col_name = link_map.get(col)
            url = str(row.get(link_col_name, ""))
            
            if url and url != "" and display_val != "":
                # Eğer TY kısmında sadece ürün ID'si varsa, başına Trendyol URL'i eklenebilir. 
                # Ama full link varsa direkt url kullanılır.
                cell_content = f'<a href="{url}" target="_blank" class="data-link"><span class="data-pill" style="{pill_style}">{display_val}</span></a>'
            else:
                cell_content = f'<span class="data-pill" style="{pill_style}">{display_val}</span>'
                
            html += f'<td>{cell_content}</td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================= ANA AKIŞ =================
col_title, col_update = st.columns([2, 1])
with col_title: st.title("📊 Fiyat Analiz Merkezi")
with col_update: st.markdown(f'<div class="update-badge">🔄 {get_update_time()}</div>', unsafe_allow_html=True)

df = load_data()
if df is not None:
    search = st.text_input("🔍 Ürün adı veya barkod ile hızlı arama...")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    display_styled_table(df)
