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

# ================= CSS =================
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
</style>
""", unsafe_allow_html=True)

# ================= YARDIMCI FONKSİYONLAR =================
def clean_id(val):
    """Hücredeki değeri temizler, .0 ekini siler, nan değerleri boş döner."""
    if pd.isna(val): return ""
    v = str(val).strip().lower()
    if v in ["nan", "none", ""]: return ""
    # Sayısal bir değerse (örn: 1282.0) noktadan sonrasını at
    return v.split('.')[0]

def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", ""]: return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").replace(".", "").replace(",", ".").strip()
    clean = re.sub(r"[^\d.]", "", val_str)
    try: return float(clean)
    except: return None

# ================= AKILLI LİNK MOTORU (HASSAS AYAR) =================
def build_smart_link(label, raw_id, row):
    # Mapping dosyasındaki ID/Link bilgisini temizle
    val = clean_id(raw_id)
    # Eğer hücre zaten tam bir link (http) içeriyorsa direkt onu kullan
    if val.startswith("http"):
        return val
    
    barcode = clean_id(row.get("Barkod_Int", ""))

    # ID boşsa bazı mağazalar için barkod araması üret (Lokal kodundaki mantık)
    if val == "":
        if label == "Media Markt": return f"https://www.mediamarkt.com.tr/tr/search.html?query={barcode}" if barcode else None
        if label == "Teknosa": return f"https://www.teknosa.com/arama/?s={barcode}" if barcode else None
        if label == "Vatan": return f"https://www.vatanbilgisayar.com/arama/{barcode}/" if barcode else None
        return None

    # ID varsa, ilgili platformun link yapısını oluştur
    if label == "Trendyol": return f"https://www.trendyol.com/brand/product-p-{val}"
    if label == "Hepsiburada": return f"https://www.hepsiburada.com/product-p-{val}"
    if label == "Amazon": return f"https://www.amazon.com.tr/dp/{val}"
    if label == "Media Markt": return f"https://www.mediamarkt.com.tr/tr/product/_{val}.html"
    if label == "Braun Shop": return f"https://www.braunshop.com.tr/index.php?route=product/product&product_id={val}"
    if label == "Aksiyon": return f"https://www.akakce.com/arama/?q={val}"
    
    return None

@st.cache_data(ttl=60)
def load_and_merge_data():
    fiyat_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Guncel&range=A:M"
    try:
        # Fiyatları string olarak oku
        df_fiyat = pd.read_csv(fiyat_url, dtype=str)
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        
        # Fiyat barkod sütunu
        bc_col = next((c for c in df_fiyat.columns if "barkod" in c.lower()), None)
        if bc_col: df_fiyat["Barkod_Int"] = df_fiyat[bc_col].apply(clean_id)

        if os.path.exists(MAPPING_FILE):
            # Mapping dosyasını string olarak oku (.0 oluşumunu engeller)
            df_map = pd.read_excel(MAPPING_FILE, engine='openpyxl', dtype=str)
            df_map.columns = [c.strip() for c in df_map.columns]
            
            # Mapping barkod sütunu
            map_bc_col = next((c for c in df_map.columns if "barkod" in c.lower()), "Ürün Barkodu")
            df_map["Barkod_Int"] = df_map[map_bc_col].apply(clean_id)
            
            # Lokal kodundaki sütun isimleri
            link_cols = ["Barkod_Int", "TY", "HB", "AMZ", "MM", "TKNS", "VTN", "BS Data ID", "CSS Code"]
            df_map_sub = df_map[[c for c in link_cols if c in df_map.columns]].copy()
            
            df_final = pd.merge(df_fiyat, df_map_sub, on="Barkod_Int", how="left")
            return df_final.fillna("")
        
        return df_fiyat.fillna("")
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return None

# ================= RENDER =================
def display_styled_table(df):
    # Kolonları ismen bul (Kayıp sütunları engellemek için)
    def find_col(name_part):
        for c in df.columns:
            if name_part.lower() in c.lower(): return c
        return None

    mapping = {
        "Marka": find_col("Marka"), "Ürün Adı": find_col("Ürün Adı"),
        "Barkod": find_col("Barkod"), "Ürün Kodu": find_col("Kodu"),
        "Alt Grup": find_col("Grup"), "Aksiyon": find_col("Aksiyon"),
        "Braun Shop": find_col("Braun Shop"), "Media Markt": find_col("Media Markt"),
        "Teknosa": find_col("Teknosa"), "Vatan": find_col("Vatan"),
        "Trendyol": find_col("Trendyol"), "Hepsiburada": find_actual("Hepsiburada"), # find_actual fix
        "Amazon": find_col("Amazon")
    }
    # Hepsiburada için küçük bir düzeltme
    if not mapping["Hepsiburada"]: mapping["Hepsiburada"] = find_col("Hepsi")

    # Mapping referansları
    refs = {
        "Aksiyon": "CSS Code", "Braun Shop": "BS Data ID", "Media Markt": "MM",
        "Teknosa": "TKNS", "Vatan": "VTN", "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ"
    }

    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for label, real in mapping.items():
        if real:
            logo = LOGOS.get(label)
            html += f'<th><img src="{logo}" class="header-logo"></th>' if logo else f'<th>{label}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for label, real in mapping.items():
            if not real: continue
            val = str(row[real])
            d_val = "" if val.lower() in ["nan", "none", ""] else val
            style = ""
            
            # Fiyat Kıyaslama
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

            # --- LİNK OLUŞTURMA ---
            m_col = refs.get(label)
            url = build_smart_link(label, row.get(m_col, ""), row)

            if url and d_val:
                html += f'<td><a href="{url}" target="_blank" class="data-link"><span class="data-pill" style="{style}">{d_val}</span></a></td>'
            else:
                html += f'<td><span class="data-pill" style="{style}">{d_val}</span></td>'
        html += '</tr>'
    
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

# ================= MAIN =================
st.title("📊 Fiyat Analiz Merkezi")
df_data = load_and_merge_data()
if df_data is not None:
    search = st.text_input("🔍 Hızlı arama...")
    if search:
        df_data = df_data[df_data.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    display_styled_table(df_data)
