import streamlit as st
import pandas as pd
import re
import requests
import base64
import os
import io
import openpyxl
import gspread
import uuid
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# ================= SAYFA AYARLARI =================
icon_path = os.path.join("logos", "sistem.png")
st.set_page_config(
    page_title="Aksiyon Raporu", 
    page_icon=icon_path if os.path.exists(icon_path) else "⚖️", 
    layout="wide"
)

SHEET_ID = "17zVRiwyUYaaEAqyzNx0u7aMMncdgH81vrKbzqS9MHB4"
MAPPING_FILE = "Aksiyon_Mapping.xlsx"

# --- PLATFORM ANA LİNKLERİ ---
PLATFORM_LINKS = {
    "Aksiyon": "https://www.akakce.com/hesabim/listelerim/detay/?l=5291190",
    "Braun Shop": "https://www.braunshop.com.tr",
    "Media Markt": "https://www.mediamarkt.com.tr/tr/category/kisisel-bakim-465820.html?brand=ORAL%20B%20OR%20BRAUN%20OR%20REVLON&marketplace=MediaMarkt&sort=availability+asc",
    "Teknosa": "https://www.teknosa.com/kisisel-bakim-c-118?s=%3Arelevance%3Aseller%3Ateknosa%3Abrand%3A2734%3Abrand%3A275%3Abrand%3A2426&text=",
    "Vatan": "https://www.vatanbilgisayar.com/oral-b-braun-revlon/kisisel-bakim-urunleri/?srt=PU",
    "Amazon": "https://www.amazon.com.tr/s?k=braun&i=beauty&rh=n%3A12466323031%2Cp_89%3ABraun%2Cp_6%3AA1UNQM1SR2CHM&s=price-desc-rank&dc&__mk_tr_TR=%C3%85M%C3%85%C5%BD%C3%95%C3%91&qid=1606138076&rnid=15358539031&ref=sr_st_price-desc-rank",
    "Hepsiburada": "https://www.hepsiburada.com/magaza/hepsiburada?markalar=braun-revlon&kategori=60001547&tab=allproducts",
    "Trendyol": "https://www.trendyol.com/sr?wb=633%2C888&os=1&mid=968"
}

