"""
智能相框合成工具
────────────────────────────────────────────────────────────────
功能：
  - 加载一张空背景图
  - 加载一张带相框的素材图（自动抠出相框）
  - AI 分析背景，智能决定相框放置位置与大小
  - 合成并预览 / 保存结果

依赖安装：
    pip install PyQt6 pillow opencv-python requests numpy
────────────────────────────────────────────────────────────────
"""

import os, sys, json, base64, logging
from pathlib import Path
from typing  import Optional, Tuple
import io

import requests
import numpy as np
from PIL import Image, ImageFilter

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QFrame, QSplitter,
    QStatusBar, QMessageBox, QSlider, QGroupBox, QCheckBox,
    QSpinBox, QFormLayout, QScrollArea
)
from PyQt6.QtCore  import Qt, QThread, pyqtSignal, QTimer, QRectF, QPointF
from PyQt6.QtGui   import (QPixmap, QPainter, QPen, QColor, QImage,
                           QBrush, QFont, QIcon, QCursor)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

API_KEY = "sk-46X32UEI0hNcKczjbwivYhrlvJgwQjOwCXQ7jZxut7oscoSo"
API_URL = "https://api.moonshot.cn/v1/chat/completions"
MODEL   = "moonshot-v1-8k-vision-preview"

# ─────────────────────────────────────────────────────────────
# macOS Dark 样式表
# ─────────────────────────────────────────────────────────────
QSS = """
QMainWindow, QWidget {
    background-color: #1c1c1e;
    color: #f5f5f7;
    font-family: "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}
QGroupBox {
    background-color: #2c2c2e;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    margin-top: 22px;
    padding: 14px 12px 12px 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px; padding: 0 5px;
    color: #636366; font-size: 10px;
    font-weight: 600; letter-spacing: 1.8px;
}
QLineEdit {
    background-color: #3a3a3c;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px; padding: 7px 11px; color: #f5f5f7;
}
QLineEdit:focus { border: 1.5px solid #0a84ff; }

QPushButton {
    border-radius: 8px; padding: 7px 16px;
    font-weight: 500; font-size: 13px; border: none;
}
QPushButton#btnMain {
    background-color: #0a84ff; color: #fff;
    font-size: 13px; font-weight: 600;
    padding: 10px 0; border-radius: 10px;
}
QPushButton#btnMain:hover   { background-color: #409cff; }
QPushButton#btnMain:pressed { background-color: #0060df; }
QPushButton#btnMain:disabled{ background-color: #3a3a3c; color: #636366; }

QPushButton#btnPick {
    background-color: #3a3a3c; color: #aeaeb2;
    border: 1px solid rgba(255,255,255,0.07);
    padding: 7px 14px; font-size: 12px;
}
QPushButton#btnPick:hover { background-color: #48484a; color: #f5f5f7; }

QPushButton#btnSave {
    background-color: rgba(48,209,88,0.13);
    color: #30d158;
    border: 1px solid rgba(48,209,88,0.24);
    font-size: 12px; font-weight: 500;
}
QPushButton#btnSave:hover { background-color: rgba(48,209,88,0.22); }
QPushButton#btnSave:disabled { background-color: #2c2c2e; color: #48484a;
    border-color: rgba(255,255,255,0.05); }

QPushButton#btnReset {
    background-color: rgba(255,69,58,0.12);
    color: #ff453a;
    border: 1px solid rgba(255,69,58,0.22);
    font-size: 12px; font-weight: 500;
}
QPushButton#btnReset:hover { background-color: rgba(255,69,58,0.22); }

QSlider::groove:horizontal {
    height: 4px; background: #3a3a3c; border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 16px; height: 16px; margin: -6px 0;
    background: #f5f5f7; border-radius: 8px;
    border: 2px solid #0a84ff;
}
QSlider::sub-page:horizontal { background: #0a84ff; border-radius: 2px; }

QSpinBox {
    background-color: #3a3a3c;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 7px; padding: 4px 8px; color: #f5f5f7;
}
QSpinBox:focus { border-color: #0a84ff; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #48484a; border: none; width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #636366; }

QCheckBox { spacing: 8px; color: #e5e5ea; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 1.5px solid #48484a; background: #3a3a3c;
}
QCheckBox::indicator:checked { background: #0a84ff; border-color: #0a84ff; }

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.16);
    border-radius: 4px; min-height: 28px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.28); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QFrame[frameShape="4"], QFrame[frameShape="5"] {
    background: rgba(255,255,255,0.07); border: none; max-height: 1px;
}
QStatusBar {
    background: #1c1c1e; border-top: 1px solid rgba(255,255,255,0.06);
    color: #48484a; font-size: 11px; padding: 2px 14px;
}
QLabel#hint { color: #48484a; font-size: 10.5px; }
QSplitter::handle { background: rgba(255,255,255,0.05); }
"""


