import base64
import html
import os
import zipfile
from datetime import datetime
from io import BytesIO

import fitz  # PyMuPDF
import streamlit as st

# ---------------- الإعدادات ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_HEADER_HEIGHT = 100
NEW_HEADER_HEIGHT = 100
NEW_FOOTER_HEIGHT = 130
TEMPLATE_FILE = os.path.join(BASE_DIR, "template.pdf")
LOGO_FILE = os.path.join(BASE_DIR, "logo.png")

# عرض اللوجو الأقصى بالبكسل
LOGO_MAX_WIDTH = 320

# الجملة اللي بتتضاف قبل اسم الملف الأصلي
FILENAME_PREFIX = "فحص شامل - "

CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    html, body, .stApp, [class*="css"] {{ font-family: 'Cairo', sans-serif; }}
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] {{ display: none; }}
    .stApp {{ background: #ffffff; direction: rtl; }}
    footer, #MainMenu {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none !important; }}

    .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 900px !important;
    }}

    /* ---------- اللوجو ---------- */
    .logo-wrap {{
        display: flex; justify-content: center; align-items: center;
        margin: 6px 0 10px 0; overflow: visible;
    }}
    .logo-wrap img {{
        width: auto; height: auto;
        max-width: min(100%, {LOGO_MAX_WIDTH}px);
        object-fit: contain; display: block;
    }}

    /* ---------- العناوين ---------- */
    .main-title {{ text-align: center; margin: 5px 0 15px 0; }}
    .main-title h1 {{ margin: 5px 0 2px 0 !important; font-size: 1.6em !important; font-weight: 700; color: #000; }}
    .main-title p  {{ margin: 0 !important; font-size: 0.9em !important; color: #555; }}

    /* ---------- الإحصائيات ---------- */
    .stats-bar {{ display: flex; justify-content: center; gap: 12px; margin: 10px 0 15px 0; flex-wrap: wrap; }}
    .stat-badge {{
        background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 20px;
        padding: 6px 18px; font-size: 0.9em; color: #333;
        display: flex; align-items: center; gap: 6px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .stat-badge .number {{ font-weight: 700; color: #8B1A1A; font-size: 1.1em; }}
    .stat-badge.success {{ background: #e8f5e9; border-color: #c8e6c9; }}
    .stat-badge.success .number {{ color: #2e7d32; }}
    .stat-badge.fail {{ background: #fdecea; border-color: #f5c6c2; }}
    .stat-badge.fail .number {{ color: #c62828; }}

    /* ---------- رفع الملفات ---------- */
    .stFileUploader {{
        background: #fafafa; border: 2px dashed #8B1A1A;
        border-radius: 10px; padding: 15px !important; margin: 10px 0 !important;
    }}
    /* تعريب نصوص الـ uploader */
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span,
    [data-testid="stFileUploaderDropzoneInstructions"] > div > small {{ display: none !important; }}
    [data-testid="stFileUploaderDropzoneInstructions"] > div::before {{
        content: "اسحب ملفات PDF هنا أو اضغط على زر الاختيار";
        font-weight: 600; color: #333; font-size: 1em;
    }}
    [data-testid="stFileUploaderDropzone"] button {{ font-size: 0 !important; }}
    [data-testid="stFileUploaderDropzone"] button * {{ font-size: 0 !important; }}
    [data-testid="stFileUploaderDropzone"] button::after {{
        content: "اختيار الملفات"; font-size: 1rem !important; font-weight: 600;
    }}
    [data-testid="stFileUploaderFile"] {{ direction: ltr; }}

    /* ---------- زر المعالجة (أحمر) ---------- */
    .stButton > button {{
        background: #8B1A1A !important; color: #fff !important; border: none !important;
        padding: 12px 40px !important; border-radius: 8px !important;
        font-weight: 700 !important; font-size: 1.1em !important;
        transition: all .3s ease !important;
        box-shadow: 0 3px 8px rgba(139,26,26,.3) !important;
    }}
    .stButton > button:hover {{ background: #A52A2A !important; transform: translateY(-2px) !important; }}
    .stButton > button:disabled {{ background: #c9a0a0 !important; box-shadow: none !important; }}

    /* ---------- زر التحميل (أخضر صلب) ---------- */
    [data-testid="stDownloadButton"] button,
    .st-key-download_button button {{
        background: #2e7d32 !important; background-color: #2e7d32 !important;
        color: #ffffff !important; border: none !important;
        padding: 12px 40px !important; border-radius: 8px !important;
        font-weight: 700 !important; font-size: 1.1em !important;
        opacity: 1 !important; transition: all .3s ease !important;
        box-shadow: 0 3px 8px rgba(46,125,50,.3) !important;
    }}
    [data-testid="stDownloadButton"] button p,
    [data-testid="stDownloadButton"] button span,
    .st-key-download_button button p {{ color: #ffffff !important; }}
    [data-testid="stDownloadButton"] button:hover,
    .st-key-download_button button:hover {{
        background: #388e3c !important; background-color: #388e3c !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 12px rgba(46,125,50,.4) !important;
    }}

    /* ---------- زر بدء جديد (رمادي) ---------- */
    .st-key-reset_button button {{
        background: #ffffff !important; background-color: #ffffff !important;
        color: #555555 !important; border: 1.5px solid #bdbdbd !important;
        box-shadow: none !important; padding: 8px 24px !important;
        font-size: 1em !important;
    }}
    .st-key-reset_button button p {{ color: #555555 !important; }}
    .st-key-reset_button button:hover {{
        background: #f3f3f3 !important; background-color: #f3f3f3 !important;
        border-color: #8B1A1A !important; transform: none !important;
    }}

    /* ---------- جدول الملخص ---------- */
    .report-wrap {{ overflow-x: auto; margin: 10px 0 18px 0; }}
    .report-table {{
        width: 100%; border-collapse: collapse; direction: rtl;
        font-size: 0.9em; border: 1px solid #e0e0e0; border-radius: 8px;
    }}
    .report-table th {{
        background: #8B1A1A; color: #fff; padding: 8px 10px;
        text-align: right; font-weight: 700;
    }}
    .report-table td {{
        padding: 8px 10px; border-bottom: 1px solid #eee;
        text-align: right; color: #333; word-break: break-word;
    }}
    .report-table tr:nth-child(even) td {{ background: #fafafa; }}
    .report-table td.ok {{ color: #2e7d32; font-weight: 700; white-space: nowrap; }}
    .report-table td.err {{ color: #c62828; font-weight: 700; white-space: nowrap; }}
</style>
"""


# ---------------- دوال مساعدة ----------------
def image_to_base64(path):
    ext = os.path.splitext(path)[1].lower().replace(".", "")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    with open(path, "rb") as f:
        return mime, base64.b64encode(f.read()).decode()


def output_name(original_name):
    """فحص شامل - اسم الملف الأصلي"""
    return f"{FILENAME_PREFIX}{original_name}"


def detect_and_remove_qr_code(page):
    try:
        for img in page.get_images(full=True):
            for rect in page.get_image_rects(img[0]):
                if rect.y0 > page.rect.height * 0.75:
                    w, h = rect.width, rect.height
                    if h > 0 and 0.7 < w / h < 1.3 and w < 120 and h < 120:
                        m = 10
                        qr_rect = fitz.Rect(
                            max(0, rect.x0 - m), max(0, rect.y0 - m),
                            min(page.rect.width, rect.x1 + m),
                            min(page.rect.height, rect.y1 + m),
                        )
                        page.add_redact_annot(qr_rect, fill=(1, 1, 1))
        page.apply_redactions()
    except Exception as e:
        print(f"خطأ في اكتشاف QR Code: {e}")


def process_pdf(input_pdf_bytes, template_path):
    doc = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    template_doc = fitz.open(template_path)
    try:
        t_rect = template_doc[0].rect
        t_w, t_h = t_rect.width, t_rect.height

        for page in doc:
            pw, ph = page.rect.width, page.rect.height

            page.add_redact_annot(fitz.Rect(0, 0, pw, OLD_HEADER_HEIGHT), fill=(1, 1, 1))
            page.apply_redactions()
            detect_and_remove_qr_code(page)

            page.show_pdf_page(
                fitz.Rect(0, 0, pw, NEW_HEADER_HEIGHT), template_doc, 0,
                clip=fitz.Rect(0, 0, t_w, NEW_HEADER_HEIGHT),
            )
            page.show_pdf_page(
                fitz.Rect(0, ph - NEW_FOOTER_HEIGHT, pw, ph), template_doc, 0,
                clip=fitz.Rect(0, t_h - NEW_FOOTER_HEIGHT, t_w, t_h),
            )

        return doc.tobytes(deflate=True, garbage=4)
    finally:
        doc.close()
        template_doc.close()


def build_download(processed):
    """processed: قائمة فيها name (الاسم الناتج) و data"""
    if len(processed) == 1:
        return processed[0]["name"], processed[0]["data"], "application/pdf"

    buf = BytesIO()
    used = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in processed:
            name, n = f["name"], 1
            while name in used:  # منع تكرار الأسماء داخل الـ ZIP
                base, ext = os.path.splitext(f["name"])
                name = f"{base}_{n}{ext}"
                n += 1
            used.add(name)
            z.writestr(name, f["data"])
    fname = f"reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return fname, buf.getvalue(), "application/zip"


def render_report(report):
    """جدول ملخص بالملفات الناجحة والفاشلة"""
    ok_count = sum(1 for r in report if r["ok"])
    fail_count = len(report) - ok_count

    st.markdown(
        f"""
        <div class="stats-bar">
            <div class="stat-badge success"><span>✅ نجحت:</span><span class="number">{ok_count}</span></div>
            <div class="stat-badge fail"><span>❌ فشلت:</span><span class="number">{fail_count}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rows = ""
    for i, r in enumerate(report, 1):
        status = '<td class="ok">✅ تمت</td>' if r["ok"] else '<td class="err">❌ فشلت</td>'
        rows += (
            f"<tr><td>{i}</td><td>{html.escape(r['name'])}</td>"
            f"{status}<td>{html.escape(r['note'])}</td></tr>"
        )

    st.markdown(
        f"""
        <div class="report-wrap">
        <table class="report-table">
            <thead><tr><th>#</th><th>الملف الأصلي</th><th>الحالة</th><th>التفاصيل</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def reset_all():
    """بدء جديد: مسح النتائج وتفريغ الـ uploader"""
    st.session_state.pop("result", None)
    st.session_state["uploader_key"] = st.session_state.get("uploader_key", 0) + 1


# ---------------- الواجهة ----------------
def main():
    st.set_page_config(
        page_title="برنامج الفحص الشامل",
        page_icon="🧪",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    if not os.path.exists(TEMPLATE_FILE):
        st.error("❌ ملف الهيدر الثابت (template.pdf) غير موجود!")
        return

    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    # اللوجو
    if os.path.exists(LOGO_FILE):
        mime, b64 = image_to_base64(LOGO_FILE)
        st.markdown(
            f'<div class="logo-wrap"><img src="data:image/{mime};base64,{b64}" alt="Logo"></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="main-title">
            <h1>برنامج الفحص الشامل - طباعة النتائج المعملية</h1>
            <p>أداة احترافية وسريعة لتعديل هيدر وفوتر ملفات نتائج التحاليل المعملية</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="text-align:center;margin-bottom:5px;"><strong style="color:#333;font-size:1.1em;">'
        '📁 رفع ملفات النتائج</strong><br><small style="color:#666;">يمكن اختيار أكثر من ملف</small></div>',
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "رفع الملفات", type="pdf", accept_multiple_files=True,
        label_visibility="collapsed",
        key=f"uploader_{st.session_state['uploader_key']}",
    )

    if uploaded_files:
        total_size = sum(f.size for f in uploaded_files) / (1024 * 1024)
        st.markdown(
            f"""
            <div class="stats-bar">
                <div class="stat-badge"><span>📄 الملفات:</span><span class="number">{len(uploaded_files)}</span></div>
                <div class="stat-badge"><span>💾 الحجم:</span><span class="number">{total_size:.2f} MB</span></div>
                <div class="stat-badge success"><span>✅ الحالة:</span><span class="number">جاهز</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    _, col_btn, _ = st.columns([1, 2, 1])
    with col_btn:
        start_button = st.button(
            "بدء المعالجة", use_container_width=True, disabled=not uploaded_files
        )

    if start_button and uploaded_files:
        progress_bar = st.progress(0)
        status_text = st.empty()
        processed, report = [], []

        for i, f in enumerate(uploaded_files):
            status_text.text(f"⚙️ معالجة: {f.name} ({i + 1}/{len(uploaded_files)})")
            try:
                data = process_pdf(f.getvalue(), TEMPLATE_FILE)
                processed.append({"name": output_name(f.name), "data": data})
                report.append({
                    "name": f.name, "ok": True,
                    "note": f"{len(data) / 1024:.0f} KB",
                })
            except Exception as e:
                report.append({
                    "name": f.name, "ok": False,
                    "note": str(e)[:120] or "خطأ غير معروف",
                })
            progress_bar.progress((i + 1) / len(uploaded_files))

        status_text.empty()
        progress_bar.empty()

        download = None
        if processed:
            fname, data, mime = build_download(processed)
            download = {"name": fname, "data": data, "mime": mime}

        st.session_state["result"] = {"report": report, "download": download}

    # النتيجة خارج الـ if عشان تفضل ظاهرة بعد أي rerun
    result = st.session_state.get("result")
    if result:
        render_report(result["report"])

        if result["download"]:
            _, col_dl, _ = st.columns([1, 2, 1])
            with col_dl:
                st.download_button(
                    label="⬇️ التحميل",
                    data=result["download"]["data"],
                    file_name=result["download"]["name"],
                    mime=result["download"]["mime"],
                    use_container_width=True,
                    key="download_button",
                )

        _, col_rs, _ = st.columns([1, 2, 1])
        with col_rs:
            st.button(
                "🔄 بدء جديد", use_container_width=True,
                on_click=reset_all, key="reset_button",
            )


if __name__ == "__main__":
    main()
