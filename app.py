import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ================= AYARLAR =================
st.set_page_config(page_title="Fiyat Karşılaştırma Paneli", page_icon="⚖️", layout="wide")

# Google Sheets ID'nizi buraya yapıştırın
SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0" 
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

# ================= BRAUN SHOP BAZLI RENKLENDİRME MANTIĞI =================
def apply_comparative_style(row):
    """
    Braun Shop fiyatını baz alır:
    - Eşitse: Yeşil
    - Düşükse: Kırmızı
    - Yüksekse: Kırmızı
    """
    # Karşılaştırılacak sütunlar
    target_cols = ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    ref_col = "Braun Shop"
    
    styles = ['' for _ in row.index]
    
    # Referans fiyatı sayıya çevirelim
    ref_val = pd.to_numeric(row[ref_col], errors='coerce') if ref_col in row.index else None
    
    if pd.notnull(ref_val) and ref_val > 0:
        for col in target_cols:
            if col in row.index:
                col_idx = row.index.get_loc(col)
                current_val = pd.to_numeric(row[col], errors='coerce')
                
                if pd.notnull(current_val):
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
    # Arama Kutusu
    search = st.text_input("🔍 Listede Ara (Ürün Adı, Barkod...):")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # Renkleri Uygula
    styled_df = df.style.apply(apply_comparative_style, axis=1)

    # Tablo Gösterimi
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        # Eğer link sütunların varsa buraya ekleyebilirsin:
        column_config={
            "Aksiyon": st.column_config.NumberColumn(format="%.2f TL"),
            "Braun Shop": st.column_config.NumberColumn(format="%.2f TL"),
            "Media Markt": st.column_config.NumberColumn(format="%.2f TL"),
            "Teknosa": st.column_config.NumberColumn(format="%.2f TL"),
            "Vatan": st.column_config.NumberColumn(format="%.2f TL"),
            "Trendyol": st.column_config.NumberColumn(format="%.2f TL"),
            "Hepsiburada": st.column_config.NumberColumn(format="%.2f TL"),
            "Amazon": st.column_config.NumberColumn(format="%.2f TL"),
        }
    )

    st.divider()
    
    # Excel Export (Tarih ve Saatli Dosya Adı)
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
