import streamlit as st
import pandas as pd
import re
import requests
import base64
import os
import io

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Fiyat Analiz Merkezi", page_icon="⚖️", layout="wide")

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

# ================= MODERN CSS =================
st.markdown("""
<style>
    :root { --text-main: inherit; --header-color: #888; --pill-default-bg: rgba(128, 128, 128, 0.1); }
    .table-container { width: 100%; margin-top: 20px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 8px; font-family: 'Inter', sans-serif; border: none; }
    .header-logo { height: 28px; width: auto; max-width: 120px; object-fit: contain; }
    .custom-table th { color: var(--header-color); font-weight: 500; text-transform: uppercase; font-size: 11px; padding: 10px 20px; text-align: center; }
    .custom-table td { padding: 4px 10px; text-align: center; border: none; white-space: nowrap; color: var(--text-main); }
    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s ease; }
    .data-pill:hover { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
    .update-badge { text-align: right; color: var(--header-color); font-size: 12px; background: var(--pill-default-bg); padding: 6px 16px; border-radius: 30px; display: inline-block; float: right; }
    .stTextInput input { border-radius: 50px !important; }
</style>
""", unsafe_allow_html=True)

# ================= YARDIMCI FONKSİYONLAR =================
def clean_barcode(val):
    if pd.isna(val): return ""
    return str(val).split('.')[0].strip()

def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", ""]: return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").replace(".", "").replace(",", ".").strip()
    clean = re.sub(r"[^\d.]", "", val_str)
    try: return float(clean)
    except: return None

# ================= LOKAL KODDAN ALINAN AKILLI LİNK MOTORU =================
def build_smart_link(source_col, raw_val, row):
    if not raw_val or pd.isna(raw_val) or str(raw_val).strip() == "":
        # Link yoksa barkodla arama sayfasına yönlendir (MM, TKNS, VTN için fallback)
        barcode = clean_barcode(row.get("Barkod_Internal", ""))
        if not barcode: return None
        if source_col == "MM": return f"https://www.mediamarkt.com.tr/tr/search.html?query={barcode}"
        if source_col == "TKNS": return f"https://www.teknosa.com/arama/?s={barcode}"
        if source_col == "VTN": return f"https://www.vatanbilgisayar.com/arama/{barcode}/"
        return None
    
    val = str(raw_val).strip()
    if val.startswith("http"): return val
    
    # Lokal kodundaki scrape mantığına göre link inşası
    if source_col == "TY": return f"https://www.trendyol.com/brand/product-p-{val}"
    if source_col == "HB": return f"https://www.hepsiburada.com/product-p-{val}"
    if source_col == "AMZ": return f"https://www.amazon.com.tr/dp/{val}"
    if source_col == "MM": return f"https://www.mediamarkt.com.tr/tr/product/_{val}.html"
    if source_col == "BS Data ID": return f"https://www.braunshop.com.tr/index.php?route=product/product&product_id={val}"
    if source_col == "CSS Code": return f"https://www.akakce.com/arama/?q={val}"
    
    return val

@st.cache_data(ttl=60)
def load_and_merge_data():
    fiyat_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Guncel&range=A:M"
    try:
        df_fiyat = pd.read_csv(fiyat_url)
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        
        # Barkod sütununu bul ve sabitle
        bc_col = next((c for c in df_fiyat.columns if "Barkod" in c), None)
        if bc_col: df_fiyat["Barkod_Internal"] = df_fiyat[bc_col].apply(clean_barcode)

        if os.path.exists(MAPPING_FILE):
            df_map = pd.read_excel(MAPPING_FILE, engine='openpyxl')
            df_map.columns = [c.strip() for c in df_map.columns]
            
            # Mapping'deki barkod sütununu bul (Lokal kodunda 'Ürün Barkodu')
            map_bc_col = next((c for c in df_map.columns if "Barkod" in c), "Ürün Barkodu")
            df_map["Barkod_Internal"] = df_map[map_bc_col].apply(clean_barcode)
            
            # Mapping'den alınacak tüm link/ID kolonları
            link_cols = ["Barkod_Internal", "TY", "HB", "AMZ", "MM", "TKNS", "VTN", "BS Data ID", "CSS Code"]
            df_map = df_map[[c for c in link_cols if c in df_map.columns]]
            
            # Birleştir
            df_final = pd.merge(df_fiyat, df_map, on="Barkod_Internal", how="left")
            return df_final.fillna("")
        
        return df_fiyat.fillna("")
    except Exception as e:
        st.error(f"Veri hatası: {e}")
        return None

