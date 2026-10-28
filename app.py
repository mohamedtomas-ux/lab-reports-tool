import fitz
import streamlit as st
from io import BytesIO
import zipfile

# إعدادات ثابتة ومضمونة
OLD_HEADER_HEIGHT = 100  # ارتفاع الهيدر القديم
OLD_FOOTER_HEIGHT = 150  # ارتفاع الفوتر القديم + QR Code + التوقيع
NEW_HEADER_HEIGHT = 100  # ارتفاع الهيدر الجديد
NEW_FOOTER_HEIGHT = 130  # ارتفاع الفوتر الجديد

def process_pdf(input_pdf_bytes, template_pdf_bytes):
    """معالجة ملف PDF"""
    doc = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    template_doc = fitz.open(stream=template_pdf_bytes, filetype="pdf")
    template_page = template_doc[0]
    template_rect = template_page.rect
    template_width = template_rect.width
    template_height = template_rect.height
    
    for page in doc:
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        # 1. مسح الهيدر القديم (بيانات المعمل)
        header_rect = fitz.Rect(0, 0, page_width, OLD_HEADER_HEIGHT)
        page.add_redact_annot(header_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # 2. مسح الفوتر القديم + QR Code + التوقيع
        footer_rect = fitz.Rect(0, page_height - OLD_FOOTER_HEIGHT, page_width, page_height)
        page.add_redact_annot(footer_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # 3. إضافة الهيدر الجديد من ملف القالب
        new_header_rect = fitz.Rect(0, 0, page_width, NEW_HEADER_HEIGHT)
        header_clip = fitz.Rect(0, 0, template_width, NEW_HEADER_HEIGHT)
        page.show_pdf_page(new_header_rect, template_doc, 0, clip=header_clip)
        
        # 4. إضافة الفوتر الجديد من ملف القالب
        new_footer_rect = fitz.Rect(0, page_height - NEW_FOOTER_HEIGHT, page_width, page_height)
        footer_clip = fitz.Rect(0, template_height - NEW_FOOTER_HEIGHT, template_width, template_height)
        page.show_pdf_page(new_footer_rect, template_doc, 0, clip=footer_clip)
    
    output_bytes = BytesIO()
    doc.save(output_bytes, deflate=True, garbage=4)
    output_bytes.seek(0)
    
    doc.close()
    template_doc.close()
    
    return output_bytes.getvalue()

def main():
    st.set_page_config(page_title="أداة تعديل هيدر نتائج المعمل", layout="wide")
    
    st.title("🏥 أداة تعديل هيدر نتائج المعمل")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 رفع ملفات النتائج")
        uploaded_files = st.file_uploader(
            "اختر ملفات PDF للنتائج المعملية",
            type="pdf",
            accept_multiple_files=True
        )
    
    with col2:
        st.subheader("📄 رفع ملف الهيدر الجديد")
        template_file = st.file_uploader(
            "اختر ملف PDF للهيدر الجديد",
            type="pdf"
        )
    
    st.markdown("---")
    
    if st.button("🚀 بدء المعالجة", type="primary", use_container_width=True):
        if not uploaded_files:
            st.error("❌ يرجى رفع ملفات النتائج أولاً")
            return
        
        if not template_file:
            st.error("❌ يرجى رفع ملف الهيدر الجديد")
            return
        
        template_bytes = template_file.read()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_files = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"جاري معالجة: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            
            input_bytes = uploaded_file.read()
            
            try:
                output_bytes = process_pdf(input_bytes, template_bytes)
                processed_files.append({
                    'name': uploaded_file.name,
                    'data': output_bytes
                })
            except Exception as e:
                st.error(f"خطأ في معالجة {uploaded_file.name}: {str(e)}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.text("✅ اكتملت المعالجة!")
        
        st.markdown("---")
        st.subheader(f"📦 الملفات المعالجة ({len(processed_files)} ملف)")
        
        if len(processed_files) == 1:
            st.download_button(
                label="📥 تحميل الملف المعدل",
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
                label="📥 تحميل جميع الملفات (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="processed_reports.zip",
                mime="application/zip",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
