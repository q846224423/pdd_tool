import os
import sys
import base64
import json
import re
import requests
from pathlib import Path
from io import BytesIO

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageEnhance
except ImportError:
    print("❌ 缺少依赖，请运行: pip install PyQt6 opencv-python-headless Pillow numpy requests")
    sys.exit(1)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox, QLabel,
    QSpinBox, QComboBox, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal

# ────────────────────────────────────────────
# 配置区
# ────────────────────────────────────────────
API_KEY  = "sk-46X32UEI0hNcKczjbwivYhrlvJgwQjOwCXQ7jZxut7oscoSo"
# API_URL  = "https://api.moonshot.cn/v1/chat/completions"
API_URL  = "https://api.moonshot.cn/v1"# MODEL    = "moonshot-v1-8k-vision-preview"

MODEL    = "kimi-k2.5"

# 打印规格 (宽×高 px, 300 DPI)
PRINT_SIZES = {
    "不裁剪 (保持原比例)": None,
    "AI智能美学裁剪(垂直5:7)": (1500, 2100),
    "AI智能美学裁剪(水平7:5)": (2100, 1500),
    "明信片(4×6寸)":         (1800, 1200),
    "5寸(5×3.5寸)":           (1500, 1050),
    "6寸(6×4寸)":             (1800, 1200),
    "7寸(7×5寸)":             (2100, 1500),
    "8寸(8×6寸)":             (2400, 1800),
    "10寸(10×8寸)":           (3000, 2400),
    "A4(21×29.7cm)":         (2480, 3508),
    "A3(29.7×42cm)":         (3508, 4961),
    "正方形海报(20×20cm)":   (2362, 2362),
}

CONFIG_FILE = "anime_pro_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "last_start_index" not in data:
                    data["last_start_index"] = 1
                return data
        except: pass
    return {"last_prefix": "goods", "last_start_index": 1}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

# ────────────────────────────────────────────
# 核心处理引擎
# ────────────────────────────────────────────

def analyze_and_detect_subject(image_path, log_signal):
    """带美学引导的 AI 主体检测 (内置防 400 & SSL 报错)"""
    log_signal.emit("  🤖 AI 正在进行美学构图分析...")
    try:
        # 【修复1：内存压缩】解决 400 Bad Request
        img_for_ai = Image.open(image_path).convert("RGB")
        max_size = 1024
        if max(img_for_ai.size) > max_size:
            img_for_ai.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        buf = BytesIO()
        img_for_ai.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()

        # 构造请求
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
        payload = {
            "model": MODEL,
            "max_tokens": 800,
            "temperature": 0.2,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": (
                        "你是一个资深动漫排版设计师。分析这张动漫图片用于拼多多高清商品主图。\n"
                        "请识别画面中‘最具吸引力的视觉焦点’（如果是人物，必须完整框选，且框顶部包含头顶/头发）。\n"
                        "返回该焦点的归一化坐标 [ymin, xmin, ymax, xmax] (0-1000)。\n"
                        "仅回复 JSON：{\"style\":\"风格描述\",\"subject_box\":[ymin,xmin,ymax,xmax]}"
                    )}
                ]
            }]
        }

        # 【修复2：屏蔽代理】解决 SSL 握手报错
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
                log_signal.emit("  ⚠️ AI 未能返回有效坐标，将回退居中裁剪。")
        return {}
    except Exception as e:
        log_signal.emit(f"  ⚠️ AI 分析失败: {e}")
        return {}

