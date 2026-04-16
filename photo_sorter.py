import os
import sys
import base64
import json
import re
import requests
from pathlib import Path
from datetime import datetime

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageEnhance
except ImportError as e:
    print(f"❌ 缺少依赖库: {e}")
    print("请运行: pip install PyQt6 opencv-python-headless Pillow numpy requests")
    sys.exit(1)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox, QLabel,
    QSpinBox, QComboBox, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal

# ────────────────────────────────────────────
# 配置项
# ────────────────────────────────────────────
# 请替换为您自己的 Moonshot API Key
API_KEY  = "sk-46X32UEI0hNcKczjbwivYhrlvJgwQjOwCXQ7jZxut7oscoSo"
API_URL  = "https://api.moonshot.cn/v1/chat/completions"
MODEL    = "moonshot-v1-8k-vision-preview" # 使用支持视觉的模型

# 打印规格 (宽×高 px, 300 DPI)
PRINT_SIZES = {
    "不裁剪 (保持原比例)": None,
    "AI智能裁剪(垂直5:7)":  (1500, 2100),
    "AI智能裁剪(水平7:5)":  (2100, 1500),
    "明信片(4×6寸)":       (1800, 1200),
    "5寸(5×3.5寸)":         (1500, 1050),
    "6寸(6×4寸)":           (1800, 1200),
    "7寸(7×5寸)":           (2100, 1500),
    "8寸(8×6寸)":           (2400, 1800),
    "10寸(10×8寸)":         (3000, 2400),
    "A4(21×29.7cm)":        (2480, 3508),
    "A3(29.7×42cm)":        (3508, 4961),
    "正方形海报(20×20cm)":  (2362, 2362),
}

CONFIG_FILE = "anime_tool_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "last_start_index" not in data:
                    data["last_start_index"] = 1
                return data
        except:
            pass
    return {"last_prefix": "", "last_start_index": 1}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except:
        pass


# ────────────────────────────────────────────
# 图像处理核心函数
# ────────────────────────────────────────────
def analyze_and_detect_subject(image_path: str, log_signal) -> dict:
    """调用 Moonshot AI 进行分析和主体坐标检测 (带内存压缩防 400 报错)"""
    log_signal.emit(f"  🤖 Moonshot AI 智能分析与主体检测中 ...")

    try:
        # --- 核心修复：内存压缩，防止图片过大导致 400 报错 ---
        img_for_ai = Image.open(image_path).convert("RGB")
        max_size = 1024
        if max(img_for_ai.size) > max_size:
            img_for_ai.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        from io import BytesIO
        buffered = BytesIO()
        img_for_ai.save(buffered, format="JPEG", quality=85)
        b64 = base64.b64encode(buffered.getvalue()).decode()
        mime = "image/jpeg"
        # ----------------------------------------------------

        headers = {"Content-Type":"application/json","Authorization":f"Bearer {API_KEY}"}
        payload = {
            "model": MODEL,
            "max_tokens": 800,
            "temperature": 0.3,
            "messages": [{
                "role": "user",
                "content": [
                    {"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}},
                    {"type":"text","text":(
                        "你是一个动漫图像处理专家。分析这张动漫图片用于拼多多高清打印商品。\n"
                        "请完成以下任务：\n"
                        "1. 分析风格、清晰度和色彩。\n"
                        "2. 精确识别画面中的‘动漫主体人物’（如果没有人物，则识别最关键的物体）。\n"
                        "3. 返回该主体的紧密边界框坐标，格式为 [ymin, xmin, ymax, xmax]，坐标值归一化到 0-1000 之间（0代表左上角，1000代表右下角）。\n"
                        "\n仅以 JSON 格式回复，不要包含任何其他说明文字：\n"
                        '{"style":"风格描述","sharpness_score":8,"color_eval":"色彩评价",'
                        '"print_tip":"打印建议","enhance_tips":["建议1","建议2"],'
                        '"subject_box":[ymin,xmin,ymax,xmax]}'
                    )}
                ]
            }]
        }

        # 禁用系统代理，防止 SSL 握手失败
        proxies = { "http": None, "https": None }

        r = requests.post(API_URL, headers=headers, json=payload, timeout=35, proxies=proxies)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]

        m = re.search(r'\{.*\}', content, re.DOTALL)
        if m:
            data = json.loads(m.group())
            if "subject_box" in data and isinstance(data["subject_box"], list) and len(data["subject_box"]) == 4:
                return data
            else:
                log_signal.emit("  ⚠️  AI 未能正确返回主体坐标框。")
        return {"raw": content}

    except Exception as e:
        log_signal.emit(f"  ⚠️  AI 分析及检测失败: {e}")
        return {}

