"""STOCKWISE PDF preview and Gmail SMTP delivery."""
import base64
import re
import smtplib
import ssl
from email.message import EmailMessage
import streamlit as st
import streamlit.components.v1 as components

_EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\\.[A-Za-z]{2,}$")

def render_pdf_preview(pdf_bytes: bytes) -> None:
    """Embed the actual generated PDF; users can scroll and zoom in supported browsers."""
    if not isinstance(pdf_bytes, (bytes, bytearray)) or not pdf_bytes.startswith(b"%PDF"):
        st.error("Báo cáo chưa có định dạng PDF hợp lệ.")
        return
    encoded = base64.b64encode(pdf_bytes).decode("ascii")
    components.html(
        '<iframe title="STOCKWISE PDF Preview" '
        'src="data:application/pdf;base64,' + encoded + '#toolbar=1&navpanes=0" '
        'style="width:100%;height:720px;border:1px solid #ead2eb;'
        'border-radius:14px;background:#fff"></iframe>',
        height=745,
        scrolling=False,
    )
    st.caption("Nếu trình duyệt không hỗ trợ xem PDF nhúng, hãy dùng nút Tải báo cáo PDF bên dưới.")

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
