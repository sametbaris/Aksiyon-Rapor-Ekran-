import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
import requests

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Fiyat Analizi", page_icon="⚖️", layout="wide")

SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0"
SHEET_NAME = "Guncel"

# ================= MODERN CSS =================
st.markdown("""
<style>
    .table-container { width: 100%; margin-top: 10px; overflow-x: auto; }
    .custom-table { width: 100%; table-layout: auto; border-collapse: separate; border-spacing: 0 4px; font-family: 'Inter', sans-serif; }
    .custom-table th { color: #888; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 1px; padding: 15px 20px; text-align: left; white-space: nowrap; }
    .custom-table td { padding: 12px 20px; text-align: left; color: #333; font-size: 14px; white-space: nowrap; transition: background-color 0.2s ease; }
    .custom-table tr:hover td { background-color: #f8f9fa !important; }
    
    .update-badge {
        text-align: right; color: #666; font-size: 13px; font-weight: 500;
        background: #f1f3f4; padding: 8px 18px; border-radius: 20px;
        display: inline-block; float: right; border: 1px solid #e0e0e0;
    }
    .stTextInput input { border-radius: 12px !important; border: 1px solid #eee !important; }
</style>
""", unsafe_allow_html=True)

# ================= VERİ ÇEKME FONKSİYONLARI =================
def parse_price(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", ""]: return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").replace(".", "").replace(",", ".").strip()
    clean = re.sub(r"[^\d.]", "", val_str)
    try: return float(clean)
    except: return None

@st.cache_data(ttl=60)
def get_last_update():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&range=N1"
    try:
        response = requests.get(url)
        return response.text.replace('"', '').strip()
    except: return "Bilinmiyor"

@st.cache_data(ttl=60) 
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]

        # 🎯 DİNAMİK FİLTRE: 'N' kolonunu ve 'Unnamed' kolonları sil, gerisini tut.
        # Bu sayede Barkod, Alt Grup, SKU ne varsa otomatik gelir.
        black_list = ["N", "Pazaryeri", "Son Güncelleme"]
        cols_to_keep = [c for c in df.columns if c not in black_list and not c.startswith("Unnamed")]
        df = df[cols_to_keep]
        
        df = df.replace(["None", "nan", "NaN", "null"], "")
        df = df.fillna("")
        return df
    except: return None

# ================= RENDER MOTORU =================
def display_styled_table(df):
    # Kıyaslama yapılacak rakip kolonlar
    target_cols = ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    
    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for col in df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for col in df.columns:
            val = str(row[col])
            display_val = "" if val.lower() in ["nan", "none", ""] else val
            inner_style = "padding: 6px 12px; display: inline-block;"
            
            if col in target_cols and "Braun Shop" in df.columns:
                ref_val = parse_price(row["Braun Shop"])
                curr_val = parse_price(display_val)
                if ref_val and curr_val:
                    if curr_val == ref_val:
                        inner_style += 'background-color: #e8f5e9; color: #2e7d32; border-radius: 20px; font-weight: 600;'
                    else:
                        inner_style += 'background-color: #ffebee; color: #c62828; border-radius: 20px; font-weight: 600;'
            
            html += f'<td><span style="{inner_style}">{display_val}</span></td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================= ÜST PANEL =================
col_title, col_update = st.columns([2, 1])
with col_title: st.title("📊 Fiyat Analiz Merkezi")
with col_update:
    last_update = get_last_update()
    st.markdown(f'<div class="update-badge">🔄 Son Güncelleme: {last_update}</div>', unsafe_allow_html=True)

# ================= ANA İÇERİK =================
df = load_data()
if df is not None:
    search = st.text_input("🔍 Ürün adı, barkod veya alt grup ile arama yapın...")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    display_styled_table(df)

    now = datetime.now().strftime("%d.%m.%Y_%H-%M")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    st.write("<br>", unsafe_allow_html=True)
    st.download_button(
        label="📥 Güncel Verileri Excel'e Aktar",
        data=output.getvalue(),
        file_name=f"Fiyat_Raporu_{now}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.error("Veriler yüklenemedi.")
