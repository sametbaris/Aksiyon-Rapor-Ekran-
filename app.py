import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

# ================= AYARLAR =================
st.set_page_config(page_title="Fiyat Karşılaştırma Paneli", page_icon="⚖️", layout="wide")

SHEET_ID = "BURAYA_SHEET_ID_GELECEK" # Lütfen kendi ID'ni buraya yapıştırmayı unutma!
SHEET_NAME = "Guncel"

@st.cache_data(ttl=60) 
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        return df
    except:
        return None

# ================= METNİ SAYIYA ÇEVİRME FİLTRESİ =================
def parse_price(val):
    """CSV'den gelen '1.250,00 TL' gibi metinleri saf sayıya (1250.00) çevirir."""
    if pd.isna(val): return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").strip()
    
    # Rakam, nokta ve virgül dışındaki her şeyi sil
    clean = re.sub(r"[^\d.,]", "", val_str)
    if not clean: return None
    
    # Türkçe fiyat formatını (1.250,00) İngilizce/Matematik formatına (1250.00) çevir
    if "." in clean and "," in clean:
        clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean:
        clean = clean.replace(",", ".")
        
    try:
        return float(clean)
    except:
        return None

# ================= BRAUN SHOP BAZLI RENKLENDİRME =================
def apply_comparative_style(row):
    target_cols = ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    ref_col = "Braun Shop"
    
    styles = ['' for _ in row.index]
    
    # Braun Shop fiyatını saf rakama çevir
    ref_val = parse_price(row[ref_col]) if ref_col in row.index else None
    
    if ref_val is not None and ref_val > 0:
        for col in target_cols:
            if col in row.index:
                col_idx = row.index.get_loc(col)
                # Rakip fiyatı saf rakama çevir
                current_val = parse_price(row[col])
                
                if current_val is not None:
                    if current_val == ref_val:
                        # Tam eşitse YEŞİL
                        styles[col_idx] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
                    else:
                        # Düşük veya Yüksekse KIRMIZI
                        styles[col_idx] = 'background-color: #f8d7da; color: #721c24;'
    
    return styles

# ================= ARAYÜZ =================
st.title("⚖️ Braun Shop Bazlı Fiyat Analizi")
st.info("💡 Braun Shop fiyatına eşit olanlar **Yeşil**, düşük veya yüksek olanlar **Kırmızı** görünür.")

df = load_data()

if df is not None:
    search = st.text_input("🔍 Listede Ara (Ürün Adı, Barkod...):")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # Renkleri Uygula
    styled_df = df.style.apply(apply_comparative_style, axis=1)

    # Tablo Gösterimi
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    
    now = datetime.now().strftime("%d.%m.%Y_%H-%M")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    st.download_button(
        label=f"📥 Verileri Excel Olarak İndir ({now})",
        data=output.getvalue(),
        file_name=f"Fiyat_Analiz_Raporu_{now}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.error("Google Sheets bağlantısı kurulamadı!")
