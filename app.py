تمام! هقلل المسافات الفارغة عشان الواجهة تظهر كاملة على الشاشة. حدّث ملف `app.py` بالكود ده:

```python
import fitz
import streamlit as st
from io import BytesIO
import zipfile
import os
from datetime import datetime

# إعدادات التطبيق
OLD_HEADER_HEIGHT = 100
NEW_HEADER_HEIGHT = 100
NEW_FOOTER_HEIGHT = 130
TEMPLATE_FILE = "template.pdf"
LOGO_FILE = "logo.png"

# CSS للتصميم - مسافات مضغوطة
st.markdown("""
<style>
    /* إخفاء الشريط الجانبي */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarNav"] { display: none; }
    
    /* الخلفية بيضاء */
    .stApp { background: #ffffff; }
    
    /* تقليل المسافات العامة */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* العنوان */
    .main-title {
        text-align: center;
        padding: 10px 0;
        margin-bottom: 10px;
    }
    
    .main-title h1 {
        margin: 5px 0;
        font-size: 2em;
        font-weight: bold;
        color: #000000;
    }
    
    .main-title p {
        margin: 5px 0;
        font-size: 1em;
        color: #000000;
    }
    
    /* بوكس رفع الملفات */
    .upload-box {
        background: #f8f9fa;
        padding: 15px 20px;
        border-radius: 10px;
        border: 2px dashed #8B1A1A;
        margin: 10px auto;
        max-width: 800px;
        text-align: right;
        direction: rtl;
    }
    
    .upload-box h2 {
        color: #000000;
        margin: 0 0 5px 0;
        font-size: 1.4em;
        font-weight: bold;
    }
    
    .small-hint {
        color: #666;
        font-size: 0.85em;
        margin: 0;
        font-style: italic;
    }
    
    /* زر المعالجة */
    .stButton > button {
        background: #8B1A1A !important;
        color: white !important;
        border: none !important;
        padding: 12px 40px !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        font-size: 1.3em !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 3px 10px rgba(139, 26, 26, 0.3) !important;
    }
    
    .stButton > button:hover {
        background: #A52A2A !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(139, 26, 26, 0.4) !important;
    }
    
    /* إخفاء footer */
    footer { visibility: hidden; }
    
    /* uploader */
    .stFileUploader {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* تقليل المسافات بين العناصر */
    .stMarkdown {
        margin-bottom: 0.5rem !important;
    }
    
    /* تقليل حجم الإحصائيات */
    .stat-card {
        padding: 10px;
    }
    
    .stat-card h2 {
        font-size: 1.8em;
    }
</style>
""", unsafe_allow_html=True)

# دوال المعالجة
def detect_and_remove_qr_code(page):
    try:
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            img_rects = page.get_image_rects(xref)
            for rect in img_rects:
                if rect.y0 > page.rect.height * 0.75:
                    width = rect.width
                    height = rect.height
                    if 0.7 < width/height < 1.3 and width < 120 and height < 120:
                        margin = 10
                        qr_rect = fitz.Rect(
                            max(0, rect.x0 - margin),
                            max(0, rect.y0 - margin),
                            min(page.rect.width, rect.x1 + margin),
                            min(page.rect.height, rect.y1 + margin)
                        )
                        page.add_redact_annot(qr_rect, fill=(1, 1, 1))
        page.apply_redactions()
    except Exception as e:
        print(f"خطأ في اكتشاف QR Code: {e}")

def process_pdf(input_pdf_bytes, template_path):
    doc = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    template_doc = fitz.open(template_path)
    template_page = template_doc[0]
    template_rect = template_page.rect
    template_width = template_rect.width
    template_height = template_rect.height
    
    for page in doc:
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        header_rect = fitz.Rect(0, 0, page_width, OLD_HEADER_HEIGHT)
        page.add_redact_annot(header_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        detect_and_remove_qr_code(page)
        
        new_header_rect = fitz.Rect(0, 0, page_width, NEW_HEADER_HEIGHT)
        header_clip = fitz.Rect(0, 0, template_width, NEW_HEADER_HEIGHT)
        page.show_pdf_page(new_header_rect, template_doc, 0, clip=header_clip)
        
        new_footer_rect = fitz.Rect(0, page_height - NEW_FOOTER_HEIGHT, page_width, page_height)
        footer_clip = fitz.Rect(0, template_height - NEW_FOOTER_HEIGHT, template_width, template_height)
        page.show_pdf_page(new_footer_rect, template_doc, 0, clip=footer_clip)
    
    output_bytes = BytesIO()
    doc.save(output_bytes, deflate=True, garbage=4)
    output_bytes.seek(0)
    
    doc.close()
    template_doc.close()
    
    return output_bytes.getvalue()

# الواجهة الرئيسية
def main():
    st.set_page_config(
        page_title="برنامج الفحص الشامل - طباعة النتائج المعملية",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # التحقق من الملفات
    logo_exists = os.path.exists(LOGO_FILE)
    template_exists = os.path.exists(TEMPLATE_FILE)
    
    if not template_exists:
        st.error("❌ ملف الهيدر الثابت غير موجود!")
        st.info(f"يرجى رفع ملف `{TEMPLATE_FILE}` إلى GitHub Repository")
        return
    
    # اللوجو في النص
    if logo_exists:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.image(LOGO_FILE, use_container_width=True)
    else:
        st.warning("⚠️ اللوجو غير متوفر - يرجى رفع ملف logo.png")
    
    # العنوان
    st.markdown("""
    <div class="main-title">
        <h1>برنامج الفحص الشامل - طباعة النتائج المعملية</h1>
        <p>أداة احترافية وسريعة لتعديل هيدر وفوتر ملفات نتائج التحاليل المعملية</p>
    </div>
    """, unsafe_allow_html=True)
    
    # بوكس رفع الملفات
    st.markdown("""
    <div style="text-align: center;">
        <div class="upload-box">
            <h2>📁 رفع ملفات النتائج</h2>
            <p class="small-hint">يمكن اختيار أكثر من ملف</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # uploader
    col_up1, col_up2, col_up3 = st.columns([1, 3, 1])
    with col_up2:
        uploaded_files = st.file_uploader(
            "",
            type="pdf",
            accept_multiple_files=True,
            help="يمكنك رفع عدد غير محدود من الملفات",
            label_visibility="collapsed"
        )
    
    # زر بدء المعالجة
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        start_button = st.button("بدء المعالجة", use_container_width=True)
    
    if start_button:
        if not uploaded_files:
            st.error("❌ يرجى رفع ملفات النتائج أولاً")
            return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_files = []
        start_time = datetime.now()
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.markdown(f"""
            <div style="background: #f8f9fa; padding: 10px; border-radius: 8px; margin-bottom: 5px; border-right: 4px solid #8B1A1A; text-align: right; direction: rtl;">
                <strong>⚙️ جاري معالجة:</strong> {uploaded_file.name}<br>
                <small style="color: #666;">الملف {i+1} من {len(uploaded_files)}</small>
            </div>
            """, unsafe_allow_html=True)
            
            input_bytes = uploaded_file.read()
            
            try:
                output_bytes = process_pdf(input_bytes, TEMPLATE_FILE)
                processed_files.append({
                    'name': uploaded_file.name,
                    'data': output_bytes,
                    'size': len(output_bytes) / 1024
                })
            except Exception as e:
                st.error(f"❌ خطأ في معالجة {uploaded_file.name}: {str(e)}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        status_text.empty()
        progress_bar.empty()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 15px; border-radius: 8px; text-align: center; font-size: 1.1em; font-weight: bold; margin: 10px 0;">
            ✅ اكتملت المعالجة بنجاح!
        </div>
        """, unsafe_allow_html=True)
        
        # تحميل الملفات
        if len(processed_files) == 1:
            st.download_button(
                label=f"📥 تحميل {processed_files[0]['name']}",
                data=processed_files[0]['data'],
                file_name=processed_files[0]['name'],
                mime="application/pdf",
                use_container_width=True
            )
        else:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_info in processed_files:
                    zip_file.writestr(file_info['name'], file_info['data'])
            
            zip_buffer.seek(0)
            
            st.download_button(
                label=f"📦 تحميل جميع الملفات ({len(processed_files)} ملف)",
                data=zip_buffer.getvalue(),
                file_name=f"processed_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
```

## ✅ التعديلات اللي عملتها:

1. **تقليل padding في العنوان الرئيسي** من 30px لـ 10px
2. **تقليل margin بين العناصر** من 20-30px لـ 5-10px
3. **تقليل حجم الخط** في العنوان من 2.5em لـ 2em
4. **تقليل padding في بوكس رفع الملفات** من 30px لـ 15px
5. **تقليل حجم زر المعالجة** من 1.8em لـ 1.3em
6. **تقليل حجم الإحصائيات** بعد المعالجة
7. **تقليل المسافات بين رسائل الحالة** أثناء المعالجة

الواجهة دلوقتي **مضغوطة أكثر** وهتظهر على الشاشة بدون ما تحتاج تمرير كتير.

**حدّث الكود وقولي النتيجة!** 🚀
