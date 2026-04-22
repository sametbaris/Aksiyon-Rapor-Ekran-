import streamlit as st
import pandas as pd
import re
import requests
import base64
import os
import io
import openpyxl
from datetime import datetime
import streamlit.components.v1 as components

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Aksiyon Raporu", page_icon="⚖️", layout="wide")

SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0"
MAPPING_FILE = "Aksiyon_Mapping.xlsx"

# ================= AKILLI LOGO YÜKLEME =================
def get_base64_logo(file_name):
    file_path = os.path.join("logos", file_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except: 
            return None
    return None

def load_logo_pair(file_name):
    """Siyah logoyu ve varsa _white uzantılı beyaz logoyu hafızaya alır."""
    base_name = file_name.split('.')[0]
    ext = file_name.split('.')[1]
    
    light_logo = get_base64_logo(file_name)
    dark_logo = get_base64_logo(f"{base_name}_white.{ext}")
    
    has_custom_dark = dark_logo is not None
    return {
        "light": light_logo, 
        "dark": dark_logo if has_custom_dark else light_logo,
        "invert_dark": not has_custom_dark # Beyaz resmi yoksa CSS ile biz beyazlatacağız
    }

LOGOS = {
    "Aksiyon": load_logo_pair("akakce.png"),
    "Media Markt": load_logo_pair("mediamarkt.png"),
    "Teknosa": load_logo_pair("teknosa.png"),
    "Vatan": load_logo_pair("vatan.png"),
    "Trendyol": load_logo_pair("trendyol.png"),
    "Hepsiburada": load_logo_pair("hepsiburada.png"),
    "Amazon": load_logo_pair("amazon.png"),
    "Braun Shop": load_logo_pair("braunshop.png")
}

# ================= SİHİRLİ TEMA DEDEKTÖRÜ =================
# Bu mini script, Streamlit kilitlenmeden sadece arka plan rengini okur
# Arka plan rengine göre logoları anında Light/Dark yapar.
components.html(
    """
    <script>
    try {
        const parentDoc = window.parent.document;
        let styleTag = parentDoc.getElementById("dynamic-theme-style");
        if (!styleTag) {
            styleTag = parentDoc.createElement("style");
            styleTag.id = "dynamic-theme-style";
            parentDoc.head.appendChild(styleTag);
        }
        
        setInterval(() => {
            const bgColor = window.getComputedStyle(parentDoc.body).backgroundColor;
            let rgb = bgColor.match(/\\d+/g);
            if (rgb && rgb.length >= 3) {
                // Arka plan renginin parlaklığını ölçer
                let brightness = (parseInt(rgb[0]) * 299 + parseInt(rgb[1]) * 587 + parseInt(rgb[2]) * 114) / 1000;
                if (brightness < 128) {
                    // Dark Mode (Siyah Arkaplan) Aktif
                    styleTag.innerHTML = `
                        .logo-light { display: none !important; }
                        .logo-dark { display: inline-block !important; }
                        .logo-dark.invert-logo { filter: brightness(0) invert(1) !important; }
                    `;
                } else {
                    // Light Mode (Beyaz Arkaplan) Aktif
                    styleTag.innerHTML = `
                        .logo-dark { display: none !important; }
                        .logo-light { display: inline-block !important; }
                    `;
                }
            }
        }, 500); // Sistemi kasmaması için saniyede 2 kez sessizce kontrol eder
    } catch (e) {}
    </script>
    """,
    height=0, width=0
)

# ================= CSS =================
st.markdown("""
<style>
    :root { --header-color: #888; --pill-default-bg: rgba(128, 128, 128, 0.1); }
    .table-container { width: 100%; margin-top: 10px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 8px; font-family: 'Inter', sans-serif; border: none; }
    .header-logo { height: 28px; width: auto; max-width: 120px; object-fit: contain; }
    .custom-table th { color: var(--header-color); font-weight: 500; text-transform: uppercase; font-size: 11px; padding: 10px 20px; text-align: center; }
    .custom-table td { padding: 4px 10px; text-align: center; border: none; white-space: nowrap; }
    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s ease; }
    .data-pill:hover { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
    .update-badge { text-align: right; color: var(--header-color); font-size: 12px; background: var(--pill-default-bg); padding: 6px 16px; border-radius: 30px; display: inline-block; float: right; margin-top: 15px; }
    div[data-testid="stDownloadButton"] button { width: 100%; border-radius: 20px; font-weight: 600; border: 1px solid #ddd; }
    
    /* Varsayılan olarak Dark logolar gizlidir, JavaScript duruma göre açar */
    .logo-dark { display: none; }
</style>
""", unsafe_allow_html=True)

# ================= YARDIMCI FONKSİYONLAR =================
def clean_val(val):
    if pd.isna(val) or str(val).strip().lower() in ["nan", "none", ""]: 
        return ""
    v = str(val).strip()
    if v.startswith("http"): 
        return v
    return v.split('.')[0]

def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", ""]: 
        return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").replace(".", "").replace(",", ".").strip()
    clean = re.sub(r"[^\d.]", "", val_str)
    try: 
        return float(clean)
    except: 
        return None

def get_column_mapping(df):
    def find_col(name_part, exclude=None):
        for c in df.columns:
            if name_part.lower() in c.lower():
                if exclude and exclude.lower() in c.lower():
                    continue
                return c
        return None

    return {
        "Marka": find_col("Marka"), "Ürün Adı": find_col("Ürün Adı"),
        "Barkod": find_col("Barkod"), "Ürün Kodu": find_col("Kodu", exclude="Barkod"),
        "Alt Grup": find_col("Grup"), "Aksiyon": find_col("Aksiyon"),
        "Braun Shop": find_col("Braun Shop"), "Media Markt": find_col("Media Markt"),
        "Teknosa": find_col("Teknosa"), "Vatan": find_col("Vatan"),
        "Trendyol": find_col("Trendyol"), "Hepsiburada": find_col("Hepsiburada") or find_col("Hepsi"),
        "Amazon": find_col("Amazon")
    }

# ================= AKILLI LİNK MOTORU =================
def build_smart_link(label, raw_id, row):
    val = clean_val(raw_id)
    barcode = clean_val(row.get("Barkod_Int", ""))

    if label == "Aksiyon":
        hidden_link = row.get("Hidden_Link")
        if pd.notna(hidden_link) and str(hidden_link).startswith("http"):
            return str(hidden_link)
        if val:
            return f"https://www.akakce.com/arama/?q={val}"
        if barcode:
            return f"https://www.akakce.com/arama/?q={barcode}"
        return None

    if val.startswith("http"): 
        return val

    if label == "Braun Shop":
        gs_link = row.get("GS_BS_Link")
        if pd.notna(gs_link) and str(gs_link).startswith("http"):
            return str(gs_link)
        if val:
            return f"https://www.braunshop.com.tr/index.php?route=product/product&product_id={val}"
        if barcode:
            return f"https://www.braunshop.com.tr/arama?q={barcode}"
        return None

    if val != "":
        if label == "Trendyol": 
            return f"https://www.trendyol.com/brand/product-p-{val}"
        if label == "Hepsiburada": 
            return f"https://www.hepsiburada.com/product-p-{val}"
        if label == "Amazon": 
            return f"https://www.amazon.com.tr/dp/{val}"
        if label == "Media Markt": 
            return f"https://www.mediamarkt.com.tr/tr/product/_{val}.html"
    
    if barcode:
        if label == "Media Markt": 
            return f"https://www.mediamarkt.com.tr/tr/search.html?query={barcode}"
        if label == "Teknosa": 
            return f"https://www.teknosa.com/arama/?s={barcode}"
        if label == "Vatan": 
            return f"https://www.vatanbilgisayar.com/arama/{barcode}/"
    
    return None

@st.cache_data(ttl=60)
def load_and_merge_data():
    fiyat_url_csv = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Guncel&range=A:M"
    fiyat_url_xlsx = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx&sheet=Guncel"
    
    try:
        df_fiyat = pd.read_csv(fiyat_url_csv, dtype=str)
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        
        bc_col = next((c for c in df_fiyat.columns if "barkod" in c.lower()), None)
        if bc_col: 
            df_fiyat["Barkod_Int"] = df_fiyat[bc_col].apply(clean_val)

        gsheet_bs_links = {}
        try:
            r = requests.get(fiyat_url_xlsx)
            wb_gs = openpyxl.load_workbook(io.BytesIO(r.content), data_only=False)
            ws_gs = wb_gs.active
            headers_gs = [str(c.value).strip() if c.value else "" for c in ws_gs[1]]
            
            idx_bc_gs = next((i for i, h in enumerate(headers_gs) if "barkod" in h.lower()), None)
            idx_bs_gs = next((i for i, h in enumerate(headers_gs) if "braun shop" in h.lower()), None)
            
            if idx_bc_gs is not None and idx_bs_gs is not None:
                for r_idx in range(2, ws_gs.max_row + 1):
                    bc_val = clean_val(ws_gs.cell(row=r_idx, column=idx_bc_gs+1).value)
                    bs_cell = ws_gs.cell(row=r_idx, column=idx_bs_gs+1)
                    
                    url = None
                    if bs_cell.hyperlink:
                        url = bs_cell.hyperlink.target
                    elif isinstance(bs_cell.value, str) and '=HYPERLINK' in bs_cell.value.upper():
                        match = re.search(r'=HYPERLINK\("([^"]+)"', bs_cell.value, re.IGNORECASE)
                        if match: 
                            url = match.group(1)
                        
                    if bc_val and url:
                        gsheet_bs_links[bc_val] = url
        except: 
            pass
        
        df_fiyat["GS_BS_Link"] = df_fiyat["Barkod_Int"].map(gsheet_bs_links)

        if os.path.exists(MAPPING_FILE):
            df_map = pd.read_excel(MAPPING_FILE, engine='openpyxl', dtype=str)
            df_map.columns = [c.strip() for c in df_map.columns]
            
            map_bc_col = next((c for c in df_map.columns if "barkod" in c.lower()), "Ürün Barkodu")
            df_map["Barkod_Int"] = df_map[map_bc_col].apply(clean_val)
            
            wb_map = openpyxl.load_workbook(MAPPING_FILE, data_only=True)
            ws_map = wb_map.active
            headers_map = [str(c.value).strip() if c.value else "" for c in ws_map[1]]
            
            idx_bc_map = next((i for i, h in enumerate(headers_map) if "barkod" in h.lower()), None)
            idx_br_map = next((i for i, h in enumerate(headers_map) if "braun" in h.lower() and "kodu" in h.lower()), None)
            
            ext_links = {}
            if idx_bc_map is not None and idx_br_map is not None:
                for r_idx in range(2, ws_map.max_row + 1):
                    bc_val = clean_val(ws_map.cell(row=r_idx, column=idx_bc_map+1).value)
                    b_cell = ws_map.cell(row=r_idx, column=idx_br_map+1)
                    if bc_val and b_cell.hyperlink:
                        ext_links[bc_val] = b_cell.hyperlink.target
            
            df_map["Hidden_Link"] = df_map["Barkod_Int"].map(ext_links)
            
            link_cols = ["Barkod_Int", "TY", "HB", "AMZ", "MM", "TKNS", "VTN", "BS Data ID", "CSS Code", "Hidden_Link"]
            df_map_sub = df_map[[c for c in link_cols if c in df_map.columns]].copy()
            
            df_final = pd.merge(df_fiyat, df_map_sub, on="Barkod_Int", how="left")
            return df_final.fillna("")
        
        return df_fiyat.fillna("")
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return None

# ================= RENDER =================
def display_styled_table(df, mapping):
    refs = {
        "Aksiyon": "CSS Code", "Braun Shop": "BS Data ID", "Media Markt": "MM",
        "Teknosa": "TKNS", "Vatan": "VTN", "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ"
    }

    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for label, real in mapping.items():
        if real:
            logo_pair = LOGOS.get(label)
            if logo_pair and logo_pair["light"]:
                l_src = logo_pair["light"]
                d_src = logo_pair["dark"]
                
                inv_class = "invert-logo" if logo_pair["invert_dark"] and label in ["Amazon", "Aksiyon"] else ""
                
                # İki logoyu da yüklüyoruz, ekrandaki CSS hangisinin gösterileceğine karar veriyor!
                html += f'<th><img src="{l_src}" class="header-logo logo-light" title="{label}"><img src="{d_src}" class="header-logo logo-dark {inv_class}" title="{label}"></th>'
            else:
                html += f'<th>{label}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for label, real in mapping.items():
            if not real: 
                continue
            val = str(row[real])
            d_val = "" if val.lower() in ["nan", "none", ""] else val
            style = ""
            
            bs_col_name = mapping.get("Braun Shop")
            if label in ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"] and bs_col_name:
                p_ref = parse_price(row[bs_col_name])
                p_curr = parse_price(d_val)
                if p_ref and p_curr:
                    if p_curr == p_ref: 
                        style = 'background-color: #d4edda; color: #155724; font-weight: 600;' 
                    elif p_curr > p_ref:
                        style = 'background-color: #fff3cd; color: #856404; font-weight: 600;' 
                    else: 
                        style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;' 
            
            if not style and d_val:
                if any(x in label.lower() for x in ["barkod", "kodu", "grup", "marka"]): 
                    style = 'background-color: transparent;'
                else: 
                    style = 'background-color: var(--pill-default-bg);'

            map_key = refs.get(label)
            target_id = row.get(map_key, "")
            
            url = build_smart_link(label, target_id, row)

            if url and d_val:
                html += f'<td><a href="{url}" target="_blank" class="data-link"><span class="data-pill" style="{style}">{d_val}</span></a></td>'
            else:
                html += f'<td><span class="data-pill" style="{style}">{d_val}</span></td>'
        html += '</tr>'
    
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

# ================= MAIN =================
col_title, col_update = st.columns([3, 1])
with col_title:
    st.title("📊 Aksiyon Raporu")

update_text = ""
try: 
    res = requests.get(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&range=N1")
    update_text = res.text.replace('"', '').strip()
except: 
    pass

with col_update:
    if update_text:
        st.markdown(f'<div class="update-badge">🔄 {update_text}</div>', unsafe_allow_html=True)

df_data = load_and_merge_data()

if df_data is not None:
    mapping = get_column_mapping(df_data)
    
    alt_grup_col = mapping.get("Alt Grup")
    if alt_grup_col and alt_grup_col in df_data.columns:
        gruplar = []
        for x in df_data[alt_grup_col].dropna():
            val = str(x).strip()
            if val != "" and val not in gruplar:
                gruplar.append(val)
        unique_gruplar = ["Tümü"] + gruplar
    else:
        unique_gruplar = ["Tümü"]

    # --- 5 Sütunlu Temiz Kontrol Paneli ---
    col_search, col_grup, col_plat, col_stat, col_btn = st.columns([2.5, 2, 2, 2.5, 1.5])
    
    with col_search:
        search = st.text_input("🔍 Ürün Adı veya Barkod...")
    with col_grup:
        filter_grup = st.selectbox("📂 Alt Grup", unique_gruplar)
    with col_plat:
        filter_platform = st.selectbox("🛒 Platform", ["Tümü", "Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"])
    with col_stat:
        filter_status = st.selectbox("🎨 Fiyat Rengi", ["Tümü", "🔴 Kırmızı (↓)", "🟢 Yeşil (=)", "🟡 Sarı (↑)"])

    if search:
        df_data = df_data[df_data.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    if filter_grup != "Tümü" and alt_grup_col:
        df_data = df_data[df_data[alt_grup_col].astype(str).str.strip() == filter_grup]

    if filter_status != "Tümü":
        bs_col = mapping.get("Braun Shop")
        if bs_col:
            p_list = [filter_platform] if filter_platform != "Tümü" else ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
            actual_cols = [mapping.get(p) for p in p_list]
            actual_cols = [c for c in actual_cols if c] 
            
            def check_color(row):
                bs_val = parse_price(row[bs_col])
                if bs_val is None: 
                    return False
                for col in actual_cols:
                    p_val = parse_price(row[col])
                    if p_val is not None:
                        if "🔴" in filter_status and p_val < bs_val: return True
                        if "🟢" in filter_status and p_val == bs_val: return True
                        if "🟡" in filter_status and p_val > bs_val: return True
                return False
                
            df_data = df_data[df_data.apply(check_color, axis=1)]

    export_cols = [real for label, real in mapping.items() if real in df_data.columns]
    df_export = df_data[export_cols].copy()
    
    current_time_str = datetime.now().strftime("%d-%m-%Y_%H-%M")
    excel_filename = f"Aksiyon_Analiz_Raporu_{current_time_str}.xlsx"

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False)
    
    with col_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Excel İndir", 
            data=output.getvalue(), 
            file_name=excel_filename, 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            use_container_width=True
        )

    display_styled_table(df_data, mapping)
