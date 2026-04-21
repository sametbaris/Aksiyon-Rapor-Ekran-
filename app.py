import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

# ================= SAYFA AYARLARI =================
st.set_page_config(page_title="Fiyat Analizi", page_icon="⚖️", layout="wide")

SHEET_ID = "BURAYA_SHEET_ID_GELECEK" # Kendi ID'ni yapıştır
SHEET_NAME = "Guncel"

# ================= MODERN CSS (YUVARLAK HATLAR VE HOVER) =================
st.markdown("""
<style>
    /* Tablo Konteynırı */
    .table-container {
        width: 100%;
        margin-top: 20px;
    }
    
    /* Sabit ve Eşit Genişlikli Tablo Yapısı */
    .custom-table {
        width: 100%;
        table-layout: fixed; /* TÜM KOLONLARI EŞİTLER */
        border-collapse: separate;
        border-spacing: 0 8px; /* Satırlar arası boşluk */
        font-family: 'Inter', sans-serif;
    }
    
    /* Başlıklar */
    .custom-table th {
        color: #999;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 1px;
        padding: 15px;
        text-align: center;
        border: none;
    }
    
    /* Hücreler (Normal Durum) */
    .custom-table td {
        padding: 14px;
        text-align: center;
        background-color: transparent;
        color: #333;
        font-size: 14px;
        border: 2px solid transparent; /* Gizli çerçeve */
        transition: all 0.2s ease-in-out;
    }

    /* HAP ŞEKLİNDE HOVER ETKİSİ */
    .custom-table td:hover {
        border: 2px solid #4CAF50 !important; /* Yeşil çerçeve */
        border-radius: 50px !important; /* Hap şekli */
        background-color: white !important;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
        cursor: pointer;
    }

    /* Arama Kutusu Modernizasyonu */
    .stTextInput input {
        border-radius: 30px !important;
        border: 1px solid #eee !important;
        padding: 12px 25px !important;
        background-color: #f9f9f9 !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= YARDIMCI FONKSİYONLAR =================
def parse_price(val):
    if not val or pd.isna(val): return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").strip()
    clean = re.sub(r"[^\d.,]", "", val_str)
    if not clean: return None
    if "." in clean and "," in clean: clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean: clean = clean.replace(",", ".")
    try: return float(clean)
    except: return None

@st.cache_data(ttl=60) 
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    try:
        df = pd.read_csv(url).fillna("")
        df.columns = [c.strip() for c in df.columns]
        return df
    except: return None

# ================= RENDER MOTORU (HTML TABLO) =================
def display_styled_table(df):
    target_cols = ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    
    html = '<div class="table-container"><table class="custom-table"><thead><tr>'
    for col in df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'

    for _, row in df.iterrows():
        html += '<tr>'
        for col in df.columns:
            val = str(row[col])
            style = ""
            
            # Braun Shop Kıyaslama Mantığı
            if col in target_cols:
                ref_val = parse_price(row["Braun Shop"])
                curr_val = parse_price(val)
                if ref_val and curr_val:
                    if curr_val == ref_val:
                        style = 'background-color: #e8f5e9; color: #2e7d32; border-radius: 50px;'
                    else:
                        style = 'background-color: #ffebee; color: #c62828; border-radius: 50px;'
            
            html += f'<td><div style="{style}">{val if val != "nan" else ""}</div></td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================= ARAYÜZ =================
st.title("⚖️ Fiyat Analiz Merkezi")

df = load_data()

if df is not None:
    search = st.text_input("🔍 Aramak istediğiniz ürünü yazın...")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # Modern tabloyu basıyoruz
    display_styled_table(df)

    # Excel İndirme
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
    st.error("Bağlantı hatası!")