def anime_sharpen(img_cv: np.ndarray) -> np.ndarray:
    """动漫专用锐化"""
    f = img_cv.astype(np.float32)
    blur = cv2.GaussianBlur(f, (0,0), sigmaX=1.5)
    usm  = cv2.addWeighted(f, 1.75, blur, -0.75, 0)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    lap  = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    mask = (np.abs(lap) / (np.abs(lap).max() + 1e-6) * 0.25).astype(np.float32)
    mask3 = np.stack([mask]*3, axis=2)
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]], dtype=np.float32)
    xsharp = cv2.filter2D(f, -1, kernel)
    result = usm*(1-mask3) + xsharp*mask3
    return np.clip(result, 0, 255).astype(np.uint8)

def enhance_colors(img_pil: Image.Image) -> Image.Image:
    """打印色彩补偿"""
    img_pil = ImageEnhance.Contrast(img_pil).enhance(1.15)
    img_pil = ImageEnhance.Color(img_pil).enhance(1.20)
    img_pil = ImageEnhance.Brightness(img_pil).enhance(1.05)
    img_pil = ImageEnhance.Sharpness(img_pil).enhance(1.5)
    return img_pil

def smart_ai_crop(img_pil: Image.Image, subject_box: list, target_size: tuple, log_signal) -> Image.Image:
    """智能 AI 裁剪：根据坐标将主体放在视觉中心"""
    w, h = img_pil.size
    tw, th = target_size
    target_ratio = tw / th

    ymin_norm, xmin_norm, ymax_norm, xmax_norm = subject_box
    ymin = int(ymin_norm * h / 1000)
    xmin = int(xmin_norm * w / 1000)
    ymax = int(ymax_norm * h / 1000)
    xmax = int(xmax_norm * w / 1000)

    sbj_cx = (xmin + xmax) // 2
    sbj_cy = (ymin + ymax) // 2

    if target_ratio > 1: # 水平裁剪
        crop_h = h
        crop_w = int(h * target_ratio)
        if crop_w > w:
            crop_w = w
            crop_h = int(w / target_ratio)
            crop_t = (h - crop_h) // 2
            crop_l = 0
        else:
            crop_t = 0
            potential_l = sbj_cx - (crop_w // 2)
            crop_l = max(0, min(potential_l, w - crop_w))
    else: # 垂直裁剪
        crop_w = w
        crop_h = int(w / target_ratio)
        if crop_h > h:
            crop_h = h
            crop_w = int(h * target_ratio)
            crop_l = (w - crop_w) // 2
            crop_t = 0
        else:
            crop_l = 0
            potential_t = sbj_cy - int(crop_h * 0.4) # 偏上放置
            crop_t = max(0, min(potential_t, h - crop_h))

    crop_r = crop_l + crop_w
    crop_b = crop_t + crop_h
    log_signal.emit(f"  📐 AI 智能裁剪坐标: [{crop_l}, {crop_t}, {crop_r}, {crop_b}]")

    img_cropped = img_pil.crop((crop_l, crop_t, crop_r, crop_b))
    return img_cropped.resize(target_size, Image.LANCZOS)

def crop_to_print_fixed(img_pil: Image.Image, target_size: tuple) -> Image.Image:
    """标准居中裁剪"""
    tw, th = target_size
    w, h   = img_pil.size
    ratio  = w/h
    if ratio > tw/th:
        nh = th; nw = int(nh*ratio)
    else:
        nw = tw; nh = int(nw/ratio)
    img = img_pil.resize((nw,nh), Image.LANCZOS)
    l = (nw-tw)//2; t = (nh-th)//2
    return img.crop((l,t,l+tw,t+th))


# ────────────────────────────────────────────
# 工作线程 (融合处理和重命名)
# ────────────────────────────────────────────
class ProcessWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int)

    def __init__(self, target_dir, output_dir, suffix, start_index, scale, print_size, skip_ai):
        super().__init__()
        self.target_dir = target_dir
        self.output_dir = output_dir
        self.suffix = suffix
        self.start_index = start_index
        self.scale = scale
        self.print_size = print_size
        self.skip_ai = skip_ai

    def run(self):
        success_count = 0
        counter = self.start_index

        exts = {".jpg",".jpeg",".png",".webp",".bmp",".tiff"}
        files = [f for f in os.listdir(self.target_dir) if os.path.isfile(os.path.join(self.target_dir, f)) and os.path.splitext(f)[1].lower() in exts]

        total_files = len(files)
        if total_files == 0:
            self.log_signal.emit(f"❌ {self.target_dir} 中没有找到支持的图片格式。")
            self.finished_signal.emit(0, 0)
            return

        os.makedirs(self.output_dir, exist_ok=True)

        for i, filename in enumerate(files, 1):
            file_path = os.path.join(self.target_dir, filename)
            ext = ".png" # 强制输出高质量PNG

            self.log_signal.emit(f"\n{'━'*50}")
            self.log_signal.emit(f"[{i}/{total_files}] 🎌 处理: {filename}")

            try:
                img_orig = Image.open(file_path).convert("RGB")
                ow, oh = img_orig.size
                self.log_signal.emit(f"  原始尺寸: {ow} × {oh} px")

                # 1. 超分放大
                self.log_signal.emit(f"  🔍 超分放大 ×{self.scale} ...")
                img_up = img_orig.resize((ow*self.scale, oh*self.scale), Image.LANCZOS)

                # 2. AI 分析与智能裁剪
                target_img = img_up
                if self.print_size and self.print_size != "不裁剪 (保持原比例)":
                    target_size = PRINT_SIZES[self.print_size]

                    if self.print_size.startswith("AI智能裁剪") and not self.skip_ai:
                        ai_data = analyze_and_detect_subject(file_path, self.log_signal)
                        if ai_data and "subject_box" in ai_data:
                            self.log_signal.emit(f"  📐 执行智能 AI 裁剪...")
                            target_img = smart_ai_crop(img_up, ai_data["subject_box"], target_size, self.log_signal)
                        else:
                            self.log_signal.emit(f"  ⚠️ AI检测主体失败，回退至标准居中裁剪...")
                            target_img = crop_to_print_fixed(img_up, target_size)
                    else:
                        if self.print_size.startswith("AI智能裁剪") and self.skip_ai:
                            self.log_signal.emit(f"  ⚠️ 您跳过了AI分析，将执行标准居中裁剪...")
                        else:
                            self.log_signal.emit(f"  📐 执行标准居中裁剪...")
                        target_img = crop_to_print_fixed(img_up, target_size)

                # 3. 动漫锐化
                self.log_signal.emit("  ✨ 动漫专用锐化 ...")
                cv_img  = cv2.cvtColor(np.array(target_img), cv2.COLOR_RGB2BGR)
                cv_sharp = anime_sharpen(cv_img)
                img_sharp = Image.fromarray(cv2.cvtColor(cv_sharp, cv2.COLOR_BGR2RGB))

                # 4. 色彩补偿
                self.log_signal.emit("  🖨️  打印色彩补偿 ...")
                img_final = enhance_colors(img_sharp)

                # 5. 格式化重命名保存 (前缀_0001.png)
                while True:
                    new_name = f"{self.suffix}_{counter:04d}{ext}"
                    target_path = os.path.join(self.output_dir, new_name)
                    if not os.path.exists(target_path):
                        break
                    counter += 1

                img_final.save(target_path, "PNG", dpi=(300,300))
                mb = os.path.getsize(target_path) / 1024 / 1024

                self.log_signal.emit(f"  ✅ 成功保存: {new_name} ({mb:.1f} MB)")
                success_count += 1
                counter += 1

            except Exception as e:
                self.log_signal.emit(f"  ❌ 处理失败: {filename} ({str(e)})")

        self.finished_signal.emit(success_count, total_files)


