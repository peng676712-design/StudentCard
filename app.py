from flask import Flask, render_template, request, redirect, url_for, send_file, session
from PIL import Image, ImageDraw, ImageFont
import io, os, textwrap, time

app = Flask(__name__)
app.secret_key = "your_secret_key"  # 必須設定 session key

LOCK_DURATION = 600  # 10 分鐘 (秒)

# ---------- 工具函式 ----------
def fit_text(font_path, text, max_width, start_size, min_size=24):
    size = start_size
    while size >= min_size:
        f = ImageFont.truetype(font_path, size)
        if f.getlength(text) <= max_width:
            return f
        size -= 2
    return ImageFont.truetype(font_path, min_size)

def wrap_lines(font, text, max_width):
    lines = []
    raw = text.split("\n")
    for block in raw:
        if not block.strip():
            continue
        for candidate in textwrap.wrap(block, width=max(1, int(max_width / (font.size * 0.6)))):
            while font.getlength(candidate) > max_width and len(candidate) > 1:
                cut = int(len(candidate) * max_width / font.getlength(candidate))
                lines.append(candidate[:cut])
                candidate = candidate[cut:]
            if candidate:
                lines.append(candidate)
    return lines

# ---------- 驗證規則 ----------
ALLOWED_CODES = {
    "30","31","32","33","34","35","36","37","38","39",
    "44","45","54","57","59","65","81","82","83","84",
    "A5","AC","AB","C0"
}

# ---------- 科系對照表 ----------
DEPT_MAP = {
    "30": "機械工程系","31": "電機工程系","32": "化學工程系","33": "材料科學系",
    "34": "土木工程系","35": "分子科學系","36": "電子工程系","37": "工業管理系",
    "38": "工業設計系","39": "建築系","44": "車輛工程系","45": "能源工程系",
    "54": "英文系","57": "經營管理系","59": "資訊工程系","65": "光電工程系",
    "81": "機電學士班","82": "電資學士班","83": "工程科技學士班","84": "創意設計學士班",
    "A5": "文化發展系","AC": "互動設計系","AB": "資訊財金系","C0": "機電學院"
}

# ---------- 路由 ----------
@app.route("/")
def home():
    return render_template("upload.html")

@app.route("/upload_photo", methods=["POST"])
def upload_photo():
    student_id = request.form.get("student_id", "").strip()

    if "fail_count" not in session:
        session["fail_count"] = 0
        session["lock_until"] = 0

    if time.time() < session["lock_until"]:
        return render_template("error.html", message="❌ 嘗試錯誤過多，請 10 分鐘後再試", remaining=0)

    # 驗證失敗
    if len(student_id) != 9 or (student_id[3:5] not in ALLOWED_CODES):
        session["fail_count"] += 1
        remaining = 3 - session["fail_count"]

        if session["fail_count"] >= 3:
            session["lock_until"] = time.time() + LOCK_DURATION
            return render_template("error.html", message="❌ 輸入錯誤三次，已封鎖 10 分鐘", remaining=0)

        return render_template("error.html", message="❌ 學號輸入錯誤", remaining=remaining)

    # 驗證成功 → 存入 session
    session["fail_count"] = 0
    session["lock_until"] = 0

    combo = student_id[3:5]
    dept = DEPT_MAP.get(combo, "未知科系")
    group = ""

    # 🔹 互動設計系第六碼判斷組別
    if dept == "互動設計系":
        sixth_digit = student_id[5]
        if sixth_digit == "1":
            group = "媒體設計組"
        elif sixth_digit == "2":
            group = "視覺傳達組"

    # 存到 session，不放在網址
    session["student_id"] = student_id
    session["dept"] = dept
    session["group"] = group

    return redirect(url_for("form"))

@app.route("/form")
def form():
    student_id = session.get("student_id", "")
    dept = session.get("dept", "")
    group = session.get("group", "")
    return render_template("form.html", student_id=student_id, dept=dept, group=group)

@app.route("/generate", methods=["POST"])
def generate():
    name = request.form.get("name", "").strip()
    student_id = session.get("student_id", "")
    dept = session.get("dept", "")
    group = session.get("group", "")
    gender = request.form.get("gender", "").strip()
    photo_file = request.files.get("photo")

    template_path = "static/templates/student_card.jpg"
    if not os.path.exists(template_path):
        return "❌ 找不到背景圖：" + template_path
    card = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(card)
    W, H = card.size

    font_path = "fonts/特粗楷體.ttf"
    if not os.path.exists(font_path):
        return "❌ 找不到字型檔：" + font_path

    photo_w, photo_h = 680, 817
    center_x, center_y = 425, 817
    photo_x = center_x - photo_w // 2
    photo_y = center_y - photo_h // 2

    if photo_file and photo_file.filename != "":
        user_img = Image.open(photo_file).convert("RGBA")
        user_img = user_img.resize((photo_w, photo_h), Image.LANCZOS)
        card.paste(user_img, (photo_x, photo_y))

    side_texts = ["四年制大學部", dept]
    if dept == "互動設計系" and group:
        side_texts.append(group)

    side_font = ImageFont.truetype(font_path, int(H * 0.06))
    side_line_gap = int(H * 0.08)
    side_x = photo_x + photo_w + 30
    side_start_y = photo_y + 80
    for i, line in enumerate(side_texts):
        y = side_start_y + i * side_line_gap
        draw.text((side_x, y), line, fill="black", font=side_font)

    info_font = ImageFont.truetype(font_path, int(H * 0.06))
    draw.text((photo_x, int(H * 0.82)), f"姓名: {name}", fill="black", font=info_font)
    draw.text((photo_x, int(H * 0.9)), f"學號: {student_id}", fill="black", font=info_font)
    draw.text((int(W * 0.36), int(H * 0.9)), f"性別: {gender}", fill="black", font=info_font)

    img_io = io.BytesIO()
    card.save(img_io, "PNG")
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")

if __name__ == "__main__":
    app.run(debug=True)