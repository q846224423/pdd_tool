"""
智能照片处理工具 v2.1  —  PyQt6 版  (视觉优化版)
────────────────────────────────────────────────────────────────
修复内容：
  - 复选框 indicator 蓝色方块问题（使用 image/border 方案）
  - 统计卡片顶部彩条加粗、数值更突出
  - GroupBox 标题渲染清晰
  - 整体对比度提升、间距更舒适
  - 路径输入框焦点蓝框问题修复
  - 按钮悬停动效更流畅
────────────────────────────────────────────────────────────────
"""

import os, sys, json, base64, logging, ctypes
from pathlib import Path
from typing  import Optional, List

import requests
import numpy as np
from PIL import Image, ImageEnhance
import cv2

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QCheckBox, QProgressBar, QTextEdit, QFileDialog, QFrame,
    QGroupBox, QStatusBar, QMessageBox, QAbstractItemView, QSplitter,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore  import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui   import QIcon, QColor, QPixmap, QPalette

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

API_KEY  = "sk-46X32UEI0hNcKczjbwivYhrlvJgwQjOwCXQ7jZxut7oscoSo"
API_URL  = "https://api.moonshot.cn/v1/chat/completions"
MODEL    = "moonshot-v1-8k-vision-preview"

OUTPUT_W, OUTPUT_H = 1500, 2100
MAIN_SIZE          = 800
SUPPORTED_EXT      = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