# ────────────────────────────────────────────
# GUI 主窗口
# ────────────────────────────────────────────
class AnimeUpscalerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("动漫图片智能超分增强 & 批量重命名工具")
        self.resize(800, 680)
        self.setStyleSheet("""
            QWidget { background: #1E1F23; color: #F0F0F2; font-family: 'Microsoft YaHei UI'; font-size: 13px; }
            QLineEdit, QTextEdit, QSpinBox, QComboBox { background: #26272C; border: 1px solid #3A3B42; border-radius: 6px; padding: 6px; }
            QComboBox::drop-down { border: none; }
            QSpinBox::up-button, QSpinBox::down-button { width: 16px; background: #2E2F35; border-radius: 3px; }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #3A3B42; }
            QPushButton { background: #26272C; border: 1px solid #3A3B42; border-radius: 6px; padding: 6px 16px; }
            QPushButton:hover { background: #2E2F35; border: 1px solid #4A4B52; }
            QPushButton#btn_primary { background: #07C160; border: none; font-weight: bold; color: white; font-size: 14px;}
            QPushButton#btn_primary:hover { background: #06AD56; }
            QPushButton#btn_primary:disabled { background: #0A3020; color: #2A6040; }
            QCheckBox { spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #3A3B42; background: #26272C;}
            QCheckBox::indicator:checked { background: #07C160; border: 1px solid #07C160;}
        """)

        self.config = load_config()

        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- 1. 路径选择区 ---
        path_layout = QVBoxLayout()
        in_layout = QHBoxLayout()
        self.in_path_entry = QLineEdit()
        self.in_path_entry.setPlaceholderText("选择待处理的动漫图片文件夹")
        self.in_path_entry.setReadOnly(True)
        in_layout.addWidget(self.in_path_entry, stretch=1)
        btn_browse_in = QPushButton("选择源文件夹")
        btn_browse_in.clicked.connect(self._browse_in_folder)
        in_layout.addWidget(btn_browse_in)
        path_layout.addLayout(in_layout)

        out_layout = QHBoxLayout()
        self.out_path_entry = QLineEdit()
        self.out_path_entry.setPlaceholderText("选择保存处理后高清图的文件夹 (为空则默认在源文件夹下建 enhanced_output 文件夹)")
        self.out_path_entry.setReadOnly(True)
        out_layout.addWidget(self.out_path_entry, stretch=1)
        btn_browse_out = QPushButton("选择保存位置")
        btn_browse_out.clicked.connect(self._browse_out_folder)
        out_layout.addWidget(btn_browse_out)
        path_layout.addLayout(out_layout)
        main_layout.addLayout(path_layout)

        # --- 2. 参数控制区 ---
        param_layout = QHBoxLayout()

        # 左侧：处理参数
        proc_layout = QVBoxLayout()

        scale_lay = QHBoxLayout()
        scale_lay.addWidget(QLabel("放大倍数:"))
        self.scale_cb = QComboBox()
        self.scale_cb.addItems(["2", "3", "4", "6", "8"])
        self.scale_cb.setCurrentText("4")
        scale_lay.addWidget(self.scale_cb, stretch=1)
        proc_layout.addLayout(scale_lay)

        size_lay = QHBoxLayout()
        size_lay.addWidget(QLabel("打印尺寸:"))
        self.size_cb = QComboBox()
        self.size_cb.addItems(list(PRINT_SIZES.keys()))
        # 默认选中一个AI裁剪尺寸
        self.size_cb.setCurrentText("AI智能裁剪(垂直5:7)")
        size_lay.addWidget(self.size_cb, stretch=1)
        proc_layout.addLayout(size_lay)

        self.chk_skip_ai = QCheckBox("跳过 AI 智能检测 (将使用普通的居中裁剪)")
        self.chk_skip_ai.setChecked(False) # 默认开启 AI 裁剪
        proc_layout.addWidget(self.chk_skip_ai)

        param_layout.addLayout(proc_layout, stretch=1)
        param_layout.addSpacing(20)

        # 右侧：重命名参数
        rename_layout = QVBoxLayout()

        prefix_lay = QHBoxLayout()
        prefix_lay.addWidget(QLabel("命名前缀:"))
        self.prefix_input = QLineEdit(self.config.get("last_prefix", ""))
        self.prefix_input.setPlaceholderText("如: anime")
        prefix_lay.addWidget(self.prefix_input, stretch=1)
        rename_layout.addLayout(prefix_lay)

        idx_lay = QHBoxLayout()
        idx_lay.addWidget(QLabel("起始序号:"))
        self.index_input = QSpinBox()
        self.index_input.setRange(1, 9999)
        self.index_input.setValue(self.config.get("last_start_index", 1))
        idx_lay.addWidget(self.index_input, stretch=1)
        rename_layout.addLayout(idx_lay)

        rename_layout.addStretch()
        param_layout.addLayout(rename_layout, stretch=1)

        main_layout.addLayout(param_layout)

        # --- 3. 日志区 ---
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 12px; background: #16171A;")
        main_layout.addWidget(self.log_view, stretch=1)

        # --- 4. 开始按钮 ---
        self.btn_start = QPushButton("🚀 开始批量智能处理 && 重命名")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.setFixedHeight(45)
        self.btn_start.clicked.connect(self._start_processing)
        main_layout.addWidget(self.btn_start)

        self.worker = None

    def _browse_in_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择源照片文件夹")
        if folder:
            self.in_path_entry.setText(folder)

    def _browse_out_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存结果的文件夹")
        if folder:
            self.out_path_entry.setText(folder)

    def _start_processing(self):
        target_dir = self.in_path_entry.text().strip()
        if not target_dir or not os.path.exists(target_dir):
            QMessageBox.warning(self, "错误", "请先选择有效的源照片文件夹！")
            return

        selected_prefix = self.prefix_input.text().strip()
        if not selected_prefix:
            QMessageBox.warning(self, "错误", "请填写重命名前缀！")
            return

        output_dir = self.out_path_entry.text().strip()
        if not output_dir:
            output_dir = os.path.join(target_dir, "enhanced_output")

        start_index = self.index_input.value()
        scale = int(self.scale_cb.currentText())
        print_size = self.size_cb.currentText()
        skip_ai = self.chk_skip_ai.isChecked()

        # 保存配置
        self.config["last_prefix"] = selected_prefix
        self.config["last_start_index"] = start_index
        save_config(self.config)

        self.btn_start.setEnabled(False)
        self.btn_start.setText("⏳ 处理中...")
        self.log_view.clear()
        self.log_view.append(f"准备开始处理目录: {target_dir}")
        self.log_view.append(f"输出目录设定为: {output_dir}\n")

        self.worker = ProcessWorker(
            target_dir=target_dir,
            output_dir=output_dir,
            suffix=selected_prefix,
            start_index=start_index,
            scale=scale,
            print_size=print_size,
            skip_ai=skip_ai
        )
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_finished(self, success_count, total_count):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("🚀 开始批量智能处理 && 重命名")

        self.log_view.append(f"\n{'='*40}")
        self.log_view.append(f"🎉 处理完成！总计: {total_count} 张，成功: {success_count} 张。")
        QMessageBox.information(self, "完成", f"批量处理完成！\n成功处理 {success_count} / {total_count} 张照片。")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnimeUpscalerApp()
    window.show()
    sys.exit(app.exec())