# ================= AKILLI LOGO YÜKLEME =================
def get_base64_logo(file_name):
    file_path = os.path.join("logos", file_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except: return None
    return None

def load_logo_pair(file_name):
    base_name = file_name.split('.')[0]
    ext = file_name.split('.')[1]
    l_logo = get_base64_logo(file_name)
    d_logo = get_base64_logo(f"{base_name}_white.{ext}")
    return {"light": l_logo, "dark": d_logo if d_logo else l_logo, "invert_dark": not d_logo}

SYSTEM_LOGO = load_logo_pair("sistem.png")

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

# ================= TEMA DEDEKTÖRÜ (GÖLGE DEĞİŞKENLERİ) =================
components.html(
    """
    <script>
    try {
        const parentDoc = window.parent.document;
        setInterval(() => {
            const bgColor = window.getComputedStyle(parentDoc.body).backgroundColor;
            let rgb = bgColor.match(/\\d+/g);
            if (rgb && rgb.length >= 3) {
                let brightness = (parseInt(rgb[0]) * 299 + parseInt(rgb[1]) * 587 + parseInt(rgb[2]) * 114) / 1000;
                
                // Arka plan rengini ve gölge tonunu CSS değişkeni olarak ana sayfaya gönder
                parentDoc.documentElement.style.setProperty('--dynamic-bg-color', bgColor);
                parentDoc.documentElement.style.setProperty('--dynamic-shadow', brightness < 128 ? 'rgba(0, 0, 0, 0.8)' : 'rgba(0, 0, 0, 0.12)');
                
                let styleTag = parentDoc.getElementById("logo-theme-style");
                if (!styleTag) {
                    styleTag = parentDoc.createElement("style");
                    styleTag.id = "logo-theme-style";
                    parentDoc.head.appendChild(styleTag);
                }
                
                if (brightness < 128) {
                    styleTag.innerHTML = `.logo-light { display: none !important; } .logo-dark { display: inline-block !important; } .logo-dark.invert-logo { filter: brightness(0) invert(1) !important; }`;
                    parentDoc.documentElement.classList.add('dark-theme');
                    parentDoc.documentElement.classList.remove('light-theme');
                } else {
                    styleTag.innerHTML = `.logo-dark { display: none !important; } .logo-light { display: inline-block !important; }`;
                    parentDoc.documentElement.classList.add('light-theme');
                    parentDoc.documentElement.classList.remove('dark-theme');
                }
            }
        }, 500);
    } catch (e) {}
    </script>
    """, height=0, width=0
)

# ================= CSS =================
st.markdown("""
<style>
    /* 1. TÜM SAYFA İÇİN KESKİN YAZI ZORLAMASI */
    * {
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
    }

    :root { --header-color: #888; --pill-default-bg: rgba(128, 128, 128, 0.1); }
    
    /* RESPONSIVE LOGO TEMA GÖSTERİM KURALLARI (JS ÇAKIŞMASIZ) */
    .logo-light { display: inline-block !important; }
    .logo-dark { display: none !important; }
    
    .dark-theme .logo-light, html[data-theme="dark"] .logo-light { display: none !important; }
    .dark-theme .logo-dark, html[data-theme="dark"] .logo-dark { display: inline-block !important; }
    .dark-theme .logo-dark.invert-logo, html[data-theme="dark"] .logo-dark.invert-logo { filter: brightness(0) invert(1) !important; }

    /* MOBİL VE MASAÜSTÜ UYUMLU RESPONSIVE BAŞLIK KONTEYNERİ */
    .main-logo-container { 
        display: flex; 
        align-items: center; 
        gap: 15px; 
        margin-bottom: 20px; 
        flex-wrap: wrap;
    }
    
    .main-system-logo { 
        height: 60px; 
        width: auto; 
        object-fit: contain; 
        transition: height 0.3s;
    }
    
    .main-title-text {
        margin: 0; 
        display: inline-block;
        font-size: 2.2rem;
        font-weight: 700;
        transition: font-size 0.3s;
    }
    
    .online-badge-container {
        display: flex; 
        align-items: center; 
        gap: 6px; 
        background: rgba(0, 255, 0, 0.1); 
        padding: 4px 12px; 
        border-radius: 20px; 
        border: 1px solid rgba(0, 255, 0, 0.2); 
    }
    
    /* TELEFONLAR (MOBİL EKRANLAR) İÇİN ÖZEL CSS MEDYA SORGUSU */
    @media (max-width: 768px) {
        .main-logo-container {
            flex-direction: column; 
            align-items: center;
            justify-content: center;
            text-align: center;
            gap: 8px;
            width: 100%;
        }
        .main-system-logo {
            height: 45px; 
        }
        .main-title-text {
            font-size: 1.6rem; 
        }
        .online-badge-container {
            margin-left: 0 !important; 
            margin-top: 2px;
        }
    }
    
    /* MULTISELECT BULANIKLIK ÇÖZÜMÜ */
    div[data-baseweb="popover"] {
        transition: none !important;
        animation: none !important;
        will-change: auto !important;
    }
    
    div[data-baseweb="popover"] ul {
        transform: translateZ(0) !important;
        backface-visibility: hidden !important;
    }

    div[data-baseweb="popover"] [role="option"],
    div[data-baseweb="popover"] [role="option"] span {
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
        font-family: inherit !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        letter-spacing: normal !important;
    }
    
    /* TABLO TASARIMI VE TİTREME (JITTER) İPTALİ */
    .table-container { 
        width: 100%; 
        margin-top: 10px; 
        overflow: auto; 
        max-height: 75vh; 
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        border: none !important;
    }
    
    /* ========================================================= */
    /* ULTRA MİNİMAL, ŞIK VE İNCE KAYDIRMA ÇUBUĞU (SCROLLBAR)    */
    /* ========================================================= */
    /* Webkit tarayıcılar (Chrome, Safari, Edge, Opera) için */
    .table-container::-webkit-scrollbar {
        width: 5px !important;  /* Dikey bar genişliği (ultra ince) */
        height: 5px !important; /* Yatay bar yüksekliği (ultra ince) */
    }
    
    .table-container::-webkit-scrollbar-track {
        background: transparent !important; /* Arka planı tamamen görünmez/saydam yap */
    }
    
    .table-container::-webkit-scrollbar-thumb {
        background: rgba(128, 128, 128, 0.2) !important; /* Yarı saydam gri asil renk */
        border-radius: 10px !important; /* Yuvarlak kenarlar */
        transition: background 0.3s ease;
    }
    
    .table-container::-webkit-scrollbar-thumb:hover {
        background: rgba(128, 128, 128, 0.4) !important; /* Üzerine gelindiğinde hafifçe koyulaşır */
    }
    
    /* Firefox tarayıcılar için modern uyumluluk */
    .table-container {
        scrollbar-width: thin !important;
        scrollbar-color: rgba(128, 128, 128, 0.2) transparent !important;
    }
    /* ========================================================= */
    
    .custom-table { 
        width: 100%; 
        table-layout: auto; 
        border-collapse: separate !important; 
        border-spacing: 0 !important; 
        font-family: 'Inter', sans-serif; 
        border: none !important; 
    }
    
    .header-logo { height: 28px; width: auto; max-width: 120px; object-fit: contain; transition: transform 0.2s; }
    .header-logo:hover { transform: scale(1.15); }
    
    /* BAŞLIK SATIRI (SIFIR SIZINTI VE ÇİFT GÖLGE) */
    .custom-table thead th { 
        position: sticky; 
        top: 0px !important; 
        z-index: 20; 
        padding: 14px 20px; 
        text-align: center;
        color: var(--header-color); 
        font-weight: 500; 
        text-transform: uppercase; 
        font-size: 11px;
        background-color: var(--dynamic-bg-color, #ffffff) !important;
        box-shadow: 0 -2px 0 var(--dynamic-bg-color, #ffffff), 0 8px 15px -4px var(--dynamic-shadow, rgba(0,0,0,0.15)) !important;
        border-top: none !important;
        border-left: none !important; 
        border-right: none !important; 
        border-bottom: 1px solid rgba(128,128,128,0.1) !important;
    }
    
    .custom-table td { 
        padding: 8px 10px; 
        text-align: center; 
        white-space: nowrap; 
        border-top: none !important;
        border-left: none !important; 
        border-right: none !important; 
        border-bottom: 1px solid rgba(128,128,128,0.06) !important; 
    }
    
    .custom-table tbody tr:last-child td { border-bottom: none !important; }
    
    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 6px 14px; display: inline-block; border-radius: 20px; transition: all 0.3s ease; }
    
    a.data-link:hover .data-pill { transform: scale(1.1); box-shadow: 0px 6px 15px rgba(0,0,0,0.2); cursor: pointer; }
    
    .update-badge { text-align: right; color: var(--header-color); font-size: 12px; background: var(--pill-default-bg); padding: 6px 16px; border-radius: 30px; display: inline-block; float: right; margin-top: 15px; }
    div[data-testid="stDownloadButton"] button { width: 100%; border-radius: 20px; font-weight: 600; border: 1px solid #ddd; }
    .logo-dark { display: none; }
</style>
""", unsafe_allow_html=True)

# ================= GSPREAD KİMLİK DOĞRULAMA =================
@st.cache_resource
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        elif os.path.exists("service_account.json"):
            creds = Credentials.from_service_account_file("service_account.json", scopes=scope)
        else:
            return None
        return gspread.authorize(creds)
    except Exception:
        return None

# ================= ZİYARETÇİ TAKİP MOTORU =================
@st.cache_data(ttl=60)
def get_online_count():
    client = get_gspread_client()
    if not client: return 1
    try:
        sh = client.open_by_key(SHEET_ID)
        log_sheet = sh.worksheet("Ziyaretci_Log")
        all_logs = log_sheet.get_all_records()
        
        online_count = 0
        tr_now = datetime.utcnow() + timedelta(hours=3)
        two_minutes_ago = tr_now - timedelta(minutes=2)
        
        for record in all_logs:
            try:
                last_seen = datetime.strptime(str(record.get('Son_Gorulme', '')), "%Y-%m-%d %H:%M:%S")
                if last_seen > two_minutes_ago:
                    online_count += 1
            except: pass
        return max(1, online_count)
    except: return 1

def track_user_presence():
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())[:8]
        st.session_state.last_ping = None
        
    now = datetime.utcnow() + timedelta(hours=3)
    client = get_gspread_client()
    
    if client and (st.session_state.last_ping is None or (now - st.session_state.last_ping).total_seconds() > 60):
        try:
            sh = client.open_by_key(SHEET_ID)
            log_sheet = sh.worksheet("Ziyaretci_Log")
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            cell = log_sheet.find(st.session_state.user_id)
            if cell:
                log_sheet.update_cell(cell.row, 2, now_str)
            else:
                log_sheet.append_row([st.session_state.user_id, now_str])
            st.session_state.last_ping = now
        except: pass
        
    return get_online_count()

