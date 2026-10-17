import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO
from pathlib import Path
import html
def create_txt_invoice(customer_name, cart, total_amount, discount, final_amount):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    content = "=" * 40 + "\n"
    content += f"{'HÓA ĐƠN BÁN HÀNG - BOBA TEA':^40}\n"
    content += "=" * 40 + "\n"
    content += f"Ngày: {now}\n"
    content += f"Khách hàng: {customer_name or 'Khách vãng lai'}\n"
    content += "-" * 40 + "\n"

    for idx, item in enumerate(cart, 1):
        content += f"{idx}. {item['name']} (Size {item['size']})\n"
        content += f"   - Đường: {item['sugar']} | Đá: {item['ice']}\n"

        if item["toppings"]:
            content += f"   - Topping: {', '.join(item['toppings'])}\n"

        unit_price = calculate_unit_price(item)
        item_total = unit_price * item["quantity"]

        content += (
            f"   SL: {item['quantity']} x {unit_price:,} "
            f"= {item_total:,} VNĐ\n"
        )

    discount_amount = int(total_amount * discount / 100)

    content += "-" * 40 + "\n"
    content += f"Tổng tiền món: {total_amount:,} VNĐ\n"
    content += f"Giảm giá: {discount}% ({discount_amount:,} VNĐ)\n"
    content += f"TỔNG THANH TOÁN: {final_amount:,} VNĐ\n"
    content += "=" * 40 + "\n"
    content += f"{'Cảm ơn quý khách và hẹn gặp lại!':^40}\n"

    return content
