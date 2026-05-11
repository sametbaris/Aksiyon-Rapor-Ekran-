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
MAPPING_FILE = "Aksiyon_Mapping_Resimli.xlsx"

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
        
        // Akakçe engeline karşı global referrer gizleyici
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
    
    .main-logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
    .main-system-logo { height: 50px; width: auto; object-fit: contain; }
    .main-title-text { margin: 0; display: inline-block; font-size: 1.8rem; font-weight: 700; }
    
    .online-badge-container { display: flex; align-items: center; gap: 6px; background: rgba(0, 255, 0, 0.1); padding: 4px 12px; border-radius: 20px; border: 1px solid rgba(0, 255, 0, 0.2); }
    
    /* TABLO TASARIMI */
    .table-container { width: 100%; margin-top: 10px; overflow: auto; max-height: 65vh; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate !important; border-spacing: 0 !important; font-family: 'Inter', sans-serif; }
    .custom-table thead th { position: sticky; top: 0px !important; z-index: 20; padding: 12px 18px; text-align: center; color: var(--header-color); font-weight: 500; font-size: 10px; background-color: var(--dynamic-bg-color, #ffffff) !important; box-shadow: 0 8px 15px -4px var(--dynamic-shadow, rgba(0,0,0,0.15)) !important; border-bottom: 1px solid rgba(128,128,128,0.1) !important; }
    .custom-table td { padding: 8px 10px; text-align: center; white-space: nowrap; border-bottom: 1px solid rgba(128,128,128,0.06) !important; }
    
    /* HOVER EFEKTİ & LIFT */
    .data-link { text-decoration: none; color: inherit; display: inline-block; width: 100%; }
    .data-pill { padding: 5px 12px; display: inline-flex; align-items: center; justify-content: center; border-radius: 20px; font-size: 13px; line-height: 1.2; transform: translateY(0); transition: transform 0.2s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.2s; }
    a.data-link:hover .data-pill { transform: translateY(-3px); box-shadow: 0px 5px 12px rgba(0,0,0,0.15); }

    /* ========================================================= */
    /* HOVER THUMBNAIL (GÖRSEL POP-UP) SİHRİ                     */
    /* ========================================================= */
    .sku-wrapper { position: relative; display: inline-block; cursor: pointer; }
    .sku-thumb { 
        visibility: hidden; position: absolute; left: 110%; top: 50%; 
        transform: translateY(-50%) translateX(10px); opacity: 0; 
        transition: all 0.2s ease-in-out; background-color: var(--dynamic-bg-color, #ffffff);
        padding: 5px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 999999 !important; border: 1px solid rgba(128,128,128,0.2); pointer-events: none; 
    }
    .sku-thumb img { width: 150px; height: 150px; object-fit: contain; border-radius: 8px; background: white; display: block; }
    .sku-thumb::after { content: ''; position: absolute; top: 50%; right: 100%; margin-top: -8px; border-width: 8px; border-style: solid; border-color: transparent var(--dynamic-bg-color, #ffffff) transparent transparent; }
    .sku-wrapper:hover .sku-thumb { visibility: visible; opacity: 1; transform: translateY(-50%) translateX(0px); }
    .custom-table tr:hover { z-index: 1000; position: relative; }
    /* ========================================================= */

    .header-logo { height: 26px; width: auto; max-width: 120px; object-fit: contain; transition: transform 0.3s, filter 0.3s; }
    .header-logo:hover { transform: scale(1.15); filter: drop-shadow(0px 6px 10px rgba(0,0,0,0.25)); }
</style>
""", unsafe_allow_html=True)

# ... (GSPREAD, ZİYARETÇİ, YARDIMCI FONKSİYONLAR AYNI KALIYOR)

@st.cache_data(ttl=180)  
def load_and_merge_data():
    client = get_gspread_client()
    if not client: return None, ""
    try:
        sh = client.open_by_key(SHEET_ID); worksheet = sh.worksheet("Guncel")
        update_text = ""
        try: update_text = str(worksheet.acell("N1").value).replace('"', '').strip()
        except: pass
        data = worksheet.get_all_values()
        if not data: return None, update_text
        df_fiyat = pd.DataFrame(data[1:], columns=[c.strip() for c in data[0]])
        df_fiyat["Barkod_Int"] = df_fiyat[next((c for c in df_fiyat.columns if "barkod" in c.lower()), "Barkod")].apply(clean_val)
        
        if os.path.exists(MAPPING_FILE):
            df_map = pd.read_excel(MAPPING_FILE, engine='openpyxl', dtype=str)
            df_map.columns = [c.strip() for c in df_map.columns]
            df_map["Barkod_Int"] = df_map[next((c for c in df_map.columns if "barkod" in c.lower()), "Barkod")].apply(clean_val)
            # Gorsel_URL sütununu da listeye ekliyoruz
            link_cols = ["Barkod_Int", "TY", "HB", "AMZ", "MM", "TKNS", "VTN", "BS Data ID", "CSS Code", "Hidden_Link", "Gorsel_URL"]
            df_final = pd.merge(df_fiyat, df_map[[c for c in link_cols if c in df_map.columns]], on="Barkod_Int", how="left")
            return df_final.fillna(""), update_text
        return df_fiyat.fillna(""), update_text
    except: return None, ""

def display_styled_table(df, mapping):
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
            val = str(row[real]); d_val = "" if val.lower() in ["nan", "none", ""] else val; style = ""
            bs_col = mapping.get("Braun Shop")
            if label in ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"] and bs_col:
                p_ref = parse_price(row[bs_col]); p_curr = parse_price(d_val)
                if p_ref and p_curr:
                    if p_curr == p_ref: style = 'background-color: #d4edda; color: #155724; font-weight: 600;' 
                    elif p_curr > p_ref: style = 'background-color: #fff3cd; color: #856404; font-weight: 600;' 
                    else: style = 'background-color: #f8d7da; color: #721c24; font-weight: 600;' 
            if not style and d_val: style = 'background-color: transparent;' if any(x in label.lower() for x in ["barkod", "kodu", "marka"]) else 'background-color: var(--pill-default-bg);'
            
            # --- HOVER THUMBNAIL EKLEMESİ ---
            img_url = str(row.get("Gorsel_URL", "")).strip()
            is_sku = (label == "Ürün Kodu") and img_url.startswith("http")
            inner_content = f'<span class="data-pill" style="{style}">{d_val}</span>'
            if is_sku: inner_content = f'<div class="sku-wrapper">{inner_content}<div class="sku-thumb"><img src="{img_url}" referrerpolicy="no-referrer"></div></div>'
            
            url = build_smart_link(label, row.get(refs.get(label, ""), ""), row)
            if url and d_val: html += f'<td><a href="{url}" target="_blank" class="data-link">{inner_content}</a></td>'
            else: html += f'<td>{inner_content}</td>'
        html += '</tr>'
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)

# ... (RESTİ ESKİSİYLE BİREBİR AYNI, ANA DÖNGÜ VE FİLTRELER DAHİL)
