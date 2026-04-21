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
    .table-container { width: 100%; margin-top: 20px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 8px; font-family: 'Inter', sans-serif; border: none; }
    .header-logo { height: 28px; width: auto; max-width: 120px; object-fit: contain; }
    .custom-table th { color: #888; font-weight: 500; text-transform: uppercase; font-size: 11px; padding: 10px 20px; text-align: center; }
    .custom-table td { padding: 4px 10px; text-align: center; border: none; white-space: nowrap; }
    
    /* Hücre içindeki link ve hap stili */
    .data-link { text-decoration: none; color: inherit; display: inline-block; }
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s ease; }
    .data-pill:hover { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# ================= VERİ ÇEKME VE BİRLEŞTİRME =================
@st.cache_data(ttl=60)
def load_and_merge_data():
    # 1. Ana Fiyat Tablosunu Çek (Guncel Sekmesi)
    fiyat_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Guncel&range=A:M"
    # 2. Linklerin Olduğu Mapping Sekmesini Çek
    mapping_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Mapping"
    
    try:
        df_fiyat = pd.read_csv(fiyat_url)
        df_map = pd.read_csv(mapping_url)
        
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        df_map.columns = [c.strip() for c in df_map.columns]
        
        # Mapping dosyasındaki başlıkları temizle (Barkod sütunu ismi eşleşmeli)
        # Senin dosyanda 'Ürün Barkodu' olarak geçiyor olabilir, Guncel'de 'Barkod'.
        # Bunları standartlaştırıyoruz:
        if "Ürün Barkodu" in df_map.columns:
            df_map = df_map.rename(columns={"Ürün Barkodu": "Barkod"})
            
        # Barkodları string yapıyoruz ki eşleşme hatasız olsun
        df_fiyat["Barkod"] = df_fiyat["Barkod"].astype(str).str.split('.').str[0]
        df_map["Barkod"] = df_map["Barkod"].astype(str).str.split('.').str[0]
        
        # Verileri Barkod üzerinden birleştir
        full_df = pd.merge(df_fiyat, df_map, on="Barkod", how="left")
        return full_df.fillna("")
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return None

# ================= RENDER MOTORU =================
def display_styled_table(df):
    # Ana sütunlar
    display_cols = ["Marka", "Ürün Adı", "Barkod", "Ürün Kodu", "Alt Grup", "Aksiyon", "Braun Shop", 
                    "Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    
    # Mağaza İsmi -> Mapping Dosyasındaki Link Sütun İsmi
    # (Senin dosyanın kolon isimlerine göre güncelledim: TY, HB, AMZ, MM, TKNS, VTN)
    link_mapping = {
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
            
            # Fiyat Renklendirme (Braun Shop ile kıyaslama)
            if col in link_mapping.keys() and "Braun Shop" in df.columns:
                try:
                    ref = float(str(row["Braun Shop"]).replace(".","").replace(",","."))
                    curr = float(display_val.replace(".","").replace(",","."))
                    if curr == ref: pill_style = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                    else: pill_style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
                except: pass
            
            # Teknik Kolon Şeffaflığı
            if not pill_style and any(x in col.lower() for x in ["barkod", "kodu", "grup", "marka"]):
                pill_style = 'background-color: transparent;'
            elif not pill_style:
                pill_style = 'background-color: rgba(128, 128, 128, 0.1);'

            # LİNK OLUŞTURMA
            link_col = link_mapping.get(col)
            link_val = str(row.get(link_col, "")) if link_col else ""
            
            # Eğer link hücresinde veri varsa linki oluştur
            if link_val and display_val:
                # Eğer mapping dosyasında sadece ID varsa (örn: 12345), Trendyol için başına URL ekleyebilirsin
                # Ama dosyanın içinde tam link varsa direkt link_val kullanıyoruz
                html_cell = f'<td><a href="{link_val}" target="_blank" class="data-link"><span class="data-pill" style="{pill_style}">{display_val}</span></a></td>'
            else:
                html_cell = f'<td><span class="data-pill" style="{pill_style}">{display_val}</span></td>'
                
            html += html_cell
        html += '</tr>'
    
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================= ANA AKIŞ =================
st.title("📊 Fiyat Analiz Merkezi")
df = load_and_merge_data()
if df is not None:
    search = st.text_input("🔍 Hızlı arama...")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    display_styled_table(df)