# ─────────────────────────────────────────────────────────────
# AI 核心：分析背景 → 返回放置建议
# ─────────────────────────────────────────────────────────────

def pil_to_b64(img: Image.Image, max_side=768) -> str:
    """缩小后转 base64，节省 token"""
    img = img.copy()
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def ai_suggest_placement(bg: Image.Image, frame: Image.Image) -> dict:
    """
    让 AI 分析背景图，给出相框的最佳放置坐标和缩放比例。
    返回：{"cx": 0.5, "cy": 0.5, "scale": 0.4, "reason": "..."}
    cx/cy 为相对坐标（0~1），scale 为相对于背景宽度的相框宽度比例。
    """
    b64_bg    = pil_to_b64(bg)
    b64_frame = pil_to_b64(frame)

    prompt = (
        "我有两张图：第一张是背景图，第二张是带相框的素材图。\n"
        "请分析背景图的构图、留白区域、视觉重心，"
        "决定把相框放在背景图的哪个位置最合适、最美观。\n\n"
        "要求：\n"
        "1. cx、cy 是相框中心点在背景图中的相对坐标（0.0~1.0）\n"
        "2. scale 是相框宽度应占背景图宽度的比例（0.1~0.95），要让相框适当大\n"
        "3. 相框不要超出背景边界\n"
        "4. 如背景有明显留白区域，优先放那里\n\n"
        "只返回 JSON，格式：\n"
        '{"cx": 0.5, "cy": 0.5, "scale": 0.4, "reason": "一句话说明"}\n'
        "不要其他任何文字。"
    )

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_bg}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_frame}"}},
            {"type": "text", "text": prompt}
        ]}],
        "max_tokens": 256
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    r = requests.post(API_URL, json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]
    log.info(f"AI 原始回复: {raw}")

    s, e = raw.find("{"), raw.rfind("}") + 1
    data = json.loads(raw[s:e])
    # 安全夹紧
    data["cx"]    = max(0.05, min(0.95, float(data.get("cx",    0.5))))
    data["cy"]    = max(0.05, min(0.95, float(data.get("cy",    0.5))))
    data["scale"] = max(0.10, min(0.95, float(data.get("scale", 0.4))))
    return data


# ─────────────────────────────────────────────────────────────
# 图像处理：抠出相框 → 合成
# ─────────────────────────────────────────────────────────────

def extract_frame(frame_img: Image.Image) -> Image.Image:
    """
    将相框图转为 RGBA：
    - 若已有透明通道，直接用
    - 否则用颜色/背景检测尝试去除纯色背景
    """
    if frame_img.mode == "RGBA":
        return frame_img

    rgba = frame_img.convert("RGBA")
    arr  = np.array(rgba)

    # 取四角采样背景色（支持白/黑/灰等纯色背景）
    corners = [arr[0,0,:3], arr[0,-1,:3], arr[-1,0,:3], arr[-1,-1,:3]]
    bg_color = np.mean(corners, axis=0).astype(np.uint8)

    # 与背景色相近的像素设为透明（阈值 30）
    diff  = np.abs(arr[:,:,:3].astype(int) - bg_color.astype(int))
    mask  = np.all(diff < 30, axis=2)
    arr[mask, 3] = 0

    return Image.fromarray(arr, "RGBA")