# ================= RENDER MOTORU =================
def display_styled_table(df):
    # Google Sheets'teki orijinal kolon isimlerini yakala
    def find_col(possible_names):
        for c in df.columns:
            if any(p.lower() == c.lower() or p.lower() in c.lower() for p in possible_names):
                return c
        return None

    # Ekranda gösterilecek sütunların gerçek isimlerini buluyoruz
    cols = {
        "Marka": find_col(["Marka"]),
        "Ürün Adı": find_col(["Ürün Adı"]),
        "Barkod": find_col(["Barkod"]),
        "Braun Ürün Kodu": find_col(["Ürün Kodu", "Braun Ürün Kodu"]),
        "Alt Grup": find_col(["Alt Grup", "ALT GRUP"]),
        "Aksiyon": find_col(["Aksiyon"]),
        "Braun Shop": find_col(["Braun Shop"]),
        "Media Markt": find_col(["Media Markt"]),
        "Teknosa": find_col(["Teknosa"]),
        "Vatan": find_col(["Vatan"]),
        "Trendyol": find_col(["Trendyol"]),
        "Hepsiburada": find_col(["Hepsiburada"]),
        "Amazon": find_col(["Amazon"])
    }

    # Linkleme eşleşmesi (App Sütunu -> Mapping Sütunu)
    link_mapping = {
        "Aksiyon": "CSS Code", "Braun Shop": "BS Data ID",
        "Media Markt": "MM", "Teknosa": "TKNS", "Vatan": "VTN", 
        "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ"
    }

    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for label, real_name in cols.items():
        if real_name:
            logo = LOGOS.get(label)
            html += f'<th><img src="{logo}" class="header-logo"></th>' if logo else f'<th>{real_name}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for label, real_name in cols.items():
            if not real_name: continue
            
            val = str(row[real_name])
            display_val = "" if val.lower() in ["nan", "none", ""] else val
            pill_style = ""
            
            # Fiyat Renklendirme (Braun Shop ile kıyaslama)
            br_shop_col = cols["Braun Shop"]
            if label in ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"] and br_shop_col:
                ref_val = parse_price(row[br_shop_col])
                curr_val = parse_price(display_val)
                if ref_val and curr_val:
                    if curr_val == ref_val: pill_style = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                    else: pill_style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
            
            # Şeffaf Stil (Barkod, Ürün Kodu vb.)
            if not pill_style and display_val != "":
                if any(x in label.lower() for x in ["barkod", "kodu", "grup", "marka"]): pill_style = 'background-color: transparent;'
                else: pill_style = 'background-color: var(--pill-default-bg);'

            # --- AKILLI LİNK OLUŞTURMA ---
            map_col = link_mapping.get(label)
            raw_id = row.get(map_col, "")
            final_url = build_smart_link(map_col, raw_id, row)

            if final_url and display_val:
                cell = f'<td><a href="{final_url}" target="_blank" class="data-link"><span class="data-pill" style="{pill_style}">{display_val}</span></a></td>'
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
    try: 
        res = requests.get(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&range=N1")
        st.markdown(f'<div class="update-badge">🔄 {res.text.replace('"', '').strip()}</div>', unsafe_allow_html=True)
    except: pass

if df is not None:
    search = st.text_input("🔍 Hızlı arama...")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    display_styled_table(df)
