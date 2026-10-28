import fitz
import streamlit as st
from io import BytesIO
import zipfile
import os
from datetime import datetime

# ==========================================
# إعدادات التطبيق
# ==========================================
OLD_HEADER_HEIGHT = 100
NEW_HEADER_HEIGHT = 100
NEW_FOOTER_HEIGHT = 130
TEMPLATE_FILE = "template.pdf"
LOGO_FILE = "logo.png"

# ==========================================
# إعدادات التصميم المخصص (CSS)
# ==========================================
st.markdown("""
<style>
    /* إخفاء الشريط الجانبي */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    [data-testid="stSidebarNav"] {
        display: none;
    }
    
    /* الخلفية العامة - بيضاء نظيفة */
    .stApp {
        background: #ffffff;
    }
    
    /* العنوان الرئيسي - بدون خلفية زرقاء */
    .main-title {
        text-align: center;
        padding: 30px 20px;
        margin-bottom: 30px;
    }
    
    .main-title h1 {
        margin: 20px 0 10px 0;
        font-size: 2.5em;
        font-weight: bold;
        color: #000000;
    }
    
    .main-title p {
        margin: 10px 0 0 0;
        font-size: 1.1em;
        color: #000000;
    }
    
    /* حاوية اللوجو في النص */
    .logo-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 20px;
    }
    
    .logo-wrapper img {
        max-height: 180px;
        width: auto;
    }
    
    /* بوكس رفع الملفات الموحد */
    .upload-box {
        background: #f8f9fa;
        padding: 30px;
        border-radius: 15px;
        border: 2px dashed #8B1A1A;
        margin-bottom: 30px;
        text-align: right;
        direction: rtl;
    }
    
    .upload-box h2 {
        color: #000000;
        margin-top: 0;
        margin-bottom: 10px;
        font-size: 1.8em;
        font-weight: bold;
    }
    
    .upload-box .small-hint {
        color: #666;
        font-size: 0.9em;
        margin-top: 0;
        margin-bottom: 20px;
        font-style: italic;
    }
    
    /* إخفاء المسافة بين العنوان والـ uploader */
    .upload-box + div[data-testid="stFileUploader"] {
        margin-top: -20px !important;
    }
    
    /* بطاقات الإحصائيات */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stat-card.success {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        box-shadow: 0 5px 15px rgba(17, 153, 142, 0.4);
    }
    
    .stat-card h2 {
        margin: 0;
        font-size: 2.5em;
        font-weight: bold;
    }
    
    .stat-card p {
        margin: 5px 0 0 0;
        font-size: 1.1em;
        opacity: 0.95;
    }
    
    /* شريط التقدم */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #8B1A1A 0%, #C41E3A 100%);
    }
    
    /* الرسائل */
    .success-message {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 1.2em;
        font-weight: bold;
        box-shadow: 0 5px 15px rgba(17, 153, 142, 0.3);
    }
    
    /* قائمة الملفات */
    .file-item {
        background: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border-left: 4px solid #38ef7d;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    /* إخفاء "Made with Streamlit" */
    footer {
        visibility: hidden;
    }
    
    /* تحسين الأزرار - أحمر وصغير وفي النص */
    .stButton > button {
        background: #8B1A1A !important;
        color: white !important;
        border: none !important;
        padding: 20px 60px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 1.8em !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 5px 15px rgba(139, 26, 26, 0.3) !important;
        width: auto !important;
        min-width: 350px !important;
    }
    
    .stButton > button:hover {
        background: #A52A2A !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(139, 26, 26, 0.4) !important;
    }
    
    /* تحسين الـ uploader */
    .stFileUploader {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    
    /* زر التحميل */
    .download-btn {
        background: #8B1A1A !important;
        color: white !important;
    }
    
    /* توسيط الأزرار */
    .center-button {
        display: flex;
        justify-content: center;
        margin: 30px 0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# دوال المعالجة
# ==========================================
def detect_and_remove_qr_code(page):
    """اكتشاف وإزالة QR Code فقط"""
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
    """معالجة ملف PDF"""
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
        
        # مسح الهيدر القديم
        header_rect = fitz.Rect(0, 0, page_width, OLD_HEADER_HEIGHT)
        page.add_redact_annot(header_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # اكتشاف وإزالة QR Code
        detect_and_remove_qr_code(page)
        
        # إضافة الهيدر الجديد
        new_header_rect = fitz.Rect(0, 0, page_width, NEW_HEADER_HEIGHT)
        header_clip = fitz.Rect(0, 0, template_width, NEW_HEADER_HEIGHT)
        page.show_pdf_page(new_header_rect, template_doc, 0, clip=header_clip)
        
        # إضافة الفوتر الجديد
        new_footer_rect = fitz.Rect(0, page_height - NEW_FOOTER_HEIGHT, page_width, page_height)
        footer_clip = fitz.Rect(0, template_height - NEW_FOOTER_HEIGHT, template_width, template_height)
        page.show_pdf_page(new_footer_rect, template_doc, 0, clip=footer_clip)
    
    output_bytes = BytesIO()
    doc.save(output_bytes, deflate=True, garbage=4)
    output_bytes.seek(0)
    
    doc.close()
    template_doc.close()
    
    return output_bytes.getvalue()

# ==========================================
# الواجهة الرئيسية
# ==========================================
def main():
    # إعداد الصفحة
    st.set_page_config(
        page_title="برنامج الفحص الشامل - طباعة النتائج المعملية",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # ==========================================
    # التحقق من وجود اللوجو وملف القالب
    # ==========================================
    logo_exists = os.path.exists(LOGO_FILE)
    template_exists = os.path.exists(TEMPLATE_FILE)
    
    if not template_exists:
        st.error("❌ ملف الهيدر الثابت غير موجود!")
        st.info(f"يرجى رفع ملف `{TEMPLATE_FILE}` إلى GitHub Repository")
        return
    
    # ==========================================
    # العنوان الرئيسي مع اللوجو في النص
    # ==========================================
    
    # عرض اللوجو في النص باستخدام HTML
    if logo_exists:
        st.markdown(f"""
        <div class="logo-wrapper">
            <img src="{LOGO_FILE}" alt="Dr. Osman Hospital Logo" />
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ اللوجو غير متوفر - يرجى رفع ملف logo.png")
    
    # العنوان والوصف
    st.markdown("""
    <div class="main-title">
        <h1>برنامج الفحص الشامل - طباعة النتائج المعملية</h1>
        <p>أداة احترافية وسريعة لتعديل هيدر وفوتر ملفات نتائج التحاليل المعملية</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ==========================================
    # بوكس رفع الملفات الموحد (العنوان + uploader)
    # ==========================================
    st.markdown("""
    <div class="upload-box">
        <h2>📁 رفع ملفات النتائج</h2>
        <p class="small-hint">يمكن اختيار أكثر من ملف</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "",
        type="pdf",
        accept_multiple_files=True,
        help="يمكنك رفع عدد غير محدود من الملفات",
        label_visibility="collapsed"
    )
    
    # ==========================================
    # عرض إحصائيات الملفات المرفوعة
    # ==========================================
    if uploaded_files:
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <h2>{len(uploaded_files)}</h2>
                <p>ملفات مرفوعة</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_size = sum(f.size for f in uploaded_files) / (1024 * 1024)
            st.markdown(f"""
            <div class="stat-card">
                <h2>{total_size:.1f}</h2>
                <p>ميغابايت</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card success">
                <h2>✓</h2>
                <p>جاهز للمعالجة</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
    
    # ==========================================
    # زر المعالجة - أحمر وصغير
    # ==========================================
    col_center, _, _ = st.columns([1, 2, 1])
    
    with col_center:
        if st.button(" بدء المعالجة", type="primary"):
            if not uploaded_files:
                st.error("❌ يرجى رفع ملفات النتائج أولاً")
                return
            
            # بدء المعالجة
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            processed_files = []
            start_time = datetime.now()
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.markdown(f"""
                <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-right: 4px solid #8B1A1A; text-align: right; direction: rtl;">
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
            
            # حساب الوقت المستغرق
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # ==========================================
            # عرض النتائج
            # ==========================================
            status_text.empty()
            progress_bar.empty()
            
            st.markdown("""
            <div class="success-message">
                ✅ اكتملت المعالجة بنجاح!
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # إحصائيات المعالجة
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="stat-card success">
                    <h2>{len(processed_files)}</h2>
                    <p>ملفات تمت معالجتها</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <h2>{duration:.1f}</h2>
                    <p>ثانية</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                avg_time = duration / len(processed_files) if processed_files else 0
                st.markdown(f"""
                <div class="stat-card">
                    <h2>{avg_time:.2f}</h2>
                    <p>ثانية/ملف</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ==========================================
            # أزرار التحميل
            # ==========================================
            st.markdown("""
            <div style="background: #f8f9fa; padding: 25px; border-radius: 15px; margin-bottom: 20px; text-align: right; direction: rtl;">
                <h2 style="color: #000000; margin-top: 0;">📥 تحميل الملفات</h2>
            </div>
            """, unsafe_allow_html=True)
            
            if len(processed_files) == 1:
                # ملف واحد
                st.download_button(
                    label=f"📥 تحميل {processed_files[0]['name']}",
                    data=processed_files[0]['data'],
                    file_name=processed_files[0]['name'],
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                # ملفات متعددة - ZIP
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for file_info in processed_files:
                            zip_file.writestr(file_info['name'], file_info['data'])
                    
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label=f" تحميل جميع الملفات ({len(processed_files)} ملف)",
                        data=zip_buffer.getvalue(),
                        file_name=f"processed_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                
                with col2:
                    st.markdown(f"""
                    <div style="background: #f0f4f8; padding: 15px; border-radius: 10px; text-align: center;">
                        <strong style="color: #8B1A1A;">💾 الحجم الكلي</strong><br>
                        <span style="font-size: 1.5em; color: #38ef7d;">{sum(f['size'] for f in processed_files) / 1024:.1f} MB</span>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ==========================================
            # قائمة الملفات المعالجة
            # ==========================================
            st.markdown("### 📋 الملفات المعالجة")
            
            for idx, file_info in enumerate(processed_files, 1):
                st.markdown(f"""
                <div class="file-item">
                    <div>
                        <strong style="color: #000000;">{idx}. {file_info['name']}</strong><br>
                        <small style="color: #666;">الحجم: {file_info['size']:.1f} KB</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