def composite(bg: Image.Image, frame_rgba: Image.Image,
              cx: float, cy: float, scale: float) -> Image.Image:
    """
    将相框合成到背景图指定位置。
    cx, cy: 相框中心相对坐标（0~1）
    scale:  相框宽度 / 背景宽度
    """
    bw, bh = bg.size
    fw_new = int(bw * scale)
    fh_new = int(frame_rgba.height * fw_new / frame_rgba.width)
    frame_resized = frame_rgba.resize((fw_new, fh_new), Image.LANCZOS)

    # 计算左上角坐标，确保不超出边界
    left = int(cx * bw - fw_new / 2)
    top  = int(cy * bh - fh_new / 2)
    left = max(0, min(left, bw - fw_new))
    top  = max(0, min(top,  bh - fh_new))

    result = bg.convert("RGBA").copy()
    result.paste(frame_resized, (left, top), frame_resized)
    return result.convert("RGB")


# ─────────────────────────────────────────────────────────────
# 后台工作线程
# ─────────────────────────────────────────────────────────────

class AiWorker(QThread):
    sig_done  = pyqtSignal(dict)   # AI 建议结果
    sig_error = pyqtSignal(str)

    def __init__(self, bg: Image.Image, frame: Image.Image):
        super().__init__()
        self.bg, self.frame = bg, frame

    def run(self):
        try:
            result = ai_suggest_placement(self.bg, self.frame)
            self.sig_done.emit(result)
        except Exception as e:
            self.sig_error.emit(str(e))


# ─────────────────────────────────────────────────────────────
# 可拖拽预览控件
# ─────────────────────────────────────────────────────────────

class PreviewCanvas(QLabel):
    """
    显示合成预览，支持：
    - 鼠标拖动相框位置
    - 发出位置变更信号
    """
    pos_changed = pyqtSignal(float, float)   # cx, cy (相对坐标)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setStyleSheet(
            "background:#161618; border-radius:12px;"
            "border:1px solid rgba(255,255,255,0.07);")
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        self._bg_pil:    Optional[Image.Image] = None
        self._frame_pil: Optional[Image.Image] = None
        self._cx = 0.5;  self._cy = 0.5
        self._scale = 0.4
        self._dragging = False
        self._drag_start = QPointF()

        # 空状态提示
        self._placeholder = QLabel("← 请先加载背景图和相框图", self)
        self._placeholder.setStyleSheet(
            "color:#48484a; font-size:13px; background:transparent;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def resizeEvent(self, e):
        self._placeholder.setGeometry(self.rect())
        self._refresh()
        super().resizeEvent(e)

    def set_images(self, bg: Optional[Image.Image],
                   frame: Optional[Image.Image]):
        self._bg_pil    = bg
        self._frame_pil = frame
        self._placeholder.setVisible(bg is None)
        self._refresh()

    def set_placement(self, cx: float, cy: float, scale: float):
        self._cx, self._cy, self._scale = cx, cy, scale
        self._refresh()

    def get_placement(self) -> Tuple[float, float, float]:
        return self._cx, self._cy, self._scale

    def _refresh(self):
        if self._bg_pil is None:
            self.clear()
            return
        if self._frame_pil is None:
            # 只显示背景
            comp = self._bg_pil.copy()
        else:
            comp = composite(self._bg_pil, self._frame_pil,
                             self._cx, self._cy, self._scale)

        # 缩放到控件大小
        cw, ch = self.width(), self.height()
        if cw < 10 or ch < 10:
            return
        comp.thumbnail((cw, ch), Image.LANCZOS)
        data = comp.convert("RGB").tobytes("raw", "RGB")
        qimg = QImage(data, comp.width, comp.height,
                      comp.width * 3, QImage.Format.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(qimg))

        # 记录实际显示区域（居中）
        pw, ph = comp.width, comp.height
        self._display_rect = (
            (cw - pw) // 2, (ch - ph) // 2, pw, ph
        )

    # ── 拖拽 ──────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._bg_pil:
            self._dragging = True
            self._drag_start = e.position()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def mouseMoveEvent(self, e):
        if not self._dragging or self._bg_pil is None:
            return
        if not hasattr(self, "_display_rect"):
            return
        dx, dy, pw, ph = self._display_rect
        # 鼠标相对显示区域的相对坐标
        mx = (e.position().x() - dx) / pw
        my = (e.position().y() - dy) / ph
        self._cx = max(0.02, min(0.98, mx))
        self._cy = max(0.02, min(0.98, my))
        self._refresh()
        self.pos_changed.emit(self._cx, self._cy)

    def mouseReleaseEvent(self, e):
        self._dragging = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))