QSS = """
/* ═══ 全局重置 ══════════════════════════════════════ */
* {
    box-sizing: border-box;
    outline: none;
}

QMainWindow {
    background-color: #141416;
}

QWidget {
    color: #e8e8ed;
    font-family: "Microsoft YaHei UI", "PingFang SC", "SF Pro Display", sans-serif;
    font-size: 13px;
    background: transparent;
}

QWidget#centralWidget {
    background-color: #141416;
    border-radius: 12px;
}

/* ═══ 分组框 ════════════════════════════════════════ */
QGroupBox {
    background-color: #1c1c1f;
    border: 1px solid #2a2a2e;
    border-radius: 12px;
    margin-top: 22px;
    padding: 18px 14px 14px 14px;
    font-weight: 600;
    font-size: 12px;
    color: #98989d;
    letter-spacing: 1.5px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: -11px;
    background-color: #1c1c1f;
    color: #98989d;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

/* ═══ 输入框 ════════════════════════════════════════ */
QLineEdit {
    background-color: #0e0e10;
    border: 1px solid #2e2e32;
    border-radius: 8px;
    padding: 8px 12px;
    color: #c8c8d0;
    font-size: 12px;
    selection-background-color: #0a84ff;
}
QLineEdit:focus {
    border: 1.5px solid #0a84ff;
    background-color: #111114;
    color: #e8e8ed;
}
QLineEdit[readOnly="true"] {
    color: #636368;
    background-color: #0e0e10;
}
QLineEdit::placeholder {
    color: #3a3a3e;
}

/* ═══ 列表 ══════════════════════════════════════════ */
QListWidget {
    background-color: #0e0e10;
    border: 1px dashed #2e2e36;
    border-radius: 8px;
    color: #c8c8d0;
    outline: none;
    padding: 4px;
    font-size: 12px;
}
QListWidget::item {
    padding: 7px 10px;
    border-radius: 6px;
    margin: 1px 2px;
    color: #c8c8d0;
}
QListWidget::item:selected {
    background-color: #0a84ff;
    color: #ffffff;
}
QListWidget::item:hover:!selected {
    background-color: #1e1e24;
}

/* ═══ 按钮基础 ══════════════════════════════════════ */
QPushButton {
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid transparent;
    outline: none;
}
QPushButton:focus { outline: none; border: none; }

/* 主行动按钮 */
QPushButton#btnStart {
    background-color: #0a84ff;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 14px 0;
    border-radius: 10px;
    border: none;
    letter-spacing: 1px;
}
QPushButton#btnStart:hover {
    background-color: #338fff;
}
QPushButton#btnStart:pressed {
    background-color: #0060df;
}
QPushButton#btnStart:disabled {
    background-color: #1e1e24;
    color: #3a3a40;
    border: 1px solid #2a2a2e;
}

/* 浏览按钮 */
QPushButton#btnPick {
    background-color: #252528;
    color: #c8c8d0;
    border: 1px solid #3a3a3e;
    font-size: 12px;
    padding: 7px 14px;
}
QPushButton#btnPick:hover {
    background-color: #2e2e34;
    border-color: #4e4e54;
    color: #e8e8ed;
}
QPushButton#btnPick:pressed {
    background-color: #1e1e22;
}

/* 添加模板 */
QPushButton#btnAdd {
    background-color: rgba(48, 209, 88, 0.12);
    color: #30d158;
    border: 1px solid rgba(48, 209, 88, 0.28);
    font-size: 12px;
}
QPushButton#btnAdd:hover {
    background-color: rgba(48, 209, 88, 0.22);
    border-color: rgba(48, 209, 88, 0.5);
}
QPushButton#btnAdd:pressed {
    background-color: rgba(48, 209, 88, 0.08);
}

/* 删除按钮 */
QPushButton#btnDel {
    background-color: rgba(255, 69, 58, 0.12);
    color: #ff453a;
    border: 1px solid rgba(255, 69, 58, 0.28);
    font-size: 12px;
}
QPushButton#btnDel:hover {
    background-color: rgba(255, 69, 58, 0.22);
    border-color: rgba(255, 69, 58, 0.5);
}
QPushButton#btnDel:pressed {
    background-color: rgba(255, 69, 58, 0.08);
}

/* 清空日志 */
QPushButton#btnClear {
    background-color: transparent;
    color: #48484e;
    border: 1px solid #2a2a2e;
    padding: 5px 14px;
    font-size: 11px;
    border-radius: 6px;
}
QPushButton#btnClear:hover {
    background-color: #1e1e24;
    color: #98989d;
    border-color: #3a3a3e;
}

/* ═══ 复选框（完整重写，避免蓝色方块） ══════════════ */
QCheckBox {
    spacing: 10px;
    color: #c8c8d0;
    font-size: 13px;
    padding: 2px 0;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid #3e3e44;
    background-color: #0e0e12;
}
QCheckBox::indicator:hover {
    border-color: #0a84ff;
    background-color: #141418;
}
QCheckBox::indicator:checked {
    background-color: #0a84ff;
    border-color: #0a84ff;
    /* 用纯色填充表示选中，不依赖图片 */
}
QCheckBox::indicator:checked:hover {
    background-color: #338fff;
    border-color: #338fff;
}

/* ═══ 进度条 ════════════════════════════════════════ */
QProgressBar {
    background-color: #1a1a1e;
    border: none;
    border-radius: 3px;
    height: 6px;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0a84ff, stop:1 #5ac8fa);
    border-radius: 3px;
}

/* ═══ 日志文本框 ════════════════════════════════════ */
QTextEdit {
    background-color: #0e0e12;
    border: 1px solid #1e1e24;
    border-radius: 10px;
    color: #7a7a80;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 12px;
    line-height: 1.7;
    selection-background-color: #0a84ff;
}

/* ═══ 状态栏 ════════════════════════════════════════ */
QStatusBar {
    background-color: #0e0e12;
    border-top: 1px solid #1e1e22;
    color: #48484e;
    font-size: 11px;
    padding: 3px 16px;
}
QStatusBar QLabel {
    color: #48484e;
    background: transparent;
}

/* ═══ 分割线 ════════════════════════════════════════ */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    background-color: #2a2a2e;
    border: none;
    max-height: 1px;
}

/* ═══ 滚动条 ════════════════════════════════════════ */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 0;
}
QScrollBar::handle:vertical {
    background: #2e2e34;
    border-radius: 4px;
    min-height: 30px;
    margin: 0 1px;
}
QScrollBar::handle:vertical:hover {
    background: #3e3e46;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical { background: none; }

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0 2px;
}
QScrollBar::handle:horizontal {
    background: #2e2e34;
    border-radius: 4px;
    min-width: 30px;
    margin: 1px 0;
}
QScrollBar::handle:horizontal:hover {
    background: #3e3e46;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }

/* ═══ Splitter ══════════════════════════════════════ */
QSplitter::handle {
    background: #1e1e22;
    width: 1px;
}
QSplitter::handle:hover {
    background: #0a84ff;
}

/* ═══ 消息弹框 ══════════════════════════════════════ */
QMessageBox {
    background-color: #1c1c1f;
    color: #e8e8ed;
}
QMessageBox QLabel {
    color: #c8c8d0;
    background: transparent;
}
QMessageBox QPushButton {
    background-color: #252528;
    color: #c8c8d0;
    border: 1px solid #3a3a3e;
    border-radius: 6px;
    padding: 6px 20px;
    min-width: 70px;
}
QMessageBox QPushButton:default {
    background-color: #0a84ff;
    color: white;
    border: none;
}
QMessageBox QPushButton:hover {
    background-color: #2e2e34;
}
"""


