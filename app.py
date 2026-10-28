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

# ==========================================
# إعدادات التصميم المخصص (CSS)
# ==========================================
st.markdown("""
<style>
    /* الخلفية العامة */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8edf3 100%);
    }
    
    /* العنوان الرئيسي */
    .main-title {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(30, 60, 114, 0.3);
        margin-bottom: 30px;
    }
    
    .main-title h1 {
        margin: 0;
        font-size: 2.5em;
        font-weight: bold;
    }
    
    .main-title p {
        margin: 10px 0 0 0;
        font-size: 1.2em;
        opacity: 0.9;
    }
    
    /* البطاقات */
    .feature-card {
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        border-left: 5px solid #2a5298;
        transition: all 0.3s ease;
        height: 100%;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    .feature-card h3 {
        color: #1e3c72;
        margin-top: 0;
        font-size: 1.3em;
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
    
    /* أزرار التحميل */
    .download-btn {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 15px 30px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 1.1em;
        border: none;
        cursor: pointer;
        box-shadow: 0 5px 15px rgba(17, 153, 142, 0.4);
        transition: all 0.3s ease;
    }
    
    /* قسم الإعدادات */
    .settings-section {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        margin-bottom: 20px;
    }
    
    /* شريط التقدم */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
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
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* إخفاء "Made with Streamlit" */
    footer {
        visibility: hidden;
    }
    
    /* تحسين الأزرار */
    .stButton > button {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 10px;
        font-weight: bold;
        font-size: 1em;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(30, 60, 114, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(30, 60, 114, 0.4);
    }
    
    /* تحسين الـ uploader */
    .stFileUploader {
        background: white;
        padding: 20px;
        border-radius: 15px;
        border: 2px dashed #2a5298;
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
        page_title="أداة تعديل هيدر نتائج المعمل",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # ==========================================
    # الشريط الجانبي
    # ==========================================
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="color: white; margin: 0;">🏥</h1>
            <h2 style="color: white; margin: 10px 0;">Lab Reports Tool</h2>
            <p style="color: rgba(255,255,255,0.8); font-size: 0.9em;">أداة احترافية لتعديل هيدر وفوتر نتائج المعمل</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # معلومات التطبيق
        st.markdown("### 📋 عن التطبيق")
        st.markdown("""
        <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
        <p style="color: white; margin: 0; font-size: 0.9em;">
        ✅ تعديل الهيدر والفوتر تلقائياً<br>
        ✅ إزالة QR Code ذكياً<br>
        ✅ الحفاظ على بيانات المريض<br>
        ✅ معالجة عدد غير محدود من الملفات
        </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # معلومات الاتصال
        st.markdown("### 📞 الدعم الفني")
        st.markdown("""
        <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
        <p style="color: white; margin: 0; font-size: 0.9em;">
        📧 support@lab.com<br>
        📱 +20 123 456 7890<br>
        🕐 24/7 متاح
        </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # الإصدار
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; color: rgba(255,255,255,0.6); font-size: 0.8em;">
        الإصدار 2.0 | {datetime.now().strftime('%Y')}
        </div>
        """, unsafe_allow_html=True)
    
    # ==========================================
    # العنوان الرئيسي
    # ==========================================
    st.markdown("""
    <div class="main-title">
        <h1>🏥 أداة تعديل هيدر نتائج المعمل</h1>
        <p>أداة احترافية وسريعة لتعديل هيدر وفوتر ملفات نتائج التحاليل المعملية</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ==========================================
    # التحقق من ملف القالب
    # ==========================================
    if not os.path.exists(TEMPLATE_FILE):
        st.error("❌ ملف الهيدر الثابت غير موجود!")
        st.info(f"يرجى رفع ملف `{TEMPLATE_FILE}` إلى GitHub Repository")
        return
    
    # ==========================================
    # بطاقات المميزات
    # ==========================================
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>⚡ سريع</h3>
            <p style="color: #666; margin: 0;">معالجة فورية للملفات</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>🎯 دقيق</h3>
            <p style="color: #666; margin: 0;">إزالة ذكية لـ QR Code</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>🔒 آمن</h3>
            <p style="color: #666; margin: 0;">حماية بيانات المريض</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="feature-card">
            <h3>📦 شامل</h3>
            <p style="color: #666; margin: 0;">معالجة غير محدودة</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ==========================================
    # منطقة رفع الملفات
    # ==========================================
    st.markdown("""
    <div style="background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.08); margin-bottom: 20px;">
        <h2 style="color: #1e3c72; margin-top: 0;">📁 رفع ملفات النتائج</h2>
        <p style="color: #666; margin: 10px 0 20px 0;">اختر ملفات PDF للنتائج المعملية التي تريد تعديلها</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "",
        type="pdf",
        accept_multiple_files=True,
        help="يمكنك رفع عدد غير محدود من الملفات"
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
    # زر المعالجة
    # ==========================================
    if st.button("🚀 بدء المعالجة", use_container_width=True, type="primary"):
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
            <div style="background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #2a5298;">
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
        <div style="background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.08); margin-bottom: 20px;">
            <h2 style="color: #1e3c72; margin-top: 0;">📥 تحميل الملفات</h2>
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
                    label=f"📦 تحميل جميع الملفات ({len(processed_files)} ملف)",
                    data=zip_buffer.getvalue(),
                    file_name=f"processed_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            
            with col2:
                st.markdown(f"""
                <div style="background: #f0f4f8; padding: 15px; border-radius: 10px; text-align: center;">
                    <strong style="color: #1e3c72;">💾 الحجم الكلي</strong><br>
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
                    <strong style="color: #1e3c72;">{idx}. {file_info['name']}</strong><br>
                    <small style="color: #666;">الحجم: {file_info['size']:.1f} KB</small>
                </div>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