# ================= YARDIMCI FONKSİYONLAR =================
def clean_val(val):
    if pd.isna(val) or str(val).strip().lower() in ["nan", "none", ""]: return ""
    v = str(val).strip()
    if v.startswith("http"): return v
    return v.split('.')[0]

def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", ""]: return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").replace(".", "").replace(",", ".").strip()
    clean = re.sub(r"[^\d.]", "", val_str)
    try: return float(clean)
    except: return None

def get_column_mapping(df):
    def find_col(name_part, exclude=None):
        for c in df.columns:
            if name_part.lower() in c.lower():
                if exclude and exclude.lower() in c.lower(): continue
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

def build_smart_link(label, raw_id, row):
    val = clean_val(raw_id)
    barcode = clean_val(row.get("Barkod_Int", ""))
    if label == "Aksiyon":
        hidden_link = row.get("Hidden_Link")
        if pd.notna(hidden_link) and str(hidden_link).startswith("http"): return str(hidden_link)
        if val: return f"https://www.akakce.com/arama/?q={val}"
        if barcode: return f"https://www.akakce.com/arama/?q={barcode}"
        return None
    if val.startswith("http"): return val
    if label == "Braun Shop":
        gs_link = row.get("GS_BS_Link")
        if pd.notna(gs_link) and str(gs_link).startswith("http"): return str(gs_link)
        if val: return f"https://www.braunshop.com.tr/index.php?route=product/product&product_id={val}"
        if barcode: return f"https://www.braunshop.com.tr/arama?q={barcode}"
        return None
    if val != "":
        if label == "Trendyol": return f"https://www.trendyol.com/brand/product-p-{val}"
        if label == "Hepsiburada": return f"https://www.hepsiburada.com/product-p-{val}"
        if label == "Amazon": return f"https://www.amazon.com.tr/dp/{val}"
        if label == "Media Markt": return f"https://www.mediamarkt.com.tr/tr/product/_{val}.html"
    if barcode:
        if label == "Media Markt": return f"https://www.mediamarkt.com.tr/tr/search.html?query={barcode}"
        if label == "Teknosa": return f"https://www.teknosa.com/arama/?s={barcode}"
        if label == "Vatan": return f"https://www.vatanbilgisayar.com/arama/{barcode}/"
    return None