def pil_to_base64(img: Image.Image) -> str:
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def moonshot_vision(prompt: str, img: Image.Image) -> str:
    b64 = pil_to_base64(img)
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": prompt}
        ]}],
        "max_tokens": 512
    }
    try:
        r = requests.post(API_URL, json=payload,
                          headers={"Authorization": f"Bearer {API_KEY}",
                                   "Content-Type": "application/json"},
                          timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning(f"Moonshot API 错误: {e}")
        return ""


def ai_detect_subject(img: Image.Image) -> Optional[tuple]:
    raw = moonshot_vision(
        '识别图片最重要主体，只返回JSON：{"x1":0.1,"y1":0.05,"x2":0.9,"y2":0.95}',
        img.resize((512, 512)))
    try:
        s, e = raw.find("{"), raw.rfind("}") + 1
        b = json.loads(raw[s:e])
        return b["x1"], b["y1"], b["x2"], b["y2"]
    except Exception:
        return None


def smart_crop(img: Image.Image) -> Image.Image:
    w, h = img.size
    ratio = OUTPUT_W / OUTPUT_H
    box = ai_detect_subject(img)
    cx = ((box[0]+box[2])/2*w) if box else w/2
    cy = ((box[1]+box[3])/2*h) if box else h/2
    if w/h > ratio:
        nw, nh = int(h*ratio), h
    else:
        nw, nh = w, int(w/ratio)
    l = int(max(0, min(cx - nw/2, w - nw)))
    t = int(max(0, min(cy - nh/2, h - nh)))
    return img.crop((l, t, l+nw, t+nh))


def enhance_image(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Sharpness(img).enhance(1.8)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    cv_img  = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    blurred = cv2.GaussianBlur(cv_img, (0, 0), 3)
    cv_img  = cv2.addWeighted(cv_img, 1.5, blurred, -0.5, 0)
    return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))


def remove_watermark(img: Image.Image) -> Image.Image:
    raw = moonshot_vision(
        '图中有水印/Logo/文字叠加？有则返回JSON列表[{"x1":0,"y1":0,"x2":0.3,"y2":0.1}]，'
        '无则返回[]，只返回JSON。',
        img.resize((512, 512)))
    try:
        s, e = raw.find("["), raw.rfind("]") + 1
        boxes = json.loads(raw[s:e])
        if not boxes:
            return img
        w, h = img.size
        mask = np.zeros((h, w), dtype=np.uint8)
        for b in boxes:
            x1, y1 = max(0, int(b["x1"]*w)-5), max(0, int(b["y1"]*h)-5)
            x2, y2 = min(w, int(b["x2"]*w)+5), min(h, int(b["y2"]*h)+5)
            mask[y1:y2, x1:x2] = 255
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        result = cv2.inpaint(cv_img, mask, 7, cv2.INPAINT_TELEA)
        return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    except Exception:
        return img


def composite_main(photo: Image.Image, tpl_path: str) -> Image.Image:
    tpl = Image.open(tpl_path).convert("RGBA")
    tw, th = tpl.size
    alpha = np.array(tpl)[:, :, 3]
    rows, cols = np.any(alpha == 0, axis=1), np.any(alpha == 0, axis=0)
    if rows.any() and cols.any():
        y1, y2 = np.where(rows)[0][[0, -1]]
        x1, x2 = np.where(cols)[0][[0, -1]]
    else:
        x1, y1, x2, y2 = 0, 0, tw, th
    hw, hh = x2 - x1, y2 - y1
    p = photo.convert("RGBA")
    scale = max(hw / p.width, hh / p.height)
    p = p.resize((int(p.width*scale), int(p.height*scale)), Image.LANCZOS)
    lc = (p.width  - hw) // 2
    tc = (p.height - hh) // 2
    p = p.crop((lc, tc, lc+hw, tc+hh))
    canvas = Image.new("RGBA", (tw, th), (255, 255, 255, 255))
    canvas.paste(p, (x1, y1))
    return Image.alpha_composite(canvas, tpl).convert("RGB").resize(
        (MAIN_SIZE, MAIN_SIZE), Image.LANCZOS)


