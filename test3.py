#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动漫图片超分修复 & AI智能去水印 & 批量重命名工具 v2.0
"""

import os
import sys
import base64
import json
import re
from pathlib import Path
from io import BytesIO

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageEnhance
    from openai import OpenAI
except ImportError:
    print("❌ 缺少依赖，请运行: pip install PyQt6 opencv-python-headless Pillow numpy openai")
    sys.exit(1)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox, QLabel,
    QSpinBox, QComboBox, QCheckBox, QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont

API_KEY  = "sk-26c7f85c8eae4ef68cf84020508ebb76"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL    = "qwen3-vl-plus"  # 或者用 qwen-vl-max


PRINT_SIZES = {
    "AI智能裁剪 · 竖版 5:7 (商品主图)": (1500, 2100),
    "AI智能裁剪 · 横版 7:5 (横幅海报)": (2100, 1500),
}

CONFIG_FILE = "anime_pro_config.json"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("last_start_index", 1)
                data.setdefault("last_prefix", "goods")
                data.setdefault("last_size", list(PRINT_SIZES.keys())[0])
                data.setdefault("skip_ai", False)
                return data
        except:
            pass
    return {
        "last_prefix": "goods",
        "last_start_index": 1,
        "last_size": list(PRINT_SIZES.keys())[0],
        "skip_ai": False,
    }


def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except:
        pass


def detect_watermark_region(img_cv: np.ndarray, log_fn) -> tuple | None:
    h, w = img_cv.shape[:2]
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    _, mask = cv2.threshold(tophat, 18, 255, cv2.THRESH_BINARY)

    qh, qw = h // 4, w // 4
    quadrants = {
        "右下": mask[h - qh:, w - qw:],
        "左下": mask[h - qh:, :qw],
        "右上": mask[:qh, w - qw:],
        "左上": mask[:qh, :qw],
    }
    densities = {k: np.sum(v > 0) for k, v in quadrants.items()}
    best = max(densities, key=densities.get)
    best_density = densities[best]

    threshold = qh * qw * 0.005
    if best_density < threshold:
        log_fn("  ℹ️  未检测到明显水印，跳过去水印步骤。")
        return None

    rw, rh = int(w * 0.30), int(h * 0.20)
    coords = {
        "右下": (w - rw, h - rh, w, h),
        "左下": (0, h - rh, rw, h),
        "右上": (w - rw, 0, w, rh),
        "左上": (0, 0, rw, rh),
    }
    log_fn(f"  🔍 自动检测到水印位置：{best}角 (置信度: {best_density:.0f}px)")
    return coords[best]


def remove_watermark_auto(img_cv: np.ndarray, log_fn) -> np.ndarray:
    region = detect_watermark_region(img_cv, log_fn)
    if region is None:
        return img_cv

    x1, y1, x2, y2 = region
    roi = img_cv[y1:y2, x1:x2]
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    tophat = cv2.morphologyEx(gray_roi, cv2.MORPH_TOPHAT, kernel)
    _, mask = cv2.threshold(tophat, 18, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(mask, np.ones((4, 4), np.uint8), iterations=2)

    if np.sum(mask > 0) < 50:
        log_fn("  ℹ️  水印区域蒙版过小，跳过修复。")
        return img_cv

    inpainted = cv2.inpaint(roi, mask, inpaintRadius=6, flags=cv2.INPAINT_TELEA)
    result = img_cv.copy()
    result[y1:y2, x1:x2] = inpainted
    log_fn("  ✅ 水印已自动修复完成。")
    return result


def analyze_and_detect_subject(image_path: str, log_fn) -> dict:
    log_fn(f"  🤖 正在调用 {MODEL} 进行美学构图分析...")
    try:
        img_for_ai = Image.open(image_path).convert("RGB")
        if max(img_for_ai.size) > 1024:
            img_for_ai.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        buf = BytesIO()
        img_for_ai.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()

        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        completion = client.chat.completions.create(
            model=MODEL,
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "你是资深动漫商品排版设计师。分析这张动漫图片用于拼多多高清商品主图。\n"
                            "识别画面中'最具吸引力的视觉焦点'（人物需完整框选，顶部包含头发）。\n"
                            "返回该焦点的归一化坐标 [ymin, xmin, ymax, xmax]（范围 0-1000）。\n"
                            "仅回复 JSON，不要其他文字：\n"
                            "{\"style\":\"风格描述\",\"subject_box\":[ymin,xmin,ymax,xmax]}"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    }
                ]
            }]
        )
        content = completion.choices[0].message.content
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if m:
            data = json.loads(m.group())
            if "subject_box" in data and len(data["subject_box"]) == 4:
                log_fn(f"  ✅ AI识别风格：{data.get('style', '—')}")
                return data
        log_fn("  ⚠️ AI 未返回有效坐标，将回退标准等比裁剪。")
        return {}
    except Exception as e:
        log_fn(f"  ⚠️ AI 分析失败: {e}")
        return {}


def smart_ai_crop(img_pil: Image.Image, subject_box: list,
                  target_size: tuple, log_fn) -> Image.Image:
    w, h = img_pil.size
    tw, th = target_size
    target_ratio = tw / th

    ymin, xmin, ymax, xmax = [
        int(v * (h if i % 2 == 0 else w) / 1000)
        for i, v in enumerate(subject_box)
    ]
    sbj_h = ymax - ymin
    visual_cx = (xmin + xmax) // 2
    visual_cy = ymin + int(sbj_h * 0.3)

    if target_ratio > 1:
        crop_h = h
        crop_w = int(h * target_ratio)
        if crop_w > w:
            crop_w = w
            crop_h = int(w / target_ratio)
            crop_l = 0
            crop_t = max(0, min(visual_cy - int(crop_h * 0.33), h - crop_h))
        else:
            crop_t = 0
            crop_l = max(0, min(visual_cx - crop_w // 2, w - crop_w))
    else:
        crop_w = w
        crop_h = int(w / target_ratio)
        if crop_h > h:
            crop_h = h
            crop_w = int(h * target_ratio)
            crop_t = 0
            crop_l = max(0, min(visual_cx - crop_w // 2, w - crop_w))
        else:
            crop_l = 0
            ideal_t = visual_cy - int(crop_h * 0.33)
            safe_top = max(0, ymin - int(crop_h * 0.05))
            crop_t = max(0, min(ideal_t, h - crop_h))
            if crop_t > safe_top:
                crop_t = safe_top

    log_fn("  📐 已应用美学构图方案（三分法 + 护头）...")
    return img_pil.crop(
        (crop_l, crop_t, crop_l + crop_w, crop_t + crop_h)
    ).resize(target_size, Image.LANCZOS)


def crop_standard(img_pil: Image.Image, target_size: tuple) -> Image.Image:
    tw, th = target_size
    w, h = img_pil.size
    if w / h > tw / th:
        nw = int(h * tw / th)
        l = (w - nw) // 2
        cropped = img_pil.crop((l, 0, l + nw, h))
    else:
        nh = int(w * th / tw)
        t = (h - nh) // 2
        cropped = img_pil.crop((0, t, w, t + nh))
    return cropped.resize(target_size, Image.LANCZOS)


def compute_scale(orig_size: tuple, target_size: tuple) -> int:
    ow, oh = orig_size
    tw, th = target_size
    scale_w = (tw + ow - 1) // ow
    scale_h = (th + oh - 1) // oh
    scale = max(scale_w, scale_h)
    return min(max(scale, 1), 8)


def anime_sharpen(img_cv: np.ndarray) -> np.ndarray:
    f = img_cv.astype(np.float32)
    blur = cv2.GaussianBlur(f, (0, 0), sigmaX=1.5)
    usm = cv2.addWeighted(f, 1.3, blur, -0.3, 0)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    mask = (np.abs(lap) / (np.abs(lap).max() + 1e-6) * 0.25).astype(np.float32)
    mask3 = np.stack([mask] * 3, axis=2)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    xsharp = cv2.filter2D(f, -1, kernel)
    return np.clip(usm * (1 - mask3) + xsharp * mask3, 0, 255).astype(np.uint8)


def enhance_colors(img_pil: Image.Image) -> Image.Image:
    img_pil = ImageEnhance.Contrast(img_pil).enhance(1.15)
    img_pil = ImageEnhance.Color(img_pil).enhance(1.20)
    img_pil = ImageEnhance.Brightness(img_pil).enhance(1.05)
    return ImageEnhance.Sharpness(img_pil).enhance(1.2)


class ProcessWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int)

    def __init__(self, in_dir, out_dir, prefix, start_idx, size_key, skip_ai):
        super().__init__()
        self.in_dir = in_dir
        self.out_dir = out_dir
        self.prefix = prefix
        self.start_idx = start_idx
        self.size_key = size_key
        self.skip_ai = skip_ai

    def run(self):
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = sorted([
            f for f in os.listdir(self.in_dir)
            if Path(f).suffix.lower() in exts
        ])

        if not files:
            self.log_signal.emit(f"❌ {self.in_dir} 中未找到支持的图片格式。")
            self.finished_signal.emit(0, 0)
            return

        os.makedirs(self.out_dir, exist_ok=True)
        target_size = PRINT_SIZES[self.size_key]
        ok = 0
        counter = self.start_idx

        for i, name in enumerate(files, 1):
            path = os.path.join(self.in_dir, name)
            self.log_signal.emit(f"\n{'━' * 42}")
            self.log_signal.emit(f"[{i}/{len(files)}]  {name}")

            try:
                img = Image.open(path).convert("RGB")
                ow, oh = img.size
                self.log_signal.emit(f"  原始尺寸: {ow} × {oh} px")

                self.log_signal.emit("  💧 智能检测并去除水印...")
                cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                cv_img = remove_watermark_auto(cv_img, self.log_signal.emit)
                img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

                scale = compute_scale((ow, oh), target_size)
                self.log_signal.emit(f"  🔍 自动放大 ×{scale}（目标 {target_size[0]}×{target_size[1]} px）...")
                img_up = img.resize((ow * scale, oh * scale), Image.LANCZOS)
                self.log_signal.emit(f"     放大后: {img_up.size[0]} × {img_up.size[1]} px")

                if not self.skip_ai:
                    ai_data = analyze_and_detect_subject(path, self.log_signal.emit)
                    if "subject_box" in ai_data:
                        img_cropped = smart_ai_crop(img_up, ai_data["subject_box"], target_size, self.log_signal.emit)
                    else:
                        self.log_signal.emit("  📐 回退标准等比居中裁剪...")
                        img_cropped = crop_standard(img_up, target_size)
                else:
                    self.log_signal.emit("  📐 标准等比居中裁剪...")
                    img_cropped = crop_standard(img_up, target_size)

                self.log_signal.emit("  ✨ 柔和锐化 & 打印色彩补偿...")
                cv_c = cv2.cvtColor(np.array(img_cropped), cv2.COLOR_RGB2BGR)
                cv_c = anime_sharpen(cv_c)
                img_final = enhance_colors(
                    Image.fromarray(cv2.cvtColor(cv_c, cv2.COLOR_BGR2RGB))
                )

                while True:
                    save_name = f"{self.prefix}_{counter:04d}.png"
                    save_path = os.path.join(self.out_dir, save_name)
                    if not os.path.exists(save_path):
                        break
                    counter += 1

                img_final.save(save_path, "PNG", dpi=(300, 300))
                mb = os.path.getsize(save_path) / 1024 / 1024
                self.log_signal.emit(f"  ✅ 已保存: {save_name}  ({mb:.1f} MB)")
                ok += 1
                counter += 1

            except Exception as e:
                self.log_signal.emit(f"  ❌ 处理失败: {e}")

        self.finished_signal.emit(ok, len(files))


DARK = "#0F1117"
CARD = "#1A1B22"
BORDER = "#2E2F38"
ACCENT = "#00D47E"
ACCENT2 = "#4E9BFF"
TEXT = "#E8E9F0"
MUTED = "#6B6D7A"

STYLE = f"""
QWidget {{
    background: {DARK};
    color: {TEXT};
    font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
    font-size: 13px;
}}
QLineEdit, QTextEdit, QSpinBox, QComboBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    color: {TEXT};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
}}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {BORDER};
    selection-background-color: #1E3A2F;
    color: {TEXT};
    padding: 4px;
}}
QPushButton {{
    background: #252630;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
    color: {TEXT};
}}
QPushButton:hover {{
    background: #2E3040;
    border-color: {ACCENT};
}}
QPushButton#btn_run {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00C571, stop:1 #00A85C);
    color: white;
    border: none;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 1px;
    border-radius: 10px;
}}
QPushButton#btn_run:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00D87A, stop:1 #00C066);
}}
QPushButton#btn_run:disabled {{
    background: #162A1F;
    color: #2A5040;
}}
QTextEdit {{
    background: #0C0D12;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    color: #9ECEFF;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px;
    line-height: 1.6;
}}
QCheckBox {{
    spacing: 8px;
    color: {MUTED};
}}
QCheckBox:hover {{ color: {TEXT}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border-radius: 5px;
    border: 1.5px solid {BORDER};
    background: {CARD};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 12'><path d='M2 6l3 3 5-5' stroke='white' stroke-width='2' fill='none' stroke-linecap='round'/></svg>");
}}
QLabel#section_label {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QFrame#divider {{
    border: none;
    border-top: 1px solid {BORDER};
    max-height: 1px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {BORDER};
    border: none;
    border-radius: 3px;
    width: 18px;
}}
"""


def section_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("section_label")
    return lbl


def divider():
    f = QFrame()
    f.setObjectName("divider")
    return f


class AnimeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎌 动漫图片全自动处理工具  v2.0")
        self.resize(820, 700)
        self.setStyleSheet(STYLE)
        self.config = load_config()
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        title = QLabel("🎌  动漫图片全自动处理工具")
        title.setFont(QFont("Microsoft YaHei UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT}; letter-spacing: 0.5px;")
        lay.addWidget(title)
        lay.addWidget(divider())

        lay.addWidget(section_label("📁  文件路径"))
        for attr, ph, btn_txt in [
            ("edit_in", "选择待处理照片的源文件夹...", "浏览源目录"),
            ("edit_out", "输出目录（留空则在源目录下自动创建）...", "选择输出目录"),
        ]:
            row = QHBoxLayout()
            edit = QLineEdit()
            edit.setPlaceholderText(ph)
            edit.setReadOnly(True)
            setattr(self, attr, edit)
            btn = QPushButton(f"  📁  {btn_txt}")
            btn.setFixedWidth(140)
            btn.clicked.connect(lambda _, e=edit: self._pick_dir(e))
            row.addWidget(edit, stretch=1)
            row.addWidget(btn)
            lay.addLayout(row)

        lay.addWidget(divider())

        lay.addWidget(section_label("⚙️  处理参数"))
        params = QHBoxLayout()
        params.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(8)

        left.addWidget(QLabel("裁剪规格"))
        self.cb_size = QComboBox()
        self.cb_size.addItems(list(PRINT_SIZES.keys()))
        self.cb_size.setCurrentText(self.config.get("last_size", list(PRINT_SIZES.keys())[0]))
        left.addWidget(self.cb_size)

        left.addSpacing(4)
        self.chk_skip = QCheckBox("跳过 AI 分析（使用标准等比裁剪）")
        self.chk_skip.setChecked(self.config.get("skip_ai", False))
        left.addWidget(self.chk_skip)

        right = QVBoxLayout()
        right.setSpacing(8)

        right.addWidget(QLabel("文件命名前缀"))
        self.edit_prefix = QLineEdit(self.config["last_prefix"])
        self.edit_prefix.setPlaceholderText("例如: goods")
        right.addWidget(self.edit_prefix)

        right.addSpacing(4)
        right.addWidget(QLabel("起始序号"))
        self.sp_idx = QSpinBox()
        self.sp_idx.setRange(1, 9999)
        self.sp_idx.setValue(self.config["last_start_index"])
        right.addWidget(self.sp_idx)

        right.addStretch()

        params.addLayout(left, stretch=3)
        params.addLayout(right, stretch=2)
        lay.addLayout(params)

        lay.addWidget(divider())

        lay.addWidget(section_label("📋  处理日志"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("日志将在处理时显示...")
        lay.addWidget(self.log, stretch=10)

        self.btn_run = QPushButton("🚀  开始全自动处理")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setFixedHeight(48)
        self.btn_run.clicked.connect(self._start)
        lay.addWidget(self.btn_run)

    def _pick_dir(self, edit):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d:
            edit.setText(d)

    def _start(self):
        in_d = self.edit_in.text().strip()
        if not in_d:
            QMessageBox.warning(self, "提示", "请先选择源照片文件夹！")
            return

        out_d = self.edit_out.text().strip() or os.path.join(in_d, "enhanced_output")

        self.config.update({
            "last_prefix": self.edit_prefix.text().strip() or "goods",
            "last_start_index": self.sp_idx.value(),
            "last_size": self.cb_size.currentText(),
            "skip_ai": self.chk_skip.isChecked(),
        })
        save_config(self.config)

        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳  拼命处理中，请稍候...")
        self.log.clear()
        self.log.append(f"▶ 源目录: {in_d}")
        self.log.append(f"▶ 输出目录: {out_d}")
        self.log.append(f"▶ 规格: {self.cb_size.currentText()}")
        self.log.append(f"▶ AI构图: {'关闭（标准裁剪）' if self.chk_skip.isChecked() else '开启'}")

        self.worker = ProcessWorker(
            in_dir=in_d,
            out_dir=out_d,
            prefix=self.config["last_prefix"],
            start_idx=self.config["last_start_index"],
            size_key=self.cb_size.currentText(),
            skip_ai=self.chk_skip.isChecked(),
        )
        self.worker.log_signal.connect(self.log.append)
        self.worker.finished_signal.connect(self._done)
        self.worker.start()

    def _done(self, ok, total):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("🚀  开始全自动处理")
        self.log.append(f"\n{'━' * 42}")
        self.log.append(f"🎉 全部完成！成功处理 {ok} / {total} 张。")
        out_d = self.worker.out_dir
        QMessageBox.information(
            self, "✅ 完成",
            f"批量处理完成！\n\n✔ 成功: {ok} / {total} 张\n📂 输出目录:\n{out_d}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = AnimeApp()
    win.show()
    sys.exit(app.exec())