# =========================================================
# CẤU HÌNH TRANG
# Lưu ý: đặt set_page_config trước mọi lệnh st hiển thị nội dung
# =========================================================
st.set_page_config(
    page_title=" TRÀ SỮA KHÔNG TRÀ KHÔNG SỮA | Quản lý bán hàng",
    page_icon="🧋",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = "boba_tea.db"
ASSET_DIR = Path("images")

MENU_TEA = {
    "Trà Sữa Truyền Thống": {"price": 30000, "image": "tra_sua_truyen_thong.jpg", "emoji": "🧋"},
    "Trà Sữa Trân Châu Đường Đen": {"price": 35000, "image": "tran_chau_duong_den.jpg", "emoji": "🧋"},
    "Trà Sữa Thái Xanh": {"price": 32000, "image": "tra_sua_thai_xanh.jpg", "emoji": "🍵"},
    "Trà Sữa Ô Long": {"price": 35000, "image": "tra_sua_o_long.jpg", "emoji": "🍃"},
    "Trà Sữa Matcha": {"price": 38000, "image": "tra_sua_matcha.jpg", "emoji": "🍵"},
    "Trà Sữa Dâu Tây": {"price": 35000, "image": "tra_sua_dau_tay.jpg", "emoji": "🍓"},
    "Trà Đào Cam Sả": {"price": 35000, "image": "tra_dao_cam_sa.jpg", "emoji": "🍑"},
    "Trà Dâu Tằm": {"price": 32000, "image": "tra_dau_tam.jpg", "emoji": "🫐"},
}
SIZE_OPTIONS = {"S": 0, "M": 5000, "L": 10000}
TOPPING_OPTIONS = {
    "Trân châu đen": 5000,
    "Trân châu trắng": 7000,
    "Thạch trái cây": 5000,
    "Pudding trứng": 8000,
    "Kem Cheese": 10000,
}
SUGAR_LEVELS = ["100% (Bình thường)", "70%", "50%", "30%", "0% (Không đường)"]
ICE_LEVELS = ["100% (Bình thường)", "70%", "50%", "30%", "0% (Không đá)"]

# =========================================================
# CSS GIAO DIỆN
# =========================================================
st.markdown("""
<style>
    .stApp { background: #fffaf7; }
    [data-testid="stSidebar"] { background: #fff0e8; }
    h1, h2, h3 { color: #5b2c2c; }
    .hero {
        padding: 1.4rem 1.6rem; border-radius: 20px;
        background: linear-gradient(120deg, #5b2c2c, #a84f55);
        color: white; margin-bottom: 1rem;
    }
    .hero h1 { color: white; margin: 0; }
    .hero p { color: #ffe9df; margin: .4rem 0 0 0; }
    .metric-card {
        background: white; border: 1px solid #f1d9cd; border-radius: 16px;
        padding: 1rem; box-shadow: 0 2px 8px rgba(91,44,44,.05);
    }
    .menu-name { font-weight: 700; color: #5b2c2c; min-height: 2.7rem; }
    .menu-price { font-weight: 800; color: #b64242; font-size: 1.1rem; }
    div.stButton > button[kind="primary"] {
        background: #8f3d43; border-color: #8f3d43; color: white;
        border-radius: 10px; font-weight: 650;
    }
    div.stButton > button { border-radius: 10px; }
    div[data-testid="stDataFrame"] { border: 1px solid #f1d9cd; border-radius: 12px; }
    .small-note { color: #765e58; font-size: .9rem; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE
# =========================================================
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                customer_name TEXT,
                items_json TEXT NOT NULL,
                subtotal INTEGER NOT NULL,
                discount_percent REAL NOT NULL,
                discount_amount INTEGER NOT NULL,
                total INTEGER NOT NULL,
                cash_received INTEGER NOT NULL,
                change_due INTEGER NOT NULL
            )
        """)
        conn.commit()

init_db()

# =========================================================
# SESSION STATE
# =========================================================
if "cart" not in st.session_state:
    st.session_state.cart = []
if "editing_index" not in st.session_state:
    st.session_state.editing_index = None
if "paid_order_id" not in st.session_state:
    st.session_state.paid_order_id = None
if "customer_name" not in st.session_state:
    st.session_state.customer_name = ""
if "discount_percent" not in st.session_state:
    st.session_state.discount_percent = 0
if "cash_received" not in st.session_state:
    st.session_state.cash_received = 0
if "reset_order_inputs" not in st.session_state:
    st.session_state.reset_order_inputs = False

# Reset widget values at the start of a rerun, before those widgets are created.
if st.session_state.reset_order_inputs:
    st.session_state.customer_name = ""
    st.session_state.discount_percent = 0
    st.session_state.cash_received = 0
    st.session_state.reset_order_inputs = False

def money(value):
    return f"{int(value):,} đ".replace(",", ".")

def calculate_unit_price(item):
    return (
        MENU_TEA[item["name"]]["price"]
        + SIZE_OPTIONS[item["size"]]
        + sum(TOPPING_OPTIONS[t] for t in item["toppings"])
    )

def cart_subtotal():
    return sum(calculate_unit_price(item) * item["quantity"] for item in st.session_state.cart)

def make_pdf(order):
    """Tạo PDF có hỗ trợ tiếng Việt nếu có font DejaVuSans.ttf trong thư mục fonts/."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )
    font_path = Path("fonts/DejaVuSans.ttf")
    bold_path = Path("fonts/DejaVuSans-Bold.ttf")
    font_name = "Helvetica"
    bold_name = "Helvetica-Bold"
    if font_path.exists():
        pdfmetrics.registerFont(TTFont("DejaVu", str(font_path)))
        font_name = "DejaVu"
        if bold_path.exists():
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(bold_path)))
            bold_name = "DejaVu-Bold"
        else:
            bold_name = font_name

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ShopTitle", parent=styles["Title"], fontName=bold_name,
        fontSize=18, leading=23, alignment=TA_CENTER, textColor=colors.HexColor("#8f3d43")
    ))
    styles.add(ParagraphStyle(
        name="Vietnamese", parent=styles["BodyText"], fontName=font_name,
        fontSize=9, leading=13
    ))
    styles.add(ParagraphStyle(
        name="RightVietnamese", parent=styles["BodyText"], fontName=font_name,
        fontSize=9, leading=13, alignment=TA_RIGHT
    ))

    story = [
        Paragraph("HÓA ĐƠN BÁN HÀNG - BOBA TEA", styles["ShopTitle"]),
        Spacer(1, 5*mm),
        Paragraph(f"Mã đơn: #{order['id']}", styles["Vietnamese"]),
        Paragraph(f"Thời gian: {html.escape(order['created_at'])}", styles["Vietnamese"]),
        Paragraph(f"Khách hàng: {html.escape(order['customer_name'] or 'Khách vãng lai')}", styles["Vietnamese"]),
        Spacer(1, 4*mm),
    ]
    rows = [["Món", "Tùy chọn", "SL", "Đơn giá", "Thành tiền"]]
    for item in order["items"]:
        toppings = ", ".join(item["toppings"]) if item["toppings"] else "Không"
        opts = f"Size {item['size']}; đường {item['sugar']}; đá {item['ice']}; {toppings}"
        unit = calculate_unit_price(item)
        total = unit * item["quantity"]
        rows.append([
            Paragraph(html.escape(item["name"]), styles["Vietnamese"]),
            Paragraph(html.escape(opts), styles["Vietnamese"]),
            str(item["quantity"]), money(unit), money(total)
        ])
    table = Table(rows, colWidths=[38*mm, 61*mm, 12*mm, 28*mm, 30*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8f3d43")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTNAME", (0, 0), (-1, 0), bold_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#e6cfc4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [table, Spacer(1, 5*mm)]
    summary = [
        ["Tổng tiền món", money(order["subtotal"])],
        [f"Giảm giá ({order['discount_percent']:g}%)", f"- {money(order['discount_amount'])}"],
        ["TỔNG THANH TOÁN", money(order["total"])],
        ["Khách đưa", money(order["cash_received"])],
        ["Tiền thừa", money(order["change_due"])],
    ]
    summary_table = Table(summary, colWidths=[120*mm, 45*mm], hAlign="RIGHT")
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTNAME", (0, 2), (-1, 2), bold_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#8f3d43")),
        ("LINEABOVE", (0, 2), (-1, 2), .8, colors.HexColor("#8f3d43")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [summary_table, Spacer(1, 8*mm),
              Paragraph("Cảm ơn quý khách và hẹn gặp lại!", ParagraphStyle(
                  "Thanks", parent=styles["Vietnamese"], alignment=TA_CENTER,
                  textColor=colors.HexColor("#8f3d43"), fontName=bold_name
              ))]
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def order_from_row(row):
    import json
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "customer_name": row["customer_name"] or "",
        "items": json.loads(row["items_json"]),
        "subtotal": row["subtotal"],
        "discount_percent": row["discount_percent"],
        "discount_amount": row["discount_amount"],
        "total": row["total"],
        "cash_received": row["cash_received"],
        "change_due": row["change_due"],
    }

# =========================================================
# HEADER
# =========================================================
st.markdown("""
<div class="hero">
  <h1>🧋 BOBA TEA</h1>
  <p>Hệ thống gọi món · Thanh toán · Quản lý hóa đơn</p>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("📌 Danh mục", ["Bán hàng", "Lịch sử đơn hàng"])
st.sidebar.markdown("---")
st.sidebar.caption("Boba Tea POS · Dữ liệu lưu trong boba_tea.db")

# =========================================================
# TRANG BÁN HÀNG
# =========================================================
if page == "Bán hàng":
    st.subheader("🍓 Menu trà sữa")
    st.caption("Chọn món bên dưới để thêm vào đơn hàng. Giá tính bằng VNĐ.")

    menu_cols = st.columns(4)
    for idx, (tea_name, info) in enumerate(MENU_TEA.items()):
        with menu_cols[idx % 4]:
            with st.container(border=True):
                image_path = ASSET_DIR / info["image"]
                if image_path.exists():
                    st.image(str(image_path), use_container_width=True)
                else:
                    st.markdown(
                        f"<div style='height:125px;display:flex;align-items:center;"
                        f"justify-content:center;background:#fff0e8;border-radius:12px;"
                        f"font-size:3rem'>{info['emoji']}</div>",
                        unsafe_allow_html=True,
                    )
                    st.caption(f"Thêm ảnh: `images/{info['image']}`")
                st.markdown(f"<div class='menu-name'>{html.escape(tea_name)}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='menu-price'>{money(info['price'])}</div>", unsafe_allow_html=True)
                if st.button("＋ Chọn món", key=f"choose_{idx}", use_container_width=True):
                    st.session_state.selected_tea = tea_name
                    st.session_state.editing_index = None

    st.markdown("---")
    left, right = st.columns([1, 1.2], gap="large")

    with left:
        st.subheader("📝 Thông tin đơn hàng")
        st.text_input("Tên khách hàng", key="customer_name", placeholder="Ví dụ: Nguyễn Văn A")
        chosen_default = st.session_state.get("selected_tea", list(MENU_TEA.keys())[0])
        chosen_tea = st.selectbox(
            "Loại trà sữa", list(MENU_TEA.keys()),
            index=list(MENU_TEA.keys()).index(chosen_default),
            key="tea_select"
        )
        edit_idx = st.session_state.editing_index
        editing = edit_idx is not None and 0 <= edit_idx < len(st.session_state.cart)
        old_item = st.session_state.cart[edit_idx] if editing else {}

        size = st.selectbox(
            "Size", list(SIZE_OPTIONS.keys()),
            index=list(SIZE_OPTIONS.keys()).index(old_item.get("size", "S")),
            key=f"size_{'edit' if editing else 'new'}"
        )
        sugar = st.selectbox(
            "Mức đường", SUGAR_LEVELS,
            index=SUGAR_LEVELS.index(old_item.get("sugar", SUGAR_LEVELS[0])),
            key=f"sugar_{'edit' if editing else 'new'}"
        )
        ice = st.selectbox(
            "Mức đá", ICE_LEVELS,
            index=ICE_LEVELS.index(old_item.get("ice", ICE_LEVELS[0])),
            key=f"ice_{'edit' if editing else 'new'}"
        )
        toppings = st.multiselect(
            "Topping (có thể chọn nhiều)", list(TOPPING_OPTIONS.keys()),
            default=old_item.get("toppings", []),
            key=f"toppings_{'edit' if editing else 'new'}"
        )
        qty = st.number_input(
            "Số lượng", min_value=1, max_value=99,
            value=int(old_item.get("quantity", 1)), step=1,
            key=f"qty_{'edit' if editing else 'new'}"
        )
        preview_item = {"name": chosen_tea, "size": size, "toppings": toppings,
                        "sugar": sugar.split()[0], "ice": ice.split()[0], "quantity": int(qty)}
        preview_unit = calculate_unit_price(preview_item)
        st.info(f"Đơn giá: **{money(preview_unit)} / ly** · Thành tiền: **{money(preview_unit * qty)}**")

        btn_label = "💾 Lưu thay đổi" if editing else "➕ Thêm vào đơn"
        if st.button(btn_label, type="primary", use_container_width=True):
            new_item = {
                "name": chosen_tea,
                "size": size,
                "sugar": sugar.split()[0],
                "ice": ice.split()[0],
                "toppings": toppings,
                "quantity": int(qty),
            }
            if editing:
                st.session_state.cart[edit_idx] = new_item
                st.session_state.editing_index = None
                st.success("Đã cập nhật món.")
            else:
                st.session_state.cart.append(new_item)
                st.success("Đã thêm món vào đơn.")
            st.session_state.paid_order_id = None
            st.rerun()
        if editing and st.button("Hủy sửa món", use_container_width=True):
            st.session_state.editing_index = None
            st.rerun()

    with right:
        st.subheader("🛒 Giỏ hàng")
        if not st.session_state.cart:
            st.info("Chưa có món nào. Chọn món từ menu để bắt đầu.")
        else:
            for i, item in enumerate(st.session_state.cart):
                unit = calculate_unit_price(item)
                total = unit * item["quantity"]
                toppings_text = ", ".join(item["toppings"]) if item["toppings"] else "Không"
                with st.container(border=True):
                    detail_col, action_col = st.columns([4, 1.4])
                    with detail_col:
                        st.markdown(f"**{i+1}. {item['name']} — Size {item['size']}**")
                        st.caption(f"Đường {item['sugar']} · Đá {item['ice']} · Topping: {toppings_text}")
                        st.write(f"{item['quantity']} × {money(unit)} = **{money(total)}**")
                    with action_col:
                        if st.button("✏️ Sửa", key=f"edit_{i}", use_container_width=True):
                            st.session_state.editing_index = i
                            st.session_state.selected_tea = item["name"]
                            st.rerun()
                        if st.button("🗑️ Xóa", key=f"delete_{i}", use_container_width=True):
                            st.session_state.cart.pop(i)
                            st.session_state.editing_index = None
                            st.session_state.paid_order_id = None
                            st.rerun()

            subtotal = cart_subtotal()
            st.markdown(f"### Tổng tiền món: {money(subtotal)}")
            discount_percent = st.number_input(
                "Giảm giá (%)", min_value=0, max_value=100, step=5,
                key="discount_percent"
            )
            discount_amount = int(subtotal * discount_percent / 100)
            total_due = subtotal - discount_amount
            st.markdown(f"**Giảm giá:** {money(discount_amount)}")
            st.markdown(f"## Cần thanh toán: {money(total_due)}")

            cash_received = st.number_input(
                "Tiền khách đưa (VNĐ)", min_value=0, step=10000,
                key="cash_received"
            )
            change_due = int(cash_received - total_due)
            if cash_received >= total_due:
                st.success(f"Tiền thừa trả khách: **{money(change_due)}**")
            else:
                st.warning(f"Khách còn thiếu: **{money(-change_due)}**")

            can_pay = cash_received >= total_due and total_due >= 0
            if st.button("💳 XÁC NHẬN THANH TOÁN", type="primary",
                         use_container_width=True, disabled=not can_pay):
                import json
                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                items_snapshot = [dict(item) for item in st.session_state.cart]
                with get_connection() as conn:
                    cursor = conn.execute("""
                        INSERT INTO orders
                        (created_at, customer_name, items_json, subtotal, discount_percent,
                         discount_amount, total, cash_received, change_due)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        now, st.session_state.customer_name.strip(),
                        json.dumps(items_snapshot, ensure_ascii=False),
                        subtotal, discount_percent, discount_amount,
                        total_due, int(cash_received), change_due
                    ))
                    order_id = cursor.lastrowid
                    conn.commit()
                st.session_state.paid_order_id = order_id
                st.session_state.last_paid_order = {
                    "id": order_id, "created_at": now,
                    "customer_name": st.session_state.customer_name.strip(),
                    "items": items_snapshot, "subtotal": subtotal,
                    "discount_percent": discount_percent,
                    "discount_amount": discount_amount, "total": total_due,
                    "cash_received": int(cash_received), "change_due": change_due,
                }
                st.session_state.cart = []
                st.session_state.editing_index = None
                st.session_state.reset_order_inputs = True
                st.success(f"Thanh toán thành công! Mã đơn #{order_id}")
                st.rerun()

    # Hóa đơn của đơn vừa thanh toán
    if st.session_state.get("last_paid_order"):
        order = st.session_state.last_paid_order
        st.markdown("---")
        st.subheader(f"🧾 Hóa đơn vừa thanh toán · #{order['id']}")
        st.write(f"**Khách hàng:** {order['customer_name'] or 'Khách vãng lai'}")
        st.write(f"**Thời gian:** {order['created_at']}")
        receipt_df = pd.DataFrame([{
            "Tên món": item["name"],
            "Size": item["size"],
            "Đường": item["sugar"],
            "Đá": item["ice"],
            "Topping": ", ".join(item["toppings"]) if item["toppings"] else "Không",
            "Số lượng": item["quantity"],
            "Đơn giá": calculate_unit_price(item),
            "Thành tiền": calculate_unit_price(item) * item["quantity"],
        } for item in order["items"]])
        st.dataframe(receipt_df, use_container_width=True, hide_index=True)
        a, b, c = st.columns(3)
        a.metric("Tổng tiền món", money(order["subtotal"]))
        b.metric("Tổng thanh toán", money(order["total"]))
        c.metric("Tiền thừa", money(order["change_due"]))
        pdf_bytes = make_pdf(order)
        if pdf_bytes:
            st.download_button(
                "📄 Tải hóa đơn PDF",
                data=pdf_bytes,
                file_name=f"HoaDon_BobaTea_{order['id']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Chưa cài thư viện reportlab. Hãy chạy: pip install reportlab")

# =========================================================
# TRANG LỊCH SỬ ĐƠN HÀNG
# =========================================================
else:
    st.subheader("📚 Lịch sử đơn hàng")
    st.caption("Đơn hàng được lưu trong SQLite tại file boba_tea.db trên máy chạy ứng dụng.")
    with get_connection() as conn:
        history_rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()

    if not history_rows:
        st.info("Chưa có đơn hàng nào được thanh toán.")
    else:
        history = pd.DataFrame([{
            "Mã đơn": row["id"],
            "Thời gian": row["created_at"],
            "Khách hàng": row["customer_name"] or "Khách vãng lai",
            "Tổng tiền món": row["subtotal"],
            "Giảm giá (%)": row["discount_percent"],
            "Tổng thanh toán": row["total"],
            "Khách đưa": row["cash_received"],
            "Tiền thừa": row["change_due"],
        } for row in history_rows])
        search = st.text_input("Tìm theo mã đơn hoặc tên khách hàng", placeholder="Nhập mã đơn hoặc tên...")
        if search.strip():
            mask = (
                history["Mã đơn"].astype(str).str.contains(search.strip(), case=False)
                | history["Khách hàng"].astype(str).str.contains(search.strip(), case=False)
            )
            history = history[mask]
        st.dataframe(history, use_container_width=True, hide_index=True)

        order_ids = [int(row["id"]) for row in history_rows]
        selected_order_id = st.selectbox("Xem chi tiết đơn hàng", order_ids)
        selected_row = next(row for row in history_rows if int(row["id"]) == int(selected_order_id))
        order = order_from_row(selected_row)
        st.markdown(f"### Chi tiết đơn #{order['id']}")
        st.write(f"**Khách hàng:** {order['customer_name'] or 'Khách vãng lai'}")
        st.write(f"**Thời gian:** {order['created_at']}")
        detail_df = pd.DataFrame([{
            "Tên món": item["name"], "Size": item["size"], "Đường": item["sugar"],
            "Đá": item["ice"],
            "Topping": ", ".join(item["toppings"]) if item["toppings"] else "Không",
            "Số lượng": item["quantity"], "Đơn giá": calculate_unit_price(item),
            "Thành tiền": calculate_unit_price(item) * item["quantity"],
        } for item in order["items"]])
        st.dataframe(detail_df, use_container_width=True, hide_index=True)
        x, y, z = st.columns(3)
        x.metric("Tổng tiền món", money(order["subtotal"]))
        y.metric("Tổng thanh toán", money(order["total"]))
        z.metric("Tiền thừa", money(order["change_due"]))
        pdf_bytes = make_pdf(order)
        if pdf_bytes:
           txt_data = create_txt_invoice(
    order["customer_name"],
    order["items"],
    order["subtotal"],
    order["discount_percent"],
    order["total"]
)

st.download_button(
    label="📥 Tải hóa đơn (.TXT)",
    data=txt_data,
    file_name=f"HoaDon_BobaTea_{order['id']}.txt",
    mime="text/plain",
    use_container_width=True
)

st.markdown("---")
st.markdown("<p style='text-align:center;color:#8b6f66'>🧋 Boba Tea · Chúc bạn kinh doanh thuận lợi!</p>", unsafe_allow_html=True)