def process_one(src: Path, out_dir: Path, templates: List[str],
                dewm: bool, enhance: bool, cb) -> None:
    cb(f"📂  载入  {src.name}")
    img = Image.open(src).convert("RGB")
    if dewm:
        cb("🔍  AI 检测并去水印...")
        img = remove_watermark(img)
    cb("✂️   AI 智能裁剪 5:7...")
    img = smart_crop(img)
    if enhance:
        cb("✨  分辨率增强...")
        img = enhance_image(img)
    img = img.resize((OUTPUT_W, OUTPUT_H), Image.LANCZOS)
    ext = src.suffix.lower()
    fmt = "JPEG" if ext in {".jpg", ".jpeg"} else "PNG"
    fixed = out_dir / src.name
    img.save(str(fixed), format=fmt, quality=95, dpi=(300, 300))
    cb(f"✅  修正照片  →  {fixed.name}")
    for tpl in templates:
        tp = Path(tpl)
        if not tp.exists():
            cb(f"⚠️  模板不存在: {tp.name}")
            continue
        suffix   = f"_{tp.stem}" if len(templates) > 1 else ""
        out_name = f"主图_{src.stem}{suffix}{ext}"
        cb(f"🖼   合成主图 ({tp.name})...")
        m = composite_main(img, tpl)
        m.save(str(out_dir / out_name), format=fmt, quality=95, dpi=(300, 300))
        cb(f"✅  主图       →  {out_name}")


class Worker(QThread):
    sig_log  = pyqtSignal(str)
    sig_prog = pyqtSignal(int, int)
    sig_done = pyqtSignal(int, int)

    def __init__(self, inp, out, tpls, dewm, enh):
        super().__init__()
        self.inp, self.out, self.tpls = inp, out, tpls
        self.dewm, self.enh = dewm, enh

    def run(self):
        files = [f for f in Path(self.inp).iterdir()
                 if f.suffix.lower() in SUPPORTED_EXT
                 and not f.name.startswith("主图_")]
        total = len(files)
        ok = fail = 0
        Path(self.out).mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(files):
            self.sig_log.emit(f"\n── [{i+1}/{total}] {f.name} ──")
            try:
                process_one(f, Path(self.out), self.tpls,
                            self.dewm, self.enh, self.sig_log.emit)
                ok += 1
            except Exception as e:
                self.sig_log.emit(f"❌  处理失败: {e}")
                fail += 1
            self.sig_prog.emit(i + 1, total)
        self.sig_done.emit(ok, fail)


