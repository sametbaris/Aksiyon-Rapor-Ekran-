import streamlit as st
import pandas as pd
import re
import requests
import base64
import os
import io

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Fiyat Analiz Merkezi", page_icon="⚖️", layout="wide")

# Ayarlar
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
    :root { --header-color: #888; --pill-default-bg: rgba(128, 128, 128, 0.1); }
    .table-container { width: 100%; margin-top: 20px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 8px; font-family: 'Inter', sans-serif; border: none; }
    .header-logo { height: 28px; width: auto; max-width: 120px; object-fit: contain; }
    .custom-table th { color: var(--header-color); font-weight: 500; text-transform: uppercase; font-size: 11px; padding: 10px 20px; text-align: center; }
    .custom-table td { padding: 4px 10px; text-align: center; border: none; white-space: nowrap; }
    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s ease; }
    .data-pill:hover { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# ================= YARDIMCI FONKSİYONLAR =================
def clean_barcode(val):
    if pd.isna(val) or val == "": return ""
    return str(val).split('.')[0].strip()

def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", ""]: return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").replace(".", "").replace(",", ".").strip()
    clean = re.sub(r"[^\d.]", "", val_str)
    try: return float(clean)
    except: return None

# ================= AKILLI LİNK MOTORU (GÜNCELLENDİ) =================
def build_smart_link(source_col, raw_val, row):
    # .0 hatasını burada da temizliyoruz
    val = str(raw_val).split('.')[0].strip() if not pd.isna(raw_val) and str(raw_val).strip() != "" else ""
    barcode = clean_barcode(row.get("Barkod_Internal", ""))

    if val.startswith("http"):
        return val

    if val != "":
        # Trendyol Linki Düzeltildi
        if source_col == "TY": return f"https://www.trendyol.com/p-{val}"
        # Braun Shop Linki Düzeltildi (.0 içermez)
        if source_col == "BS Data ID": return f"https://www.braunshop.com.tr/index.php?route=product/product&product_id={val}"
        # Aksiyon (Akakçe) Linki Düzeltildi
        if source_col == "CSS Code": return f"https://www.akakce.com/arama/?q={val}"
        
        # Diğerleri (Dosyandaki çalışan mantık)
        if source_col == "HB": return f"https://www.hepsiburada.com/product-p-{val}"
        if source_col == "AMZ": return f"https://www.amazon.com.tr/dp/{val}"
        if source_col == "MM": return f"https://www.mediamarkt.com.tr/tr/product/_{val}.html"
    
    # Hiçbir veri yoksa barkod fallback
    if barcode:
        if source_col == "MM": return f"https://www.mediamarkt.com.tr/tr/search.html?query={barcode}"
        if source_col == "TKNS": return f"https://www.teknosa.com/arama/?s={barcode}"
        if source_col == "VTN": return f"https://www.vatanbilgisayar.com/arama/{barcode}/"
    
    return None

@st.cache_data(ttl=60)
def load_and_merge_data():
    fiyat_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Guncel&range=A:M"
    try:
        # Fiyatları Çek
        df_fiyat = pd.read_csv(fiyat_url, dtype=str) # Tüm kolonları string olarak oku
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        
        bc_col = next((c for c in df_fiyat.columns if "barkod" in c.lower()), None)
        if bc_col: df_fiyat["Barkod_Internal"] = df_fiyat[bc_col].apply(clean_barcode)

        if os.path.exists(MAPPING_FILE):
            # Mapping'i string olarak okumak .0 problemini %100 çözer
            df_map = pd.read_excel(MAPPING_FILE, engine='openpyxl', dtype=str)
            df_map.columns = [c.strip() for c in df_map.columns]
            
            map_bc_col = next((c for c in df_map.columns if "barkod" in c.lower()), None)
            if map_bc_col:
                df_map["Barkod_Internal"] = df_map[map_bc_col].apply(clean_barcode)
                link_cols = ["Barkod_Internal", "TY", "HB", "AMZ", "MM", "TKNS", "VTN", "BS Data ID", "CSS Code"]
                df_map_subset = df_map[[c for c in link_cols if c in df_map.columns]].copy()
                
                df_final = pd.merge(df_fiyat, df_map_subset, on="Barkod_Internal", how="left")
                return df_final.fillna("")
        
        return df_fiyat.fillna("")
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return None

# ================= RENDER MOTORU =================
def display_styled_table(df):
    def find_actual_col(df, name):
        for c in df.columns:
            if name.lower() in c.lower(): return c
        return None

    # Sütunları yakala (Hassas eşleşme)
    col_map = {
        "Marka": find_actual_col(df, "Marka"),
        "Ürün Adı": find_actual_col(df, "Ürün Adı"),
        "Barkod": find_actual_col(df, "Barkod"),
        "Ürün Kodu": find_actual_col(df, "Ürün Kodu"),
        "Alt Grup": find_actual_col(df, "Alt Grup"),
        "Aksiyon": find_actual_col(df, "Aksiyon"),
        "Braun Shop": find_actual_col(df, "Braun Shop"),
        "Media Markt": find_actual_col(df, "Media Markt"),
        "Teknosa": find_actual_col(df, "Teknosa"),
        "Vatan": find_actual_col(df, "Vatan"),
        "Trendyol": find_actual_col(df, "Trendyol"),
        "Hepsiburada": find_actual_col(df, "Hepsiburada"),
        "Amazon": find_actual_col(df, "Amazon")
    }

    link_ref = {
        "Aksiyon": "CSS Code", "Braun Shop": "BS Data ID", "Media Markt": "MM",
        "Teknosa": "TKNS", "Vatan": "VTN", "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ"
    }

    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for label, real in col_map.items():
        if real:
            logo = LOGOS.get(label)
            html += f'<th><img src="{logo}" class="header-logo"></th>' if logo else f'<th>{real}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for label, real in col_map.items():
            if not real: continue
            
            val = str(row[real])
            display_val = "" if val.lower() in ["nan", "none", ""] else val
            pill_style = ""
            
            # Fiyat Renklendirme
            bs_col_name = col_map["Braun Shop"]
            if label in ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"] and bs_col_name:
                ref = parse_price(row[bs_col_name])
                curr = parse_price(display_val)
                if ref and curr:
                    if curr == ref: pill_style = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                    else: pill_style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
            
            if not pill_style and display_val != "":
                if any(x in label.lower() for x in ["barkod", "kodu", "grup", "marka"]): pill_style = 'background-color: transparent;'
                else: pill_style = 'background-color: var(--pill-default-bg);'

            # LINK OLUSTUR
            map_key = link_ref.get(label)
            raw_id = row.get(map_key, "")
            final_url = build_smart_link(map_key, raw_id, row)

            if final_url and display_val:
                html += f'<td><a href="{final_url}" target="_blank" class="data-link"><span class="data-pill" style="{pill_style}">{display_val}</span></a></td>'
            else:
                html += f'<td><span class="data-pill" style="{pill_style}">{display_val}</span></td>'
        html += '</tr>'
    
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

# ================= MAIN =================
df_data = load_and_merge_data()
st.title("📊 Fiyat Analiz Merkezi")
if df_data is not None:
    search = st.text_input("🔍 Hızlı arama...")
    if search:
        df_data = df_data[df_data.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    display_styled_table(df_data)
