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
from streamlit_autorefresh import st_autorefresh

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

# ================= TEMA DEDEKTÖRÜ & GİZLİ NINJA ÇİPİ =================
components.html(
    """
    <script>
    try {
        const parentDoc = window.parent.document;
        
        // Akakçe engeline karşı global referrer gizleyici (Olmazsa resim yüklenmez)
        if (!parentDoc.getElementById("ninja-referer")) {
            let meta = parentDoc.createElement("meta");
            meta.id = "ninja-referer";
            meta.name = "referrer";
            meta.content = "no-referrer";
            parentDoc.head.appendChild(meta);
        }

        setInterval(() => {
            const bgColor = window.getComputedStyle(parentDoc.body).backgroundColor;
            let rgb = bgColor.match(/\\d+/g);
            if (rgb && rgb.length >= 3) {
                let brightness = (parseInt(rgb[0]) * 299 + parseInt(rgb[1]) * 587 + parseInt(rgb[2]) * 114) / 1000;
                
                parentDoc.documentElement.style.setProperty('--dynamic-bg-color', bgColor);
                parentDoc.documentElement.style.setProperty('--dynamic-shadow', brightness < 128 ? 'rgba(0, 0, 0, 0.8)' : 'rgba(0, 0, 0, 0.12)');
                
                let styleTag = parentDoc.getElementById("logo-theme-style");
                if (!styleTag) {
                    styleTag = parentDoc.createElement("style");
                    styleTag.id = "logo-theme-style";
                    parentDoc.head.appendChild(styleTag);
                }
                
                if (brightness < 128) {
                    styleTag.innerHTML = `.logo-light { display: none !important; } .logo-dark { display: inline-block !important; } .logo-dark.invert-logo { filter: brightness(0) invert(1) !important; } .logo-dark.invert-logo:hover { filter: brightness(0) invert(1) drop-shadow(0px 6px 10px rgba(255,255,255,0.4)) !important; }`;
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
    html, body, [class*="css"] { font-size: 14px !important; }
    .block-container { max-width: 100% !important; padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    header[data-testid="stHeader"] { height: 2.5rem !important; background: transparent !important; }
    * { -webkit-font-smoothing: antialiased !important; -moz-osx-font-smoothing: grayscale !important; text-rendering: optimizeLegibility !important; }
    :root { --header-color: #888; --pill-default-bg: rgba(128, 128, 128, 0.1); }
    
    .logo-light { display: inline-block !important; }
    .logo-dark { display: none !important; }
    .dark-theme .logo-light, html[data-theme="dark"] .logo-light { display: none !important; }
    .dark-theme .logo-dark, html[data-theme="dark"] .logo-dark { display: inline-block !important; }
    .dark-theme .logo-dark.invert-logo, html[data-theme="dark"] .logo-dark.invert-logo { filter: brightness(0) invert(1) !important; }

    .main-logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
    .main-system-logo { height: 50px; width: auto; object-fit: contain; transition: height 0.3s; }
    .main-title-text { margin: 0; display: inline-block; font-size: 1.8rem; font-weight: 700; transition: font-size 0.3s; }
    
    .online-badge-container { display: flex; align-items: center; gap: 6px; background: rgba(0, 255, 0, 0.1); padding: 4px 12px; border-radius: 20px; border: 1px solid rgba(0, 255, 0, 0.2); }
    
    @media (max-width: 768px) {
        .main-logo-container { flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 8px; width: 100%; }
        .main-system-logo { height: 40px; }
        .main-title-text { font-size: 1.4rem; }
        .online-badge-container { margin-left: 0 !important; margin-top: 2px; }
    }
    
    .table-container { width: 100%; margin-top: 10px; overflow: auto; max-height: 65vh; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: none !important; }
    .table-container::-webkit-scrollbar { width: 5px !important; height: 5px !important; }
    .table-container::-webkit-scrollbar-thumb { background-color: rgba(128, 128, 128, 0.15) !important; border-radius: 10px !important; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate !important; border-spacing: 0 !important; font-family: 'Inter', sans-serif; border: none !important; }
    
    .header-logo { height: 26px; width: auto; max-width: 120px; object-fit: contain; transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), filter 0.3s ease; }
    .header-logo:hover { transform: scale3d(1.15, 1.15, 1); filter: drop-shadow(0px 6px 10px rgba(0,0,0,0.25)); }
    
    .custom-table thead th { position: sticky; top: 0px !important; z-index: 20; padding: 12px 18px; text-align: center; color: var(--header-color); font-weight: 500; text-transform: uppercase; font-size: 10px; background-color: var(--dynamic-bg-color, #ffffff) !important; box-shadow: 0 8px 15px -4px var(--dynamic-shadow, rgba(0,0,0,0.15)) !important; border-bottom: 1px solid rgba(128,128,128,0.1) !important; }
    .custom-table td { padding: 8px 10px; text-align: center; white-space: nowrap; border-bottom: 1px solid rgba(128,128,128,0.06) !important; }
    
    /* ========================================================= */
    /* HOVER THUMBNAIL (SİLÜET GÖLGESİ & LIFT)                   */
    /* ========================================================= */
    .sku-wrapper { position: relative; display: inline-block; cursor: pointer; }
    
    .sku-thumb { 
        visibility: hidden; 
        position: absolute; 
        left: 110%; 
        top: 50%; 
        transform: translateY(-50%) translateX(10px); 
        opacity: 0; 
        transition: all 0.2s ease-in-out;
        background-color: var(--dynamic-bg-color, #ffffff);
        padding: 6px; 
        border-radius: 12px; 
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 999999 !important; /* Her şeyin üstünde olmalı */
        border: 1px solid rgba(128,128,128,0.2);
        pointer-events: none; 
    }
    
    .sku-thumb img { 
        width: 150px; 
        height: 150px; 
        object-fit: contain; 
        border-radius: 8px; 
        display: block; 
        background: white; 
    }
    
    /* Çentik */
    .sku-thumb::after {
        content: ''; position: absolute; top: 50%; right: 100%; margin-top: -8px;
        border-width: 8px; border-style: solid;
        border-color: transparent var(--dynamic-bg-color, #ffffff) transparent transparent;
    }
    
    /* Hover olunca göster */
    .sku-wrapper:hover .sku-thumb { 
        visibility: visible; 
        opacity: 1; 
        transform: translateY(-50%) translateX(0px); 
    }
    
    /* Satırın z-index değerini hover'da yükselt (Pencerenin kesilmemesi için) */
    .custom-table tr:hover { z-index: 999; position: relative; }
    /* ========================================================= */

    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 5px 12px; display: inline-flex; align-items: center; justify-content: center; border-radius: 20px; font-size: 13px; line-height: 1.2; transform: translateY(0); transition: transform 0.2s ease, box-shadow 0.2s ease; }
    a.data-link:hover .data-pill { transform: translateY(-2px); box-shadow: 0px 5px 12px rgba(0,0,0,0.15); }
    
    .update-badge { text-align: right; color: var(--header-color); font-size: 11px; background: var(--pill-default-bg); padding: 5px 14px; border-radius: 30px; display: inline-block; float: right; margin-top: 10px; }
    div[data-testid="stDownloadButton"] button, div[data-testid="stButton"] button { width: 100%; border-radius: 20px; font-weight: 600; border: 1px solid #ddd; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ================= GSPREAD KİMLİK DOĞRULAMA =================
@st.cache_resource
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        elif os.path.exists("service_account.json"):
            creds = Credentials.from_service_account_file("service_account.json", scopes=scope)
        else: return None
        return gspread.authorize(creds)
    except Exception: return None

# ================= ZİYARETÇİ TAKİP =================
@st.cache_data(ttl=60)
def get_online_count():
    client = get_gspread_client()
    if not client: return 1
    try:
        sh = client.open_by_key(SHEET_ID)
        log_sheet = sh.worksheet("Ziyaretci_Log")
        all_logs = log_sheet.get_all_records()
        tr_now = datetime.utcnow() + timedelta(hours=3)
        two_mins_ago = tr_now - timedelta(minutes=2)
        count = 0
        for r in all_logs:
            try:
                ls = datetime.strptime(str(r.get('Son_Gorulme', '')), "%Y-%m-%d %H:%M:%S")
                if ls > two_mins_ago: count += 1
            except: pass
        return max(1, count)
    except: return 1

def track_presence():
    if 'user_id' not in st.session_state: st.session_state.user_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow() + timedelta(hours=3)
    client = get_gspread_client()
    if client:
        try:
            sh = client.open_by_key(SHEET_ID); log_sheet = sh.worksheet("Ziyaretci_Log")
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            cell = log_sheet.find(st.session_state.user_id)
            if cell: log_sheet.update_cell(cell.row, 2, now_str)
            else: log_sheet.append_row([st.session_state.user_id, now_str])
        except: pass
    return get_online_count()

# ================= VERİ MOTORU =================
def clean_val(val):
    if pd.isna(val) or str(val).strip().lower() in ["nan", "none", ""]: return ""
    v = str(val).strip()
    return v if v.startswith("http") else v.split('.')[0]

def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", ""]: return None
    v = str(val).lower().replace("tl","").replace("₺","").replace(".","").replace(",",".").strip()
    try: return float(re.sub(r"[^\d.]", "", v))
    except: return None

def get_mapping(df):
    def f(p):
        for c in df.columns:
            if p.lower() in c.lower(): return c
        return None
    return { "Marka": f("Marka"), "Ürün Adı": f("Ürün Adı"), "Barkod": f("Barkod"), "Ürün Kodu": f("Kodu"), "Alt Grup": f("Grup"), "Aksiyon": f("Aksiyon"), "Braun Shop": f("Braun Shop"), "Media Markt": f("Media Markt"), "Teknosa": f("Teknosa"), "Vatan": f("Vatan"), "Trendyol": f("Trendyol"), "Hepsiburada": f("Hepsiburada") or f("Hepsi"), "Amazon": f("Amazon") }

def build_link(label, raw_id, row):
    val = clean_val(raw_id); bc = clean_val(row.get("Barkod_Int", ""))
    if label == "Aksiyon":
        hl = row.get("Hidden_Link")
        if pd.notna(hl) and str(hl).startswith("http"): return str(hl)
        return f"https://www.akakce.com/arama/?q={val or bc}"
    if val.startswith("http"): return val
    if label == "Braun Shop":
        gl = row.get("GS_BS_Link")
        if pd.notna(gl) and str(gl).startswith("http"): return str(gl)
        return f"https://www.braunshop.com.tr/arama?q={val or bc}"
    if val:
        if label == "Trendyol": return f"https://www.trendyol.com/brand/product-p-{val}"
        if label == "Hepsiburada": return f"https://www.hepsiburada.com/product-p-{val}"
        if label == "Amazon": return f"https://www.amazon.com.tr/dp/{val}"
    if bc:
        if label == "Media Markt": return f"https://www.mediamarkt.com.tr/tr/search.html?query={bc}"
        if label == "Teknosa": return f"https://www.teknosa.com/arama/?s={bc}"
        if label == "Vatan": return f"https://www.vatanbilgisayar.com/arama/{bc}/"
    return None

@st.cache_data(ttl=180)  
def load_data():
    client = get_gspread_client()
    if not client: return None, ""
    try:
        sh = client.open_by_key(SHEET_ID); ws = sh.worksheet("Guncel")
        update_text = ""
        try: update_text = str(ws.acell("N1").value).replace('"', '').strip()
        except: pass
        data = ws.get_all_values()
        if not data: return None, ""
        df = pd.DataFrame(data[1:], columns=[c.strip() for c in data[0]])
        bc_col = next((c for c in df.columns if "barkod" in c.lower()), "Barkod")
        df["Barkod_Int"] = df[bc_col].apply(clean_val)
        
        if os.path.exists(MAPPING_FILE):
            df_m = pd.read_excel(MAPPING_FILE, engine='openpyxl', dtype=str)
            df_m.columns = [c.strip() for c in df_m.columns]
            m_bc = next((c for c in df_m.columns if "barkod" in c.lower()), "Barkod")
            df_m["Barkod_Int"] = df_m[m_bc].apply(clean_val)
            cols = ["Barkod_Int", "TY", "HB", "AMZ", "MM", "TKNS", "VTN", "BS Data ID", "CSS Code", "Hidden_Link", "Gorsel_URL"]
            df = pd.merge(df, df_m[[c for c in cols if c in df_m.columns]], on="Barkod_Int", how="left")
        return df.fillna(""), update_text
    except: return None, ""

# ================= TABLO RENDER =================
def render_table(df, mapping):
    refs = { "Aksiyon": "CSS Code", "Braun Shop": "BS Data ID", "Media Markt": "MM", "Teknosa": "TKNS", "Vatan": "VTN", "Trendyol": "TY", "Hepsiburada": "HB", "Amazon": "AMZ" }
    
    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for label, real in mapping.items():
        if not real: continue
        logo = LOGOS.get(label); plat_url = PLATFORM_LINKS.get(label)
        if logo and logo["light"]:
            inv = "invert-logo" if logo["invert_dark"] and label in ["Amazon", "Aksiyon"] else ""
            content = f'<img src="{logo["light"]}" class="header-logo logo-light"><img src="{logo["dark"]}" class="header-logo logo-dark {inv}">'
            if plat_url: content = f'<a href="{plat_url}" target="_blank">{content}</a>'
            html += f'<th>{content}</th>'
        else: html += f'<th>{label}</th>'
    html += '</tr></thead><tbody>'
    
    for _, row in df.iterrows():
        html += '<tr>'
        for label, real in mapping.items():
            if not real: continue
            val = str(row[real]); d_val = "" if val.lower() in ["nan","none",""] else val
            style = ""
            bs_col = mapping.get("Braun Shop")
            if label in ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"] and bs_col:
                p_ref = parse_price(row[bs_col]); p_curr = parse_price(d_val)
                if p_ref and p_curr:
                    if p_curr == p_ref: style = 'background-color: #d4edda; color: #155724; font-weight:600;'
                    elif p_curr > p_ref: style = 'background-color: #fff3cd; color: #856404; font-weight:600;'
                    else: style = 'background-color: #f8d7da; color: #721c24; font-weight:600;'
            
            if not style and d_val: style = 'background-color: transparent;' if any(x in label.lower() for x in ["barkod","kodu","marka"]) else 'background-color: var(--pill-default-bg);'
            
            # --- ÖZEL SKM/THUMBNAIL MANTIĞI ---
            img_url = str(row.get("Gorsel_URL", "")).strip()
            is_sku = (label == "Ürün Kodu") and img_url.startswith("http")
            
            inner = f'<span class="data-pill" style="{style}">{d_val}</span>'
            if is_sku:
                inner = f'<div class="sku-wrapper">{inner}<div class="sku-thumb"><img src="{img_url}"></div></div>'
            
            url = build_link(label, row.get(refs.get(label, "")), row)
            if url and d_val: html += f'<td><a href="{url}" target="_blank" class="data-link">{inner}</a></td>'
            else: html += f'<td>{inner}</td>'
        html += '</tr>'
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

# ================= UI =================
st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
col_t, col_u = st.columns([3, 1])

with col_t:
    online = track_presence()
    badge = f'<div class="online-badge-container"><span style="height: 8px; width: 8px; background-color: #00ff00; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px #00ff00; margin-right: 6px;"></span><span style="color: #00ff00; font-size: 11px; font-weight: 600;">{online} Online</span></div>'
    if SYSTEM_LOGO["light"]: st.markdown(f'<div class="main-logo-container"><img src="{SYSTEM_LOGO["light"]}" class="main-system-logo"><h1 class="main-title-text">Aksiyon Raporu</h1>{badge}</div>', unsafe_allow_html=True)
    else: st.markdown(f'<div class="main-logo-container"><h1 class="main-title-text">📊 Aksiyon Raporu</h1>{badge}</div>', unsafe_allow_html=True)

df_raw, up_txt = load_data()
with col_u:
    if up_txt: st.markdown(f'<div class="update-badge">🔄 {up_txt}</div>', unsafe_allow_html=True)

if df_raw is not None:
    mapping = get_mapping(df_raw)
    gr_col = mapping.get("Alt Grup")
    gruplar = list(dict.fromkeys([str(x).strip() for x in df_raw[gr_col].dropna() if str(x).strip()])) if gr_col in df_raw.columns else []

    c1, c2, c3, c4, c5 = st.columns([2.5, 2.2, 2.2, 1.5, 2.0])
    with c1: search = st.text_input("🔍 Ürün Ara...", key="s_val")
    with c2: f_gr = st.multiselect("📂 Alt Grup", gruplar, key="g_val", placeholder="Tümü")
    with c3: f_pl = st.selectbox("🛒 Platform", ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"], index=None, key="p_val", placeholder="Tümü")
    with c4: f_st = st.selectbox("🎨 Renk", ["🔴 Kırmızı (↓)", "🟢 Yeşil (=)", "🟡 Sarı (↑)"], index=None, key="st_val", placeholder="Tümü")
    
    if search: df_raw = df_raw[df_raw.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    if f_gr: df_raw = df_raw[df_raw[gr_col].astype(str).str.strip().isin(f_gr)]
    if f_st:
        bs = mapping.get("Braun Shop")
        if bs:
            plats = [f_pl] if f_pl else ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
            cols = [mapping.get(p) for p in plats if mapping.get(p)]
            def check(r):
                b_p = parse_price(r[bs])
                if b_p is None: return False
                for c in cols:
                    v_p = parse_price(r[c])
                    if v_p:
                        if "🔴" in f_st and v_p < b_p: return True
                        if "🟢" in f_st and v_p == b_p: return True
                        if "🟡" in f_st and v_p > b_p: return True
                return False
            df_raw = df_raw[df_raw.apply(check, axis=1)]

    with c5:
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1: st.button("🧹 Temizle", on_click=lambda: st.session_state.clear(), use_container_width=True)
        with b2: 
            output = io.BytesIO()
            df_raw.to_excel(output, index=False)
            st.download_button("📥 Excel", output.getvalue(), "Rapor.xlsx", use_container_width=True)

    render_table(df_raw, mapping)

st_autorefresh(interval=180000, key="refresh")