class StatCard(QFrame):
    """统计卡片 — 顶部彩色粗边条 + 大数字"""
    def __init__(self, title: str, val: str = "—",
                 color: str = "#0a84ff", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(82)
        self._color = color
        self._apply_style()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 12, 10, 10)
        lay.setSpacing(3)

        self._v = QLabel(val)
        self._v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._v.setStyleSheet(
            f"color:{color}; font-size:28px; font-weight:800;"
            "background:transparent; border:none; letter-spacing:-0.5px;")

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(
            "color:#48484e; font-size:10px; letter-spacing:1.8px;"
            "font-weight:600; background:transparent; border:none;"
            "text-transform: uppercase;")

        lay.addStretch()
        lay.addWidget(self._v)
        lay.addWidget(t)
        lay.addStretch()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: #1a1a1e;
                border: 1px solid #252528;
                border-top: 3px solid {self._color};
                border-radius: 10px;
            }}
        """)

    def set_value(self, v):
        self._v.setText(str(v))


class PathRow(QWidget):
    def __init__(self, lbl: str, placeholder: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        label = QLabel(lbl)
        label.setFixedWidth(52)
        label.setStyleSheet(
            "color:#48484e; font-size:12px; font-weight:500;")

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setReadOnly(True)

        btn = QPushButton("浏览")
        btn.setObjectName("btnPick")
        btn.setFixedWidth(52)
        btn.clicked.connect(self._browse)

        lay.addWidget(label)
        lay.addWidget(self.edit, 1)
        lay.addWidget(btn)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d:
            self.edit.setText(d)

    def path(self) -> str:
        return self.edit.text().strip()


class MainWindow(QMainWindow):
    _LOG_COLORS = {
        "✅": "#30d158",
        "❌": "#ff453a",
        "⚠️": "#ff9f0a",
        "🚀": "#0a84ff",
        "──": "#2e2e34",
        "🏁": "#bf5af2",
        "🖼": "#5ac8fa",
        "✂️": "#30d158",
        "🔍": "#0a84ff",
        "✨": "#ffd60a",
        "📂": "#636368",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能照片处理工具")

        logo = str(Path(__file__).parent / "logo.png")
        if os.path.exists(logo):
            self.setWindowIcon(QIcon(logo))

        self.setMinimumSize(880, 680) # 限制最小尺寸
        self.resize(980, 760)         # 设置默认弹出尺寸
        self.templates: List[str] = []
        self._worker: Optional[Worker] = None

        self._build_ui()
        self.setStyleSheet(QSS)

        # 热重载 style.qss（开发用）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._reload_qss)
        self._timer.start(2000)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            "就绪  ·  选择输入文件夹并配置选项，然后点击「开始批量处理」")

    def _reload_qss(self):
        try:
            if os.path.exists("style.qss"):
                with open("style.qss", "r", encoding="utf-8") as f:
                    s = f.read()
                    if s.strip():
                        self.setStyleSheet(s)
        except Exception:
            pass

    def _build_ui(self):
        root_widget = QWidget()
        root_widget.setObjectName("centralWidget")
        self.setCentralWidget(root_widget)

        root = QVBoxLayout(root_widget)
        root.setContentsMargins(20, 18, 20, 12)
        root.setSpacing(16)

        # ── 顶部标题栏 ──────────────────────────────────
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border-bottom: 1px solid #1e1e22;
                padding-bottom: 12px;
            }
            QLabel { border: none; background: transparent; }
        """)
        hdr = QHBoxLayout(hdr_frame)
        hdr.setContentsMargins(0, 0, 0, 0)

        self.logo_label = QLabel()
        logo_path = str(Path(__file__).parent / "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled)
        else:
            self.logo_label.setText("🖼️")
            self.logo_label.setStyleSheet("font-size:22px;")
        hdr.addWidget(self.logo_label)

        title = QLabel("智能照片处理工具")
        title.setStyleSheet(
            "color:#e8e8ed; font-size:17px; font-weight:700; letter-spacing:0.3px;")

        sub = QLabel("Moonshot Vision  ·  v2.1")
        sub.setStyleSheet("color:#3a3a3e; font-size:11px;")

        hdr.addSpacing(10)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(sub)
        root.addWidget(hdr_frame)

        # ── 统计卡片行 ──────────────────────────────────
        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.c_total = StatCard("待处理", "—",  "#0a84ff")
        self.c_ok    = StatCard("已成功", "—",  "#30d158")
        self.c_fail  = StatCard("失败数", "—",  "#ff453a")
        self.c_tpl   = StatCard("主图模板", "0", "#bf5af2")
        for c in (self.c_total, self.c_ok, self.c_fail, self.c_tpl):
            cards.addWidget(c, 1)
        root.addLayout(cards)

        # ── 主体分割区 ──────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # —— 左侧面板 ——
        left_pane = QFrame()
        left_pane.setObjectName("leftPane")
        left_pane.setStyleSheet("""
            QFrame#leftPane {
                background-color: #161618;
                border: 1px solid #252528;
                border-radius: 14px;
            }
        """)
        llay = QVBoxLayout(left_pane)
        llay.setContentsMargins(14, 14, 14, 14)
        llay.setSpacing(12)

        # 路径配置
        grp_path = QGroupBox("路径配置")
        gp = QVBoxLayout(grp_path)
        gp.setSpacing(10)
        self.row_in  = PathRow("📂 输入", "选择包含照片的文件夹")
        self.row_out = PathRow("💾 输出", "选择处理结果保存位置")
        gp.addWidget(self.row_in)
        gp.addWidget(self.row_out)
        llay.addWidget(grp_path)

        # 模板配置
        grp_tpl = QGroupBox("主图模板  ·  PNG 透明镂空")
        gt = QVBoxLayout(grp_tpl)
        gt.setSpacing(8)
        self.tpl_list = QListWidget()
        self.tpl_list.setFixedHeight(100)
        self.tpl_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        gt.addWidget(self.tpl_list)

        tb = QHBoxLayout()
        tb.setSpacing(8)
        ba = QPushButton("＋  添加模板")
        ba.setObjectName("btnAdd")
        bd = QPushButton("－  删除选中")
        bd.setObjectName("btnDel")
        ba.clicked.connect(self._add_tpl)
        bd.clicked.connect(self._del_tpl)
        tb.addWidget(ba)
        tb.addWidget(bd)
        gt.addLayout(tb)


        llay.addWidget(grp_tpl)

        # 处理选项
        grp_opt = QGroupBox("处理选项")
        go = QVBoxLayout(grp_opt)
        go.setSpacing(12)
        self.chk_dewm    = QCheckBox("🔍  AI 去水印（识别区域 + inpaint 修复）")
        self.chk_enhance = QCheckBox("✨  分辨率增强（USM 锐化 + 对比度提升）")
        self.chk_dewm.setChecked(True)
        self.chk_enhance.setChecked(True)
        go.addWidget(self.chk_dewm)
        go.addWidget(self.chk_enhance)

        spec_bar = QWidget()
        spec_bar.setStyleSheet("""
            QWidget {
                background: rgba(10,132,255,0.07);
                border: 1px solid rgba(10,132,255,0.18);
                border-radius: 7px;
            }
        """)
        sb_lay = QHBoxLayout(spec_bar)
        sb_lay.setContentsMargins(12, 8, 12, 8)
        spec_lbl = QLabel("修正图  1500×2100 · 300 dpi    ·    主图  800×800")
        spec_lbl.setStyleSheet(
            "color:#2a6aad; font-size:11px; font-weight:500;"
            "background:transparent; border:none;")
        sb_lay.addWidget(spec_lbl)
        go.addWidget(spec_bar)
        llay.addWidget(grp_opt)

        llay.addStretch()

        # 开始按钮 + 进度条
        self.btn_start = QPushButton("开始批量处理")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self._start)
        self.prog = QProgressBar()
        self.prog.setFixedHeight(5)
        self.prog.setTextVisible(False)
        llay.addWidget(self.btn_start)
        llay.addWidget(self.prog)

        # —— 右侧日志面板 ——
        right_pane = QFrame()
        right_pane.setObjectName("rightPane")
        right_pane.setStyleSheet("""
            QFrame#rightPane {
                background-color: #161618;
                border: 1px solid #252528;
                border-radius: 14px;
            }
            QLabel { background: transparent; }
        """)
        rlay = QVBoxLayout(right_pane)
        rlay.setContentsMargins(14, 12, 14, 14)
        rlay.setSpacing(8)

        log_hdr = QHBoxLayout()
        log_lbl = QLabel("处 理 日 志")
        log_lbl.setStyleSheet(
            "color:#3a3a40; font-size:10px; font-weight:700; letter-spacing:3px;")
        btn_clr = QPushButton("清  空")
        btn_clr.setObjectName("btnClear")
        btn_clr.clicked.connect(lambda: self.log_box.clear())
        log_hdr.addWidget(log_lbl)
        log_hdr.addStretch()
        log_hdr.addWidget(btn_clr)
        rlay.addLayout(log_hdr)

        # 分割线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        rlay.addWidget(sep)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("处理日志将在这里实时显示…")
        rlay.addWidget(self.log_box, 1)

        # splitter 包装
        left_wrapper = QWidget()
        lw = QVBoxLayout(left_wrapper)
        lw.setContentsMargins(0, 0, 8, 0)
        lw.addWidget(left_pane)

        right_wrapper = QWidget()
        rw = QVBoxLayout(right_wrapper)
        rw.setContentsMargins(8, 0, 0, 0)
        rw.addWidget(right_pane)

        splitter.addWidget(left_wrapper)
        splitter.addWidget(right_wrapper)
        splitter.setSizes([400, 580])

        root.addWidget(splitter, 1)

    def _add_tpl(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择主图模板",
            filter="PNG 文件 (*.png);;所有文件 (*.*)")
        for f in files:
            if f not in self.templates:
                self.templates.append(f)
                item = QListWidgetItem(f"  🖼  {Path(f).name}")
                item.setToolTip(f)
                self.tpl_list.addItem(item)
        self.c_tpl.set_value(len(self.templates))

    def _del_tpl(self):
        for item in reversed(self.tpl_list.selectedItems()):
            row = self.tpl_list.row(item)
            self.tpl_list.takeItem(row)
            self.templates.pop(row)
        self.c_tpl.set_value(len(self.templates))

    def _log(self, msg: str):
        color = "#48484e"
        for prefix, c in self._LOG_COLORS.items():
            if msg.startswith(prefix):
                color = c
                break
        self.log_box.append(
            f'<span style="color:{color}; font-family: Consolas, monospace;">{msg}</span>')
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_prog(self, cur, total):
        self.prog.setMaximum(total)
        self.prog.setValue(cur)
        self.statusBar().showMessage(f"处理中  [{cur} / {total}]  请稍候…")

    def _on_done(self, ok, fail):
        self.c_ok.set_value(ok)
        self.c_fail.set_value(fail)
        self.btn_start.setEnabled(True)
        self.btn_start.setText("开始批量处理")
        self.prog.setValue(self.prog.maximum())
        self.statusBar().showMessage(
            f"完成  ·  成功 {ok} 张  ·  失败 {fail} 张  ·  输出：{self.row_out.path()}")
        self._log(f"\n🏁  全部完成 — 成功 {ok} 张  失败 {fail} 张")
        if fail == 0:
            QMessageBox.information(
                self, "处理完成",
                f"成功处理 {ok} 张照片\n\n输出目录：\n{self.row_out.path()}")
        else:
            QMessageBox.warning(
                self, "完成（含错误）",
                f"成功 {ok} 张 / 失败 {fail} 张\n\n输出目录：\n{self.row_out.path()}")

    def _start(self):
        inp = self.row_in.path()
        out = self.row_out.path()
        if not inp or not os.path.isdir(inp):
            QMessageBox.warning(self, "错误", "请选择有效的输入文件夹")
            return
        if not out:
            QMessageBox.warning(self, "错误", "请选择输出文件夹")
            return
        if not self.templates:
            if QMessageBox.question(
                    self, "未添加模板",
                    "未添加主图模板，将只生成修正照片（不合成主图）。\n是否继续？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return

        files = [f for f in Path(inp).iterdir()
                 if f.suffix.lower() in SUPPORTED_EXT
                 and not f.name.startswith("主图_")]
        if not files:
            QMessageBox.warning(self, "提示", "输入文件夹中没有找到支持的图片")
            return

        total = len(files)
        self.c_total.set_value(total)
        self.c_ok.set_value("—")
        self.c_fail.set_value("—")
        self.prog.setValue(0)
        self.prog.setMaximum(total)
        self.btn_start.setEnabled(False)
        self.btn_start.setText("处理中…")
        self._log(f"🚀  开始处理  ·  共 {total} 张  ·  输出: {out}")

        self._worker = Worker(inp, out, self.templates,
                              self.chk_dewm.isChecked(),
                              self.chk_enhance.isChecked())
        self._worker.sig_log.connect(self._log)
        self._worker.sig_prog.connect(self._on_prog)
        self._worker.sig_done.connect(self._on_done)
        self._worker.start()


def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "ralo.photo_processor.v2")
        except Exception:
            pass
        # Windows 高 DPI 支持
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Fusion 基底色设为深色，避免部分控件露白
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(20, 20, 22))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(232, 232, 237))
    palette.setColor(QPalette.ColorRole.Base,            QColor(14, 14, 16))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(22, 22, 26))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(28, 28, 32))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(200, 200, 208))
    palette.setColor(QPalette.ColorRole.Text,            QColor(200, 200, 208))
    palette.setColor(QPalette.ColorRole.Button,          QColor(30, 30, 34))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(200, 200, 208))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Link,            QColor(10, 132, 255))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(10, 132, 255))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
