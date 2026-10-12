"""STOCKWISE PDF preview and Gmail SMTP delivery."""
import re
import smtplib
import ssl
from email.message import EmailMessage
import streamlit as st

_EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}$")

@st.cache_data(show_spinner=False, ttl=3600, max_entries=12)
def _render_pdf_pages(pdf_bytes: bytes, max_pages: int = 20):
    import fitz  # PyMuPDF
    pages = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        count = len(doc)
        for page in list(doc)[:max_pages]:
            pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
            pages.append(pix.tobytes("png"))
    return pages, count


def render_pdf_preview(pdf_bytes: bytes) -> None:
    """Render real PDF pages as PNGs; works without browser PDF iframe support."""
    if not isinstance(pdf_bytes, (bytes, bytearray)) or not pdf_bytes.startswith(b"%PDF"):
        st.error("Báo cáo chưa có định dạng PDF hợp lệ.")
        return
    try:
        with st.spinner("Đang hiển thị các trang báo cáo..."):
            pages, count = _render_pdf_pages(bytes(pdf_bytes))
        if not pages:
            st.warning("Báo cáo PDF chưa có trang nào để xem trước.")
            return
        st.caption(f"Xem trước {len(pages)}/{count} trang PDF thực tế")
        for i, page_png in enumerate(pages, 1):
            st.caption(f"Trang {i}")
            st.image(page_png, width="stretch")
        if count > len(pages):
            st.info("Bản xem trước giới hạn 20 trang; tải PDF để xem toàn bộ.")
    except ImportError:
        st.error("Thiếu thư viện PyMuPDF. Cần thêm PyMuPDF vào requirements.txt rồi deploy lại.")
    except Exception:
        st.error("Không thể render bản xem trước. Hãy dùng nút tải PDF bên dưới.")

def send_pdf_gmail(*, recipient: str, filename: str, pdf_bytes: bytes, symbol: str) -> None:
    recipient = recipient.strip()
    if len(recipient) > 254 or not _EMAIL.fullmatch(recipient):
        raise ValueError("Địa chỉ email không hợp lệ.")
    if not isinstance(pdf_bytes, (bytes, bytearray)) or not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Không tìm thấy báo cáo PDF hợp lệ.")
    if len(pdf_bytes) > 15 * 1024 * 1024:
        raise ValueError("Báo cáo quá lớn để gửi qua Gmail (giới hạn ứng dụng: 15 MB).")
    try:
        cfg = st.secrets["gmail"]
        sender = str(cfg["sender"]).strip()
        password = str(cfg["app_password"]).replace(" ", "").strip()
    except (KeyError, FileNotFoundError, AttributeError):
        raise ValueError("Chưa cấu hình [gmail] sender và app_password trong Streamlit Secrets.")
    if not sender or not password:
        raise ValueError("Thiếu Gmail sender hoặc app_password trong Streamlit Secrets.")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = f"STOCKWISE | Báo cáo phân tích cổ phiếu {symbol}"
    msg.set_content(
        f"Xin chào,\\n\\nĐính kèm là báo cáo STOCKWISE cho mã {symbol}.\\n"
        "Báo cáo mang tính tham khảo, không phải khuyến nghị đầu tư.\\n\\n"
        "Trân trọng,\\nSTOCKWISE"
    )
    safe_filename = re.sub(r"[^A-Za-z0-9_.-]", "_", filename)[:100] or "STOCKWISE_report.pdf"
    msg.add_attachment(
        bytes(pdf_bytes), maintype="application", subtype="pdf", filename=safe_filename
    )
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=25) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)
