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
    .custom-table td { padding: 4px 10px; text-align: center; border: none; white-space: nowrap; }
    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s ease; }
    .data-pill:hover { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
    .stTextInput input { border-radius: 50px !important; }
</style>
""", unsafe_allow_html=True)

# ================= VERİ TEMİZLEME VE OKUMA =================
def clean_id(val):
    """Hücredeki değeri temizler, .0 ekini siler."""
    if pd.isna(val) or str(val).strip() == "": return ""
    # .0 kısmını temizle (Pandas float dönüşümü hatası)
    s = str(val).split('.')[0].strip()
    return s

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
        # Fiyatları string (metin) olarak oku
        df_fiyat = pd.read_csv(fiyat_url, dtype=str)
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        
        # Barkod sütununu bul (Duyarsız)
        bc_col = next((c for c in df_fiyat.columns if "barkod" in c.lower()), None)
        if bc_col: df_fiyat["Barkod_Int"] = df_fiyat[bc_col].apply(clean_id)

        if os.path.exists(MAPPING_FILE):
            # Mapping'i string olarak oku (Böylece ID'ler asla .0 olmaz)
            df_map = pd.read_excel(MAPPING_FILE, engine='openpyxl', dtype=str)
            df_map.columns = [c.strip() for c in df_map.columns]
            
            map_bc_col = next((c for c in df_map.columns if "barkod" in c.lower()), "Ürün Barkodu")
            df_map["Barkod_Int"] = df_map[map_bc_col].apply(clean_id)
            
            # Eşleşme yapılacak kolonlar (Senin Mapping dosyandaki isimler)
            link_cols = ["Barkod_Int", "TY", "HB", "AMZ", "MM", "TKNS", "VTN", "BS Data ID", "CSS Code"]
            df_map_sub = df_map[[c for c in link_cols if c in df_map.columns]].copy()
            
            df_final = pd.merge(df_fiyat, df_map_sub, on="Barkod_Int", how="left")
            return df_final.fillna("")
        
        return df_fiyat.fillna("")
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return None

# ================= AKILLI LİNK MOTORU =================
def build_link(site, raw_id, row):
    val = clean_id(raw_id)
    if val.startswith("http"): return val
    
    barcode = clean_id(row.get("Barkod_Int", ""))
    
    if val == "":
        # Link/ID yoksa Barkod araması (MM, TKNS, VTN için)
        if site == "MM": return f"https://www.mediamarkt.com.tr/tr/search.html?query={barcode}"
        if site == "TKNS": return f"https://www.teknosa.com/arama/?s={barcode}"
        if site == "VTN": return f"https://www.vatanbilgisayar.com/arama/{barcode}/"
        return None

    # Lokal kodundaki patterns
    if site == "TY": return f"https://www.trendyol.com/p-{val}"
    if site == "HB": return f"https://www.hepsiburada.com/p-{val}"
    if site == "AMZ": return f"https://www.amazon.com.tr/dp/{val}"
    if site == "MM": return f"https://www.mediamarkt.com.tr/tr/product/_{val}.html"
    if site == "Braun Shop": return f"https://www.braunshop.com.tr/index.php?route=product/product&product_id={val}"
    if site == "Aksiyon": return f"https://www.akakce.com/p/{val}.html"
    
    return None

# ================= RENDER =================
def display_styled_table(df):
    def find_actual(name):
        for c in df.columns:
            if name.lower() in c.lower(): return c
        return None

    # Kolon eşleme (Kaybolmamaları için hassas arama)
    mapping = {
        "Marka": find_actual("Marka"), "Ürün Adı": find_actual("Ürün Adı"),
        "Barkod": find_actual("Barkod"), "Ürün Kodu": find_actual("Kodu"),
        "Alt Grup": find_actual("Grup"), "Aksiyon": find_actual("Aksiyon"),
        "Braun Shop": find_actual("Braun Shop"), "Media Markt": find_actual("Media Markt"),
        "Teknosa": find_actual("Teknosa"), "Vatan": find_actual("Vatan"),
        "Trendyol": find_actual("Trendyol"), "Hepsiburada": find_actual("Hepsiburada"),
        "Amazon": find_actual("Amazon")
    }

    # Hangi başlık hangi Mapping sütununa bakacak?
    refs = {
        "Aksiyon": "CSS Code", "Braun Shop": "BS Data ID", "Media Markt": "MM",
        "Teknosa": "TKNS", "Vatan": "VTN", "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ"
    }

    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for label, real in mapping.items():
        if real:
            logo = LOGOS.get(label)
            html += f'<th><img src="{logo}" class="header-logo"></th>' if logo else f'<th>{real}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for label, real in mapping.items():
            if not real: continue
            val = str(row[real])
            d_val = "" if val.lower() in ["nan", "none", ""] else val
            style = ""
            
            # Kıyaslama
            bs_col = mapping["Braun Shop"]
            if label in ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"] and bs_col:
                p_ref = parse_price(row[bs_col])
                p_curr = parse_price(d_val)
                if p_ref and p_curr:
                    if p_curr == p_ref: style = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                    else: style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
            
            if not style and d_val:
                if any(x in label.lower() for x in ["barkod", "kodu", "grup", "marka"]): style = 'background-color: transparent;'
                else: style = 'background-color: var(--pill-default-bg);'

            # LINK OLUŞTURMA
            m_col = refs.get(label)
            url = build_link(label, row.get(m_col, ""), row)

            if url and d_val:
                html += f'<td><a href="{url}" target="_blank" class="data-link"><span class="data-pill" style="{style}">{d_val}</span></a></td>'
            else:
                html += f'<td><span class="data-pill" style="{style}">{d_val}</span></td>'
        html += '</tr>'
    
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

# ================= MAIN =================
df = load_and_merge_data()
st.title("📊 Fiyat Analiz Merkezi")
if df is not None:
    search = st.text_input("🔍 Hızlı arama...")
    if search: df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    display_styled_table(df)