# ================= GİZLİ BAĞLANTI & VERİ BİRLEŞTİRME =================
@st.cache_data(ttl=180)  # 3 dakikalık önbellek
def load_and_merge_data():
    client = get_gspread_client()
    if not client:
        st.error("🔒 Güvenlik Hatası: Streamlit Secrets'ta JSON Bilgileri Bulunamadı!")
        return None, ""

    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("Guncel")
        
        update_text = ""
        try:
            update_text = worksheet.acell("N1").value
            update_text = str(update_text).replace('"', '').strip()
        except: pass

        data = worksheet.get_all_values()
        if not data: return None, update_text
            
        df_fiyat = pd.DataFrame(data[1:], columns=data[0])
        df_fiyat.columns = [c.strip() for c in df_fiyat.columns]
        bc_col = next((c for c in df_fiyat.columns if "barkod" in c.lower()), None)
        if bc_col: df_fiyat["Barkod_Int"] = df_fiyat[bc_col].apply(clean_val)
        
        gsheet_bs_links = {}
        try:
            export_data = client.export(SHEET_ID, format='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            wb_gs = openpyxl.load_workbook(io.BytesIO(export_data), data_only=False)
            ws_gs = wb_gs["Guncel"]
            
            headers_gs = [str(c.value).strip() if c.value else "" for c in ws_gs[1]]
            idx_bc_gs = next((i for i, h in enumerate(headers_gs) if "barkod" in h.lower()), None)
            idx_bs_gs = next((i for i, h in enumerate(headers_gs) if "braun shop" in h.lower()), None)
            if idx_bc_gs is not None and idx_bs_gs is not None:
                for r_idx in range(2, ws_gs.max_row + 1):
                    bc_val = clean_val(ws_gs.cell(row=r_idx, column=idx_bc_gs+1).value)
                    bs_cell = ws_gs.cell(row=r_idx, column=idx_bs_gs+1)
                    url = bs_cell.hyperlink.target if bs_cell.hyperlink else None
                    if bc_val and url: gsheet_bs_links[bc_val] = url
        except Exception as e: pass
            
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
                    if bc_val and b_cell.hyperlink: ext_links[bc_val] = b_cell.hyperlink.target
            df_map["Hidden_Link"] = df_map["Barkod_Int"].map(ext_links)
            link_cols = ["Barkod_Int", "TY", "HB", "AMZ", "MM", "TKNS", "VTN", "BS Data ID", "CSS Code", "Hidden_Link"]
            df_map_sub = df_map[[c for c in link_cols if c in df_map.columns]].copy()
            df_final = pd.merge(df_fiyat, df_map_sub, on="Barkod_Int", how="left")
            return df_final.fillna(""), update_text
            
        return df_fiyat.fillna(""), update_text
        
    except Exception as e:
        st.error(f"Google bağlantı hatası: {e}")
        return None, ""

# ================= RENDER TABLO =================
def display_styled_table(df, mapping):
    refs = { "Aksiyon": "CSS Code", "Braun Shop": "BS Data ID", "Media Markt": "MM", "Teknosa": "TKNS", "Vatan": "VTN", "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ" }
    pazaryerleri = ["Aksiyon", "Braun Shop", "Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    
    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    
    for label, real in mapping.items():
        if real:
            count_html = ""
            if label in pazaryerleri:
                valid_count = sum(1 for v in df[real] if parse_price(v) is not None)
                count_html = f'<div style="font-size: 11px; color: var(--header-color); margin-top: 6px; font-weight: 700; letter-spacing: 0.5px; text-transform: none;">{valid_count} Ürün</div>'

            logo_pair = LOGOS.get(label)
            plat_url = PLATFORM_LINKS.get(label)
            
            if logo_pair and logo_pair["light"]:
                l_src = logo_pair["light"]; d_src = logo_pair["dark"]
                inv_class = "invert-logo" if logo_pair["invert_dark"] and label in ["Amazon", "Aksiyon"] else ""
                if plat_url: content = f'<a href="{plat_url}" target="_blank" style="text-decoration:none;"><img src="{l_src}" class="header-logo logo-light" title="{label}"><img src="{d_src}" class="header-logo logo-dark {inv_class}" title="{label}"></a>'
                else: content = f'<img src="{l_src}" class="header-logo logo-light" title="{label}"><img src="{d_src}" class="header-logo logo-dark {inv_class}" title="{label}">'
                
                html += f'<th>{content}{count_html}</th>'
            else: 
                html += f'<th>{label}{count_html}</th>'

    html += '</tr></thead><tbody>'
    
    for _, row in df.iterrows():
        html += '<tr>'
        for label, real in mapping.items():
            if not real: continue
            val = str(row[real]); d_val = "" if val.lower() in ["nan", "none", ""] else val; style = ""
            bs_col_name = mapping.get("Braun Shop")
            
            if label in ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"] and bs_col_name:
                p_ref = parse_price(row[bs_col_name]); p_curr = parse_price(d_val)
                if p_ref and p_curr:
                    if p_curr == p_ref: style = 'background-color: #d4edda; color: #155724; font-weight: 600;' 
                    elif p_curr > p_ref: style = 'background-color: #fff3cd; color: #856404; font-weight: 600;' 
                    else: style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;' 
                    
            if not style and d_val:
                if any(x in label.lower() for x in ["barkod", "kodu", "grup", "marka"]): style = 'background-color: transparent;'
                else: style = 'background-color: var(--pill-default-bg);'
                
            map_key = refs.get(label); target_id = row.get(map_key, "")
            url = build_smart_link(label, target_id, row)
            
            if url and d_val: html += f'<td><a href="{url}" target="_blank" class="data-link"><span class="data-pill" style="{style}">{d_val}</span></a></td>'
            else: html += f'<td><span class="data-pill" style="{style}">{d_val}</span></td>'
        html += '</tr>'
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

# ================= MAIN =================
col_title, col_update = st.columns([3, 1])

with col_title:
    online_users = track_user_presence()
    
    # Online rozeti HTML'i (HTML Parser sızıntısı tamamen engellendi)
    online_badge = f'<div class="online-badge-container"><span style="height: 8px; width: 8px; background-color: #00ff00; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px #00ff00; margin-right: 6px;"></span><span style="color: #00ff00; font-size: 13px; font-weight: 600; white-space: nowrap;">{online_users} Online</span></div>'

    if SYSTEM_LOGO["light"]:
        l_sys = SYSTEM_LOGO["light"]
        st.markdown(f'<div class="main-logo-container"><img src="{l_sys}" class="main-system-logo"><h1 class="main-title-text">Aksiyon Raporu</h1>{online_badge}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="main-logo-container"><h1 class="main-title-text">📊 Aksiyon Raporu</h1>{online_badge}</div>', unsafe_allow_html=True)

res = load_and_merge_data()
df_data = res[0] if res else None
update_text = res[1] if res else ""

with col_update:
    if update_text: 
        st.markdown(f'<div class="update-badge">🔄 {update_text}</div>', unsafe_allow_html=True)

if df_data is not None:
    mapping = get_column_mapping(df_data)
    alt_grup_col = mapping.get("Alt Grup")
    
    if alt_grup_col and alt_grup_col in df_data.columns:
        gruplar = []
        for x in df_data[alt_grup_col].dropna():
            v = str(x).strip()
            if v != "" and v not in gruplar: gruplar.append(v)
    else: 
        gruplar = []

    col_search, col_grup, col_plat, col_stat, col_btn = st.columns([2.5, 2, 2, 2.5, 1.5])
    with col_search: search = st.text_input("🔍 Ürün Ara...")
    with col_grup: filter_grup = st.multiselect("📂 Alt Grup", gruplar, placeholder="Tümü (Çoklu Seçim)")
    with col_plat: filter_platform = st.selectbox("🛒 Platform", ["Tümü", "Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"])
    with col_stat: filter_status = st.selectbox("🎨 Renge Göre", ["Tümü", "🔴 Kırmızı (↓)", "🟢 Yeşil (=)", "🟡 Sarı (↑)"])

    if search: df_data = df_data[df_data.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    
    if filter_grup and alt_grup_col: 
        if "Tümü" not in filter_grup: 
            df_data = df_data[df_data[alt_grup_col].astype(str).str.strip().isin(filter_grup)]
            
    if filter_status != "Tümü":
        bs_col = mapping.get("Braun Shop")
        if bs_col:
            p_list = [filter_platform] if filter_platform != "Tümü" else ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
            actual_cols = [mapping.get(p) for p in p_list]; actual_cols = [c for c in actual_cols if c] 
            def check_color(row):
                bs_val = parse_price(row[bs_col])
                if bs_val is None: return False
                for col in actual_cols:
                    p_val = parse_price(row[col])
                    if p_val is not None:
                        if "🔴" in filter_status and p_val < bs_val: return True
                        if "🟢" in filter_status and p_val == bs_val: return True
                        if "🟡" in filter_status and p_val > bs_val: return True
                return False
            df_data = df_data[df_data.apply(check_color, axis=1)]

    # ================= EXCEL İNDİRME VE FORMATLAMA =================
    tr_time_now = datetime.utcnow() + timedelta(hours=3)
    current_time_str = tr_time_now.strftime("%d-%m-%Y_%H-%M")
    excel_filename = f"Aksiyon_Raporu_{current_time_str}.xlsx"
    
    export_cols = [real for label, real in mapping.items() if real in df_data.columns]
    df_export = df_data[export_cols].copy()
    
    # 1. Fiyatları sayıya çevir
    price_platforms = ["Aksiyon", "Braun Shop", "Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    price_cols = [mapping.get(p) for p in price_platforms if mapping.get(p) in df_export.columns]
    for col_name in price_cols:
        df_export[col_name] = df_export[col_name].apply(parse_price)
        
    # 2. Barkod sütununu sayıya çevir (varsa)
    barcode_col = mapping.get("Barkod")
    if barcode_col and barcode_col in df_export.columns:
        def parse_barcode(v):
            try: return int(float(str(v).replace(' ', '')))
            except: return v
        df_export[barcode_col] = df_export[barcode_col].apply(parse_barcode)
    
    # 3. Excel oluştur ve hücre biçimlerini ayarla (Openpyxl)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Aksiyon_Raporu')
        
        workbook = writer.book
        worksheet = writer.sheets['Aksiyon_Raporu']
        
        # Sütunları dolaşıp tek tek hücre formatlarını ve genişliklerini düzeltiyoruz
        for idx, col_name in enumerate(df_export.columns):
            excel_col_idx = idx + 1
            col_letter = openpyxl.utils.get_column_letter(excel_col_idx)
            
            if col_name in price_cols:
                worksheet.column_dimensions[col_letter].width = 12
                for row in range(2, len(df_export) + 2):
                    worksheet.cell(row=row, column=excel_col_idx).number_format = '#,##0.00'
                    
            elif col_name == barcode_col:
                worksheet.column_dimensions[col_letter].width = 16
                for row in range(2, len(df_export) + 2):
                    worksheet.cell(row=row, column=excel_col_idx).number_format = '0'
            else:
                worksheet.column_dimensions[col_letter].width = 15
                
    with col_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.download_button("📥 Excel'e Aktar", output.getvalue(), excel_filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True)

    display_styled_table(df_data, mapping)

# ================= OTOMATİK SESSİZ RERUN TETİKLEYİCİ =================
components.html(
    """
    <script>
    const parentWindow = window.parent;
    setTimeout(() => {
        const rerunButton = parentWindow.document.querySelector('.stApp [data-testid="stHeader"] button');
        if (rerunButton) {
            rerunButton.click();
        } else {
            parentWindow.location.reload();
        }
    }, 180000); 
    </script>
    """, height=0, width=0
)
