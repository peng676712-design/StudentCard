from flask import Flask, render_template, request, redirect, url_for, send_file
from PIL import Image, ImageDraw, ImageFont
import io
import os
import textwrap

app = Flask(__name__)

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

# ---------- 路由 ----------
@app.route("/")
def home():
    return render_template("upload.html")

@app.route("/upload_photo", methods=["POST"])
def upload_photo():
    photo = request.files.get("photo")
    if not photo:
        return "❌ 沒有上傳照片"

    os.makedirs("uploads", exist_ok=True)
    photo_path = os.path.join("uploads", "student_card.png")
    photo.save(photo_path)

    # 暫時不用 pyzbar，直接給一個假學號
    student_id = "A123456789"

    # 通過 → 跳轉表單
    return redirect(url_for("form", student_id=student_id))

@app.route("/form")
def form():
    student_id = request.args.get("student_id", "")
    return render_template("form.html", student_id=student_id)

@app.route("/generate", methods=["POST"])
def generate():
    name = request.form.get("name", "").strip()
    student_id = request.form.get("student_id", "").strip()
    dept = request.form.get("dept", "").strip()
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

    # 照片區塊
    photo_w, photo_h = 680, 817
    center_x, center_y = 425, 817
    photo_x = center_x - photo_w // 2
    photo_y = center_y - photo_h // 2

    if photo_file:
        user_img = Image.open(photo_file).convert("RGBA")
        src_w, src_h = user_img.size
        target_ratio = photo_w / photo_h
        src_ratio = src_w / src_h
        if src_ratio > target_ratio:
            new_w = int(src_h * target_ratio)
            left = (src_w - new_w) // 2
            user_img = user_img.crop((left, 0, left + new_w, src_h))
        else:
            new_h = int(src_w / target_ratio)
            top = (src_h - new_h) // 2
            user_img = user_img.crop((0, top, src_w, top + new_h))
        user_img = user_img.resize((photo_w, photo_h), Image.LANCZOS)
        card.paste(user_img, (photo_x, photo_y))

    # 側邊文字
    side_texts = ["四年制大學部", "         ", "媒體設計組"]
    side_font = ImageFont.truetype(font_path, int(H * 0.06))
    side_line_gap = int(H * 0.08)
    side_x = photo_x + photo_w + 30
    side_start_y = photo_y + 40
    for i, line in enumerate(side_texts):
        y = side_start_y + i * side_line_gap
        draw.text((side_x, y), line, fill="black", font=side_font)

    # 系所文字
    base_dept_font = ImageFont.truetype(font_path, int(H * 0.065))
    dept_lines = wrap_lines(base_dept_font, dept or "", W * 0.50)
    if not dept_lines:
        dept_lines = [""]
    dept_lines = dept_lines[:3]
    for i, line in enumerate(dept_lines):
        f = fit_text(font_path, line, W * 0.50, start_size=base_dept_font.size)
        line_w = f.getlength(line)
        x = int(W * 0.43) - int(line_w / 2)
        y = int(H * 0.37) + i * int(H * 0.075)
        draw.text((x, y), line, fill="black", font=f)

    # 個人資訊
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