def smart_ai_crop(img_pil, subject_box, target_size, log_signal):
    """美学裁剪算法：三分法 + 护头机制 + 边缘留白"""
    w, h = img_pil.size
    tw, th = target_size
    target_ratio = tw / th

    ymin, xmin, ymax, xmax = [int(v * (h if i%2==0 else w) / 1000) for i, v in enumerate(subject_box)]
    sbj_h = ymax - ymin

    # 视觉重心（人物面部/胸部位置，通常在主体上部 30% 处）
    visual_cx = (xmin + xmax) // 2
    visual_cy = ymin + int(sbj_h * 0.3)

    if target_ratio > 1: # 横图
        crop_h = h; crop_w = int(h * target_ratio)
        if crop_w > w:
            crop_w = w; crop_h = int(w / target_ratio)
            crop_l = 0; crop_t = max(0, min(visual_cy - int(crop_h * 0.33), h - crop_h))
        else:
            crop_t = 0; crop_l = max(0, min(visual_cx - (crop_w // 2), w - crop_w))
    else: # 竖图 (黄金三分法应用)
        crop_w = w; crop_h = int(w / target_ratio)
        if crop_h > h:
            crop_h = h; crop_w = int(h * target_ratio)
            crop_t = 0; crop_l = max(0, min(visual_cx - (crop_w // 2), w - crop_w))
        else:
            crop_l = 0
            # 视觉重心放在裁剪框的上 1/3 处
            ideal_t = visual_cy - int(crop_h * 0.33)
            # 强制护头：给头顶留出画面高度 5% 的呼吸空间
            safe_top = max(0, ymin - int(crop_h * 0.05))
            crop_t = max(0, min(ideal_t, h - crop_h))
            if crop_t > safe_top: crop_t = safe_top

    log_signal.emit(f"  📐 已应用美学构图方案，正在裁剪...")
    return img_pil.crop((crop_l, crop_t, crop_l + crop_w, crop_t + crop_h)).resize(target_size, Image.LANCZOS)

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
    return np.clip(usm*(1-mask3) + xsharp*mask3, 0, 255).astype(np.uint8)

def enhance_colors(img_pil: Image.Image) -> Image.Image:
    """打印色彩补偿"""
    img_pil = ImageEnhance.Contrast(img_pil).enhance(1.15)
    img_pil = ImageEnhance.Color(img_pil).enhance(1.20)
    img_pil = ImageEnhance.Brightness(img_pil).enhance(1.05)
    return ImageEnhance.Sharpness(img_pil).enhance(1.5)

# ────────────────────────────────────────────
# 工作线程
# ────────────────────────────────────────────
class ProcessWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int)

    def __init__(self, in_dir, out_dir, prefix, start_idx, scale, size_key, skip_ai):
        super().__init__()
        self.in_dir, self.out_dir = in_dir, out_dir
        self.prefix, self.start_idx = prefix, start_idx
        self.scale, self.size_key, self.skip_ai = scale, size_key, skip_ai

    def run(self):
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = [f for f in os.listdir(self.in_dir) if Path(f).suffix.lower() in exts]

        if not files:
            self.log_signal.emit(f"❌ {self.in_dir} 中未找到支持的图片格式。")
            self.finished_signal.emit(0, 0)
            return

        os.makedirs(self.out_dir, exist_ok=True)
        ok = 0
        counter = self.start_idx

        for i, name in enumerate(files, 1):
            path = os.path.join(self.in_dir, name)
            self.log_signal.emit(f"\n{'━'*40}")
            self.log_signal.emit(f"[{i}/{len(files)}] 处理: {name}")
            try:
                img = Image.open(path).convert("RGB")
                ow, oh = img.size

                # 1. 超分放大
                self.log_signal.emit(f"  🔍 超分放大 ×{self.scale}...")
                img_up = img.resize((ow * self.scale, oh * self.scale), Image.LANCZOS)

                # 2. 裁剪
                target_img = img_up
                if self.size_key != "不裁剪 (保持原比例)":
                    target_size = PRINT_SIZES[self.size_key]
                    if not self.skip_ai and "AI智能" in self.size_key:
                        ai_data = analyze_and_detect_subject(path, self.log_signal)
                        if "subject_box" in ai_data:
                            target_img = smart_ai_crop(img_up, ai_data["subject_box"], target_size, self.log_signal)
                        else:
                            self.log_signal.emit(f"  📐 执行标准居中裁剪...")
                            target_img = img_up.crop((0,0,img_up.width,img_up.height)).resize(target_size, Image.LANCZOS)
                    else:
                        self.log_signal.emit(f"  📐 执行标准缩放裁剪...")
                        # 简易居中裁剪
                        tw, th = target_size; w, h = img_up.size; ratio = w/h
                        if ratio > tw/th: nh = th; nw = int(nh*ratio)
                        else: nw = tw; nh = int(nw/ratio)
                        img_tmp = img_up.resize((nw,nh), Image.LANCZOS)
                        l = (nw-tw)//2; t = (nh-th)//2
                        target_img = img_tmp.crop((l,t,l+tw,t+th))

                # 3. 增强画质
                self.log_signal.emit("  ✨ 锐化与打印色彩补偿...")
                cv_img = cv2.cvtColor(np.array(target_img), cv2.COLOR_RGB2BGR)
                cv_sharp = anime_sharpen(cv_img)
                img_final = Image.fromarray(cv2.cvtColor(cv_sharp, cv2.COLOR_BGR2RGB))
                img_final = enhance_colors(img_final)

                # 4. 保存重命名
                while True:
                    save_name = f"{self.prefix}_{counter:04d}.png"
                    target_path = os.path.join(self.out_dir, save_name)
                    if not os.path.exists(target_path): break
                    counter += 1

                img_final.save(target_path, "PNG", dpi=(300,300))
                mb = os.path.getsize(target_path) / 1024 / 1024
                self.log_signal.emit(f"  ✅ 成功保存: {save_name} ({mb:.1f} MB)")

                ok += 1
                counter += 1
            except Exception as e:
                self.log_signal.emit(f"  ❌ 失败: {e}")

        self.finished_signal.emit(ok, len(files))

# ────────────────────────────────────────────
# 界面类
# ────────────────────────────────────────────
class AnimeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("动漫图片智能美学裁剪 & 批量重命名工具")
        self.resize(850, 700)
        self.setStyleSheet("""
            QWidget { background: #1E1F23; color: #F0F0F2; font-family: 'Microsoft YaHei UI'; font-size: 13px; }
            QLineEdit, QTextEdit, QSpinBox, QComboBox { background: #26272C; border: 1px solid #3A3B42; border-radius: 6px; padding: 7px; }
            QPushButton { background: #3A3B42; border-radius: 6px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background: #4A4B52; }
            QPushButton#btn_primary { background: #07C160; color: white; border: none; font-size: 14px;}
            QPushButton#btn_primary:hover { background: #06AD56; }
            QPushButton#btn_primary:disabled { background: #0A3020; color: #2A6040; }
            QTextEdit { background: #16171A; font-family: 'Consolas'; color: #A8C7FA; }
            QCheckBox { spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #3A3B42; background: #26272C;}
            QCheckBox::indicator:checked { background: #07C160; border: 1px solid #07C160;}
        """)

        self.config = load_config()
        self.init_ui()

    def init_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # 1. 路径选择
        p_in_lay = QHBoxLayout()
        self.edit_in = QLineEdit(); self.edit_in.setPlaceholderText("选择待处理照片的源文件夹...")
        self.edit_in.setReadOnly(True)
        btn_in = QPushButton("📁 浏览源目录"); btn_in.clicked.connect(lambda: self._sel_dir(self.edit_in))
        p_in_lay.addWidget(self.edit_in, stretch=1); p_in_lay.addWidget(btn_in)
        layout.addLayout(p_in_lay)

        p_out_lay = QHBoxLayout()
        self.edit_out = QLineEdit(); self.edit_out.setPlaceholderText("保存目录 (为空则默认在源目录下新建 enhanced_output)...")
        self.edit_out.setReadOnly(True)
        btn_out = QPushButton("📁 选择保存目录"); btn_out.clicked.connect(lambda: self._sel_dir(self.edit_out))
        p_out_lay.addWidget(self.edit_out, stretch=1); p_out_lay.addWidget(btn_out)
        layout.addLayout(p_out_lay)

        # 2. 参数控制
        param_lay = QHBoxLayout()

        # 左侧：图像处理
        v_left = QVBoxLayout()
        v_left.addWidget(QLabel("放大倍数:"))
        self.cb_scale = QComboBox()
        self.cb_scale.addItems(["2", "3", "4", "6", "8"])
        self.cb_scale.setCurrentText("4")
        v_left.addWidget(self.cb_scale)

        v_left.addSpacing(10)
        v_left.addWidget(QLabel("打印规格:"))
        self.cb_size = QComboBox()
        self.cb_size.addItems(list(PRINT_SIZES.keys()))
        self.cb_size.setCurrentText("AI智能美学裁剪(垂直5:7)")
        v_left.addWidget(self.cb_size)

        v_left.addSpacing(10)
        self.chk_skip = QCheckBox("跳过 AI 分析 (不使用智能构图)")
        v_left.addWidget(self.chk_skip)

        param_lay.addLayout(v_left, stretch=1)
        param_lay.addSpacing(20)

        # 右侧：重命名
        v_right = QVBoxLayout()
        v_right.addWidget(QLabel("命名前缀:"))
        self.edit_pre = QLineEdit(self.config["last_prefix"])
        self.edit_pre.setPlaceholderText("如: goods")
        v_right.addWidget(self.edit_pre)

        v_right.addSpacing(10)
        v_right.addWidget(QLabel("起始序号:"))
        self.sp_idx = QSpinBox()
        self.sp_idx.setRange(1, 9999)
        self.sp_idx.setValue(self.config["last_start_index"])
        v_right.addWidget(self.sp_idx)

        v_right.addStretch()
        param_lay.addLayout(v_right, stretch=1)

        layout.addLayout(param_lay)

        # 3. 日志窗
        self.log = QTextEdit(); layout.addWidget(self.log, stretch=1)

        # 4. 按钮
        self.btn_run = QPushButton("🚀 开始批量智能处理 && 重命名")
        self.btn_run.setObjectName("btn_primary"); self.btn_run.setFixedHeight(45)
        self.btn_run.clicked.connect(self._run)
        layout.addWidget(self.btn_run)

    def _sel_dir(self, edit):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d: edit.setText(d)

    def _run(self):
        in_d = self.edit_in.text().strip()
        if not in_d: return QMessageBox.warning(self, "错误", "请先选择源照片文件夹！")

        out_d = self.edit_out.text().strip() or os.path.join(in_d, "enhanced_output")

        # 保存配置
        self.config["last_prefix"] = self.edit_pre.text().strip()
        self.config["last_start_index"] = self.sp_idx.value()
        save_config(self.config)

        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳ 处理中...")
        self.log.clear()

        self.worker = ProcessWorker(
            in_dir=in_d,
            out_dir=out_d,
            prefix=self.config["last_prefix"],
            start_idx=self.config["last_start_index"],
            scale=int(self.cb_scale.currentText()),
            size_key=self.cb_size.currentText(),
            skip_ai=self.chk_skip.isChecked()
        )
        self.worker.log_signal.connect(self.log.append)
        self.worker.finished_signal.connect(self._done)
        self.worker.start()

    def _done(self, ok, total):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("🚀 开始批量智能处理 && 重命名")

        self.log.append(f"\n{'='*40}")
        self.log.append(f"🎉 处理完成！成功生成 {ok}/{total} 张高清主图。")
        QMessageBox.information(self, "完成", f"批量处理完成！\n成功: {ok}/{total}\n文件保存在:\n{self.worker.out_dir}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = AnimeApp()
    win.show()
    sys.exit(app.exec())