# ─────────────────────────────────────────────────────────────
# 主窗口
# ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能相框合成工具")
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)

        self._bg_pil:    Optional[Image.Image] = None
        self._frame_pil: Optional[Image.Image] = None   # 原始（未抠图）
        self._frame_rgba: Optional[Image.Image] = None  # 抠图后 RGBA
        self._result:    Optional[Image.Image] = None
        self._ai_worker: Optional[AiWorker] = None
        self._ai_reason  = ""

        self._build_ui()
        self.setStyleSheet(QSS)
        self.setStatusBar(QStatusBar())
        self._status("就绪  ·  请加载背景图和相框图")

    # ── UI 构建 ───────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 10)
        root.setSpacing(12)

        # ── 顶栏 ──────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("智能相框合成工具")
        title.setStyleSheet(
            "color:#f5f5f7; font-size:18px; font-weight:700;"
            "background:transparent;")
        sub = QLabel("by Ralo  ·  Moonshot Vision")
        sub.setStyleSheet("color:#48484a; font-size:11px; background:transparent;")
        hdr.addWidget(title); hdr.addStretch(); hdr.addWidget(sub)
        root.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── 主体 Splitter ─────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # ─── 左控制面板 ───────────────────────────────────────
        left = QWidget(); left.setFixedWidth(290)
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 14, 0)
        llay.setSpacing(10)

        # 图片加载
        grp_load = QGroupBox("图片加载")
        gl = QVBoxLayout(grp_load); gl.setSpacing(10)

        # 背景图行
        bg_row = QHBoxLayout()
        self.lbl_bg = QLabel("未选择")
        self.lbl_bg.setStyleSheet("color:#8e8e93; font-size:11px;")
        self.lbl_bg.setWordWrap(True)
        btn_bg = QPushButton("选择背景图"); btn_bg.setObjectName("btnPick")
        btn_bg.clicked.connect(self._load_bg)
        gl.addWidget(QLabel("🖼  背景图"))
        bg_row.addWidget(self.lbl_bg, 1); bg_row.addWidget(btn_bg)
        gl.addLayout(bg_row)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        gl.addWidget(sep2)

        # 相框图行
        fr_row = QHBoxLayout()
        self.lbl_fr = QLabel("未选择")
        self.lbl_fr.setStyleSheet("color:#8e8e93; font-size:11px;")
        self.lbl_fr.setWordWrap(True)
        btn_fr = QPushButton("选择相框图"); btn_fr.setObjectName("btnPick")
        btn_fr.clicked.connect(self._load_frame)
        gl.addWidget(QLabel("🪟  相框图"))
        fr_row.addWidget(self.lbl_fr, 1); fr_row.addWidget(btn_fr)
        gl.addLayout(fr_row)

        llay.addWidget(grp_load)

        # AI 分析
        grp_ai = QGroupBox("AI 智能定位")
        ga = QVBoxLayout(grp_ai); ga.setSpacing(8)
        self.btn_ai = QPushButton("🤖  AI 分析最佳位置")
        self.btn_ai.setObjectName("btnMain")
        self.btn_ai.setEnabled(False)
        self.btn_ai.clicked.connect(self._run_ai)
        ga.addWidget(self.btn_ai)
        self.lbl_reason = QLabel("")
        self.lbl_reason.setObjectName("hint")
        self.lbl_reason.setWordWrap(True)
        ga.addWidget(self.lbl_reason)
        llay.addWidget(grp_ai)

        # 手动微调
        grp_adj = QGroupBox("手动微调")
        gadj = QVBoxLayout(grp_adj); gadj.setSpacing(10)

        form = QFormLayout(); form.setSpacing(8)

        # 水平位置
        self.sld_cx = QSlider(Qt.Orientation.Horizontal)
        self.sld_cx.setRange(1, 99); self.sld_cx.setValue(50)
        self.sld_cx.valueChanged.connect(self._on_cx)
        form.addRow("水平位置", self.sld_cx)

        # 垂直位置
        self.sld_cy = QSlider(Qt.Orientation.Horizontal)
        self.sld_cy.setRange(1, 99); self.sld_cy.setValue(50)
        self.sld_cy.valueChanged.connect(self._on_cy)
        form.addRow("垂直位置", self.sld_cy)

        # 大小
        self.sld_scale = QSlider(Qt.Orientation.Horizontal)
        self.sld_scale.setRange(10, 95); self.sld_scale.setValue(40)
        self.sld_scale.valueChanged.connect(self._on_scale)
        form.addRow("相框大小", self.sld_scale)

        gadj.addLayout(form)

        hint_drag = QLabel("💡 也可以在预览图上直接拖动相框")
        hint_drag.setObjectName("hint")
        hint_drag.setWordWrap(True)
        gadj.addWidget(hint_drag)

        llay.addWidget(grp_adj)

        llay.addStretch()

        # 保存 / 重置
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        self.btn_save  = QPushButton("💾  保存结果"); self.btn_save.setObjectName("btnSave")
        self.btn_reset = QPushButton("↺  重置");     self.btn_reset.setObjectName("btnReset")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save)
        self.btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(self.btn_save, 2)
        btn_row.addWidget(self.btn_reset, 1)
        llay.addLayout(btn_row)

        splitter.addWidget(left)

        # ─── 右预览区 ─────────────────────────────────────────
        right = QWidget()
        rlay  = QVBoxLayout(right)
        rlay.setContentsMargins(14, 0, 0, 0)
        rlay.setSpacing(6)

        preview_lbl = QLabel("PREVIEW")
        preview_lbl.setStyleSheet(
            "color:#48484a; font-size:10px; font-weight:600; letter-spacing:2px;")
        rlay.addWidget(preview_lbl)

        self.canvas = PreviewCanvas()
        self.canvas.pos_changed.connect(self._on_canvas_drag)
        rlay.addWidget(self.canvas, 1)

        splitter.addWidget(right)
        splitter.setSizes([290, 800])
        root.addWidget(splitter, 1)

    # ── 辅助 ─────────────────────────────────────────────────
    def _status(self, msg: str):
        self.statusBar().showMessage(msg)

    def _check_ready(self):
        ready = self._bg_pil is not None and self._frame_rgba is not None
        self.btn_ai.setEnabled(ready)
        self.btn_save.setEnabled(ready)
        if ready:
            self.canvas.set_images(self._bg_pil, self._frame_rgba)
            self._apply_placement()

    def _apply_placement(self, cx=None, cy=None, scale=None):
        if cx    is None: cx    = self.sld_cx.value()    / 100
        if cy    is None: cy    = self.sld_cy.value()    / 100
        if scale is None: scale = self.sld_scale.value() / 100
        self.canvas.set_placement(cx, cy, scale)
        # 生成结果图
        if self._bg_pil and self._frame_rgba:
            self._result = composite(self._bg_pil, self._frame_rgba,
                                     cx, cy, scale)

    # ── 加载图片 ──────────────────────────────────────────────
    def _load_bg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图",
            filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        if not path: return
        self._bg_pil = Image.open(path).convert("RGB")
        self.lbl_bg.setText(Path(path).name)
        self._status(f"背景图已加载：{Path(path).name}  "
                     f"({self._bg_pil.width}×{self._bg_pil.height})")
        self._check_ready()

    def _load_frame(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择相框图",
            filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        if not path: return
        self._frame_pil  = Image.open(path)
        self._frame_rgba = extract_frame(self._frame_pil)
        self.lbl_fr.setText(Path(path).name)
        self._status(f"相框图已加载：{Path(path).name}  （已自动抠出透明通道）")
        self._check_ready()

    # ── AI 分析 ───────────────────────────────────────────────
    def _run_ai(self):
        if self._bg_pil is None or self._frame_rgba is None:
            return
        self.btn_ai.setEnabled(False)
        self.btn_ai.setText("⏳  AI 分析中…")
        self.lbl_reason.setText("")
        self._status("正在调用 Moonshot Vision 分析构图…")

        self._ai_worker = AiWorker(self._bg_pil, self._frame_pil or self._frame_rgba)
        self._ai_worker.sig_done.connect(self._on_ai_done)
        self._ai_worker.sig_error.connect(self._on_ai_error)
        self._ai_worker.start()

    def _on_ai_done(self, data: dict):
        cx    = data["cx"]
        cy    = data["cy"]
        scale = data["scale"]
        reason = data.get("reason", "")

        # 同步滑块（阻断信号避免递归）
        for sld, val in [
            (self.sld_cx,    int(cx    * 100)),
            (self.sld_cy,    int(cy    * 100)),
            (self.sld_scale, int(scale * 100)),
        ]:
            sld.blockSignals(True)
            sld.setValue(val)
            sld.blockSignals(False)

        self._apply_placement(cx, cy, scale)
        self.lbl_reason.setText(f"💡 {reason}")
        self.btn_ai.setEnabled(True)
        self.btn_ai.setText("🤖  AI 分析最佳位置")
        self._status(f"AI 定位完成  ·  {reason}")

    def _on_ai_error(self, err: str):
        self.btn_ai.setEnabled(True)
        self.btn_ai.setText("🤖  AI 分析最佳位置")
        self._status(f"AI 分析失败: {err}")
        QMessageBox.warning(self, "AI 错误", f"调用失败：\n{err}")

    # ── 滑块 / 拖拽回调 ───────────────────────────────────────
    def _on_cx(self, v):    self._apply_placement(cx=v/100)
    def _on_cy(self, v):    self._apply_placement(cy=v/100)
    def _on_scale(self, v): self._apply_placement(scale=v/100)

    def _on_canvas_drag(self, cx: float, cy: float):
        for sld, val in [(self.sld_cx, int(cx*100)), (self.sld_cy, int(cy*100))]:
            sld.blockSignals(True)
            sld.setValue(val)
            sld.blockSignals(False)
        scale = self.sld_scale.value() / 100
        self._apply_placement(cx, cy, scale)

    # ── 保存 / 重置 ───────────────────────────────────────────
    def _save(self):
        if self._result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存合成结果",
            "合成结果.jpg",
            "JPEG (*.jpg);;PNG (*.png);;所有文件 (*.*)")
        if not path: return
        fmt = "PNG" if path.lower().endswith(".png") else "JPEG"
        self._result.save(path, format=fmt, quality=95, dpi=(300,300))
        self._status(f"✅  已保存：{path}")
        QMessageBox.information(self, "保存成功", f"文件已保存：\n{path}")

    def _reset(self):
        self._bg_pil = self._frame_pil = self._frame_rgba = self._result = None
        self.lbl_bg.setText("未选择")
        self.lbl_fr.setText("未选择")
        self.lbl_reason.setText("")
        self.sld_cx.setValue(50)
        self.sld_cy.setValue(50)
        self.sld_scale.setValue(40)
        self.btn_ai.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.canvas.set_images(None, None)
        self._status("已重置")
 

# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────

def main():
    import ctypes
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "ralo.frame_composer.v1")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()