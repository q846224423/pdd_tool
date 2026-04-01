import sys, os, json, ctypes, logging
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QFrame,
    QStatusBar, QMessageBox, QSlider, QListWidget, QListWidgetItem,
    QProgressBar, QScrollArea, QAbstractItemView, QDoubleSpinBox,
    QTabWidget, QSpinBox, QTextEdit, QLineEdit, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QCursor, QColor, QPalette

try:
    from scipy.ndimage import label as scipy_label
    SCIPY_OK = True
except ImportError:
    SCIPY_OK = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
CONFIG_FILE   = Path(__file__).parent / "photo_tool_config.json"

def load_cfg():
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception: pass
    return {}

def save_cfg(d):
    try: CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e: log.warning(f"配置保存失败: {e}")

QSS = """
* { box-sizing: border-box; outline: none; }
QMainWindow { background: #111113; }
QWidget { color: #dddde5; font-family: "Microsoft YaHei UI","PingFang SC",sans-serif; font-size: 13px; background: transparent; }
QWidget#root { background: #111113; }
QWidget#panel { background: #161619; border: 1px solid #24242c; border-radius: 12px; }
QWidget#rpanel { background: #161619; border: 1px solid #24242c; border-radius: 12px; }
QTabWidget::pane { border: none; margin-top: 2px; background: transparent; }
QTabBar::tab { background: #1a1a22; color: #606075; padding: 9px 32px; border-radius: 8px 8px 0 0; margin-right: 3px; font-size: 13px; font-weight: 600; }
QTabBar::tab:selected { background: #22222e; color: #dddde5; }
QTabBar::tab:hover:!selected { background: #1e1e28; color: #9898b8; }
QLabel#sec { color: #505068; font-size: 10px; font-weight: 700; letter-spacing: 2.5px; background: transparent; }
QFrame#div { background: #26263a; border: none; max-height: 1px; }
QLineEdit { background: #1e1e28; border: 1px solid #2c2c3c; border-radius: 7px; padding: 8px 10px; color: #a8a8c0; font-size: 12px; }
QLineEdit:focus { border-color: #2c2c3c; }
QLineEdit[readOnly="true"] { color: #505068; }
QListWidget { background: #1a1a22; border: 1px solid #2c2c3c; border-radius: 8px; color: #b8b8cc; outline: none; padding: 3px; font-size: 12px; }
QListWidget::item { padding: 7px 10px; border-radius: 5px; }
QListWidget::item:selected { background: #0a84ff; color: #fff; }
QListWidget::item:hover:!selected { background: #242434; }
QSlider::groove:horizontal { height: 3px; background: #282838; border-radius: 1px; }
QSlider::handle:horizontal { width: 13px; height: 13px; margin: -5px 0; background: #c0c0d8; border-radius: 7px; }
QSlider::handle:horizontal:hover { background: #fff; }
QSlider::sub-page:horizontal { background: #0a84ff; border-radius: 1px; }
QDoubleSpinBox, QSpinBox { background: #1e1e28; border: 1px solid #2c2c3c; border-radius: 6px; padding: 5px 6px; color: #a8a8c0; font-size: 12px; }
QDoubleSpinBox { min-width: 64px; max-width: 64px; font-family: "Cascadia Code","Consolas",monospace; }
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button, QSpinBox::up-button, QSpinBox::down-button { background: #24242e; border: none; width: 15px; }
QComboBox { background: #1e1e28; border: 1px solid #2c2c3c; border-radius: 7px; padding: 7px 10px; color: #a8a8c0; font-size: 12px; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background: #20202c; border: 1px solid #32323e; color: #c0c0d0; selection-background-color: #0a84ff; outline: none; }
QCheckBox { color: #9090a8; font-size: 12px; spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 4px; border: 1.5px solid #38384a; background: #1e1e28; }
QCheckBox::indicator:checked { background: #0a84ff; border-color: #0a84ff; }
QProgressBar { background: #1a1a22; border: none; border-radius: 2px; height: 4px; color: transparent; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0a84ff,stop:1 #5ac8fa); border-radius: 2px; }
QTextEdit { background: #0e0e16; border: 1px solid #1e1e2a; border-radius: 9px; color: #707080; font-family: "Cascadia Code","Consolas","Courier New",monospace; font-size: 11.5px; padding: 10px; }
QPushButton { background: #24242e; color: #c8c8dc; border-radius: 7px; padding: 8px 14px; font-weight: 600; font-size: 13px; border: none; }
QPushButton:hover { background: #30303e; color: #fff; }
QPushButton:disabled { background: #1a1a22; color: #404050; }
QPushButton#btnPrimary { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #2591ff,stop:1 #0073ea); border: 1px solid #005bb8; border-top: 1px solid #5ab0ff; color: #fff; font-size: 14px; font-weight: 800; padding: 12px 0; border-radius: 9px; }
QPushButton#btnPrimary:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #47a3ff,stop:1 #0a80f5); }
QPushButton#btnPrimary:disabled { background: #1e1e28; border: 1px solid #22222a; color: #404052; }
QPushButton#btnGhost { background: #1e1e2a; color: #8080a0; border: 1px solid #32323e; font-size: 12px; }
QPushButton#btnGhost:hover { background: #28283a; color: #c0c0d8; }
QPushButton#btnGreen { background: rgba(40,196,84,0.13); color: #4ade80; border: 1px solid rgba(40,196,84,0.38); font-size: 12px; font-weight: 600; }
QPushButton#btnGreen:hover { background: rgba(40,196,84,0.24); }
QPushButton#btnRed { background: rgba(240,64,48,0.13); color: #f87171; border: 1px solid rgba(240,64,48,0.38); font-size: 12px; font-weight: 600; }
QPushButton#btnRed:hover { background: rgba(240,64,48,0.24); }
QPushButton#btnClear { background: rgba(255,255,255,0.05); color: #606070; border: 1px solid rgba(255,255,255,0.12); padding: 4px 12px; font-size: 11px; border-radius: 6px; }
QPushButton#btnClear:hover { background: rgba(255,255,255,0.1); color: #c0c0d0; }
QStatusBar { background: #0c0c12; border-top: 1px solid #1a1a22; color: #44445a; font-size: 11px; padding: 2px 14px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 5px; }
QScrollBar::handle:vertical { background: #282838; border-radius: 2px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

# ==============================================================================
# 新增：红框解析与擦除函数
# ==============================================================================
def parse_red_box(img_rgba: Image.Image) -> Tuple[Optional[Tuple[int,int,int,int]], Image.Image]:
    """
    寻找图像中的纯红色矩形框。
    如果找到，返回 (坐标, 擦除红线后的图像)，否则返回 (None, 原图像)
    """
    arr = np.array(img_rgba)
    if arr.shape[2] < 4:
        return None, img_rgba

    # 分离通道，并转为 int 防止溢出
    r = arr[:,:,0].astype(int)
    g = arr[:,:,1].astype(int)
    b = arr[:,:,2].astype(int)
    a = arr[:,:,3].astype(int)

    # 判定规则：R值较高，且明显大于G和B，且非完全透明
    red_mask = (r > 150) & (r > g * 2) & (r > b * 2) & (a > 20)

    if not red_mask.any():
        return None, img_rgba

    ys, xs = np.where(red_mask)
    x1, y1 = int(xs.min()), int(ys.min())
    x2, y2 = int(xs.max()) + 1, int(ys.max()) + 1

    # 核心：将所有被判定为“红线”的像素 Alpha 设为 0（变透明）
    arr[red_mask, 3] = 0
    cleaned_img = Image.fromarray(arr, 'RGBA')

    return (x1, y1, x2, y2), cleaned_img

# ==============================================================================
# 备用：原有透明孔洞识别 (当没有画红框时触发)
# ==============================================================================
def find_main_hole_fallback(tpl_rgba: Image.Image) -> Tuple[int,int,int,int]:
    arr = np.array(tpl_rgba)
    h_img, w_img = arr.shape[:2]

    if arr.shape[2] < 4:
        return 0, 0, w_img, h_img

    alpha = arr[:, :, 3]
    mask = (alpha < 128)

    if not mask.any():
        return 0, 0, w_img, h_img

    if SCIPY_OK:
        labeled, num = scipy_label(mask)
        if num == 0:
            ys, xs = np.where(mask)
            return int(xs.min()), int(ys.min()), int(xs.max())+1, int(ys.max())+1

        sizes = np.bincount(labeled.ravel())
        sizes[0] = 0
        target_label = np.argmax(sizes)
        ys, xs = np.where(labeled == target_label)
        return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1

    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1

def photo_cover_fill(photo: Image.Image, box_w: int, box_h: int) -> Image.Image:
    pw, ph = photo.size
    scale = max(box_w / pw, box_h / ph)
    new_w = max(int(pw * scale), box_w)
    new_h = max(int(ph * scale), box_h)
    resized = photo.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - box_w) // 2
    top  = (new_h - box_h) // 2
    return resized.crop((left, top, left + box_w, top + box_h))

def composite_tab1(bg: Image.Image, frame_rgba: Image.Image, cx: float, cy: float, scale: float) -> Image.Image:
    bw, bh = bg.size
    fw = int(bw * scale)
    fh = int(frame_rgba.height * fw / frame_rgba.width)
    if fw <= 0 or fh <= 0: return bg.convert("RGBA")

    # 1. 优先解析红框，如果存在则直接用它的坐标，并擦除红线
    box, cleaned_frame = parse_red_box(frame_rgba)

    # 用擦除过红线的干净相框进行缩放
    fr = cleaned_frame.resize((fw, fh), Image.LANCZOS)
    left = max(0, min(int(cx*bw - fw/2), bw-fw))
    top  = max(0, min(int(cy*bh - fh/2), bh-fh))

    out = bg.convert("RGBA").copy()

    # 2. 计算最终需要挖孔的坐标
    if box:
        orig_w, orig_h = frame_rgba.size
        x1, y1, x2, y2 = box
        # 将原图红框坐标按比例缩放
        hx1 = int(x1 * fw / orig_w)
        hy1 = int(y1 * fh / orig_h)
        hx2 = int(x2 * fw / orig_w)
        hy2 = int(y2 * fh / orig_h)
    else:
        hx1, hy1, hx2, hy2 = find_main_hole_fallback(fr)

    hole_w = hx2 - hx1
    hole_h = hy2 - hy1
    if hole_w > 0 and hole_h > 0:
        # 只在这个严格指定的区域制造透明
        transparent_hole = Image.new("RGBA", (hole_w, hole_h), (0, 0, 0, 0))
        out.paste(transparent_hole, (left + hx1, top + hy1))

    # 贴上相框。如果是夹层透明，此时背后的 bg 还没被挖空，所以夹层依然是 bg
    out.paste(fr, (left, top), fr)
    return out

def composite_tab2(photo: Image.Image, tpl_path: str, out_w: int, out_h: int, dpi: int, logger=None) -> Image.Image:
    tpl_orig = Image.open(tpl_path)
    if tpl_orig.mode != "RGBA":
        tpl = tpl_orig.convert("RGBA")
    else:
        tpl = tpl_orig.copy()

    tw, th = tpl.size

    # 同样优先检测红框（兼容用户直接在模板里画红框的做法）
    box, cleaned_tpl = parse_red_box(tpl)
    if box:
        x1, y1, x2, y2 = box
        tpl = cleaned_tpl # 使用被擦除红线的干净模板叠加
        if logger: logger("   🎯 检测到人工红色标注框")
    else:
        x1, y1, x2, y2 = find_main_hole_fallback(tpl)

    box_w = x2 - x1
    box_h = y2 - y1

    if box_w <= 0 or box_h <= 0:
        x1, y1, box_w, box_h = 0, 0, tw, th

    filled = photo_cover_fill(photo.convert("RGBA"), box_w, box_h)

    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    canvas.paste(filled, (x1, y1))

    # alpha叠加，因为红线已经被干净地擦掉了，这里也不会现形
    result = Image.alpha_composite(canvas, tpl)
    result = result.resize((out_w, out_h), Image.LANCZOS)
    return result

class FrameBatchWorker(QThread):
    sig_progress = pyqtSignal(int, str)
    sig_done     = pyqtSignal(int)
    sig_error    = pyqtSignal(str)

    def __init__(self, bg_paths, frame_rgba, cx, cy, scale, out_dir):
        super().__init__()
        self.bg_paths, self.frame_rgba = bg_paths, frame_rgba
        self.cx, self.cy, self.scale, self.out_dir = cx, cy, scale, out_dir

    def run(self):
        saved = 0
        for i, path in enumerate(self.bg_paths):
            try:
                bg = Image.open(path).convert("RGB")
                r  = composite_tab1(bg, self.frame_rgba, self.cx, self.cy, self.scale)
                out = str(Path(self.out_dir) / f"{Path(path).stem}_模板.png")
                r.save(out, "PNG")
                saved += 1
                self.sig_progress.emit(i+1, Path(path).name)
            except Exception as e:
                self.sig_error.emit(f"{Path(path).name}: {e}")
        self.sig_done.emit(saved)

class MainBatchWorker(QThread):
    sig_log  = pyqtSignal(str)
    sig_prog = pyqtSignal(int, int)
    sig_done = pyqtSignal(int, int)

    def __init__(self, inp, out, templates, out_w, out_h, dpi, quality, save_png):
        super().__init__()
        self.inp, self.out, self.templates = inp, out, templates
        self.out_w, self.out_h, self.dpi   = out_w, out_h, dpi
        self.quality, self.save_png        = quality, save_png

    def run(self):
        files = [f for f in Path(self.inp).iterdir()
                 if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("主图_")]
        total, ok, fail = len(files), 0, 0
        Path(self.out).mkdir(parents=True, exist_ok=True)

        for i, src in enumerate(files):
            self.sig_log.emit(f"\n── [{i+1}/{total}]  {src.name}")
            try:
                photo = Image.open(src).convert("RGB")
                for tp_str in self.templates:
                    tp   = Path(tp_str)
                    suf  = f"_{tp.stem}" if len(self.templates) > 1 else ""
                    ext  = ".png" if self.save_png else ".jpg"
                    name = f"主图_{src.stem}{suf}{ext}"
                    self.sig_log.emit(f"🖼   {tp.name} → {name}")

                    result = composite_tab2(
                        photo, tp_str, self.out_w, self.out_h, self.dpi,
                        logger=lambda m: self.sig_log.emit(m)
                    )

                    out_path = str(Path(self.out) / name)
                    if self.save_png:
                        result.save(out_path, "PNG")
                    else:
                        result.convert("RGB").save(
                            out_path, "JPEG",
                            quality=self.quality, dpi=(self.dpi, self.dpi))
                    self.sig_log.emit(f"✅  {name}")
                ok += 1
            except Exception as e:
                self.sig_log.emit(f"❌  {e}")
                fail += 1
            self.sig_prog.emit(i+1, total)

        self.sig_done.emit(ok, fail)

def sec(text):
    l = QLabel(text); l.setObjectName("sec"); return l

def div():
    f = QFrame(); f.setObjectName("div"); f.setFrameShape(QFrame.Shape.HLine); return f

class PathRow(QWidget):
    def __init__(self, icon, placeholder, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(8)
        ico = QLabel(icon); ico.setFixedWidth(20)
        ico.setStyleSheet("font-size:15px;background:transparent;color:#606070;")
        self.edit = QLineEdit(); self.edit.setPlaceholderText(placeholder); self.edit.setReadOnly(True)
        btn = QPushButton("浏览"); btn.setObjectName("btnGhost"); btn.setFixedWidth(52)
        btn.clicked.connect(self._browse)
        lay.addWidget(ico); lay.addWidget(self.edit, 1); lay.addWidget(btn)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d: self.edit.setText(d); self.edit.setToolTip(d)

    def path(self): return self.edit.text().strip()
    def set_path(self, p): self.edit.setText(p); self.edit.setToolTip(p)

class PreviewCanvas(QLabel):
    pos_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(380, 280)
        self.setStyleSheet("background:#0e0e16;border-radius:10px;border:1px solid #1e1e2c;")
        self._bg = self._fr = None
        self._cx = 0.5; self._cy = 0.5; self._sc = 0.4
        self._dragging = False; self._dr = (0,0,1,1)
        self._buf = None
        ph = QLabel("请先选相框图和预览背景图", self)
        ph.setStyleSheet("color:#303044;font-size:12px;background:transparent;")
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter); self._ph = ph

    def resizeEvent(self, e):
        self._ph.setGeometry(self.rect()); self._refresh(); super().resizeEvent(e)

    def set_images(self, bg, fr):
        self._bg, self._fr = bg, fr; self._ph.setVisible(bg is None); self._refresh()

    def set_placement(self, cx, cy, sc):
        self._cx, self._cy, self._sc = cx, cy, sc; self._refresh()

    def _refresh(self):
        if self._bg is None: return
        cw, ch = self.width(), self.height()
        if cw < 10 or ch < 10: return
        comp = composite_tab1(self._bg, self._fr, self._cx, self._cy, self._sc) \
            if self._fr else self._bg.convert("RGBA")
        comp.thumbnail((cw, ch), Image.LANCZOS)
        pw, ph = comp.width, comp.height
        self._buf = comp.convert("RGBA").tobytes("raw", "RGBA")
        qi = QImage(self._buf, pw, ph, pw*4, QImage.Format.Format_RGBA8888)
        self.setPixmap(QPixmap.fromImage(qi))
        self._dr = ((cw-pw)//2, (ch-ph)//2, pw, ph)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._bg:
            self._dragging = True; self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def mouseMoveEvent(self, e):
        if not self._dragging or not self._bg: return
        dx, dy, pw, ph = self._dr
        self._cx = max(0.01, min(0.99, (e.position().x()-dx)/pw))
        self._cy = max(0.01, min(0.99, (e.position().y()-dy)/ph))
        self._refresh(); self.pos_changed.emit(self._cx, self._cy)

    def mouseReleaseEvent(self, e):
        self._dragging = False; self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

class FrameTab(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg; self._fr_rgba = None; self._bg_pil = None
        self._batch_paths: List[str] = []; self._worker = None
        self._build(); self._restore()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0, 8, 0, 0); root.setSpacing(10)
        lp = QWidget(); lp.setObjectName("panel"); lp.setFixedWidth(300)
        ll = QVBoxLayout(lp); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        sc_a = QScrollArea(); sc_a.setWidgetResizable(True)
        sc_a.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); sl = QVBoxLayout(inner)
        sl.setContentsMargins(14,14,10,10); sl.setSpacing(0)

        sl.addWidget(sec("相框图  (PNG RGBA)")); sl.addSpacing(8)
        fr_row = QHBoxLayout(); fr_row.setSpacing(8)
        self.lbl_fr = QLabel("未选择")
        self.lbl_fr.setStyleSheet("color:#505068;font-size:11px;background:transparent;")
        self.lbl_fr.setWordWrap(True)
        btn_fr = QPushButton("选择"); btn_fr.setObjectName("btnGhost"); btn_fr.setFixedWidth(52)
        btn_fr.clicked.connect(self._load_fr)
        fr_row.addWidget(self.lbl_fr, 1); fr_row.addWidget(btn_fr)
        sl.addLayout(fr_row); sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        sl.addWidget(sec("预览背景图")); sl.addSpacing(8)
        bg_row = QHBoxLayout(); bg_row.setSpacing(8)
        self.lbl_bg = QLabel("未选择")
        self.lbl_bg.setStyleSheet("color:#505068;font-size:11px;background:transparent;")
        self.lbl_bg.setWordWrap(True)
        btn_bg = QPushButton("选择"); btn_bg.setObjectName("btnGhost"); btn_bg.setFixedWidth(52)
        btn_bg.clicked.connect(self._load_bg)
        bg_row.addWidget(self.lbl_bg, 1); bg_row.addWidget(btn_bg)
        sl.addLayout(bg_row); sl.addSpacing(14)

        def mk_sld_row(label):
            row = QHBoxLayout(); row.setSpacing(8)
            l = QLabel(label); l.setFixedWidth(44)
            l.setStyleSheet("color:#606078;font-size:11.5px;background:transparent;")
            sld = QSlider(Qt.Orientation.Horizontal); sld.setRange(1, 99); sld.setValue(50)
            spn = QDoubleSpinBox(); spn.setRange(0.01,0.99); spn.setDecimals(3)
            spn.setSingleStep(0.005); spn.setValue(0.5)
            row.addWidget(l); row.addWidget(sld, 1); row.addWidget(spn)
            return row, sld, spn

        r1,self.sld_cx,   self.spn_cx    = mk_sld_row("水平")
        r2,self.sld_cy,   self.spn_cy    = mk_sld_row("垂直")
        r3,self.sld_scale,self.spn_scale = mk_sld_row("大小")
        self.sld_scale.setRange(5, 98); self.spn_scale.setRange(0.05, 0.98)
        self.sld_scale.setValue(40); self.spn_scale.setValue(0.40)

        for r in (r1, r2, r3): sl.addLayout(r); sl.addSpacing(5)

        def link(sld, spn, fn):
            sld.valueChanged.connect(lambda v: [
                spn.blockSignals(True), spn.setValue(v/100), spn.blockSignals(False), fn()])
            spn.valueChanged.connect(lambda v: [
                sld.blockSignals(True), sld.setValue(int(round(v*100))), sld.blockSignals(False), fn()])

        link(self.sld_cx,    self.spn_cx,    self._apply)
        link(self.sld_cy,    self.spn_cy,    self._apply)
        link(self.sld_scale, self.spn_scale, self._apply)

        self.lbl_pos = QLabel("—")
        self.lbl_pos.setStyleSheet("color:#303048;font-size:10.5px;background:transparent;")
        sl.addSpacing(4); sl.addWidget(self.lbl_pos)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        sl.addWidget(sec("批量背景图")); sl.addSpacing(8)
        add_row = QHBoxLayout(); add_row.setSpacing(8)
        btn_add = QPushButton("＋ 添加"); btn_add.setObjectName("btnGreen"); btn_add.setFixedHeight(32)
        btn_clr = QPushButton("清空");   btn_clr.setObjectName("btnRed");   btn_clr.setFixedHeight(32); btn_clr.setFixedWidth(100)
        btn_add.clicked.connect(self._add_batch); btn_clr.clicked.connect(self._clear_batch)
        add_row.addWidget(btn_add, 1); add_row.addWidget(btn_clr)
        sl.addLayout(add_row); sl.addSpacing(8)

        self.lst = QListWidget(); self.lst.setFixedHeight(110)
        self.lst.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        sl.addWidget(self.lst)
        self.lbl_count = QLabel("0 张")
        self.lbl_count.setStyleSheet("color:#303048;font-size:10.5px;background:transparent;")
        sl.addSpacing(4); sl.addWidget(self.lbl_count); sl.addStretch()

        sc_a.setWidget(inner); ll.addWidget(sc_a, 1)

        bot = QWidget(); bot.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(bot); bl.setContentsMargins(14,8,14,12); bl.setSpacing(6)
        self.prog = QProgressBar(); self.prog.setFixedHeight(4)
        self.prog.setTextVisible(False); self.prog.setVisible(False)
        self.btn_run = QPushButton("🚀  生成透明模板 PNG")
        self.btn_run.setObjectName("btnPrimary"); self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run)
        bl.addWidget(self.prog); bl.addWidget(self.btn_run)
        ll.addWidget(bot); root.addWidget(lp)

        rp = QWidget(); rl = QVBoxLayout(rp); rl.setContentsMargins(0,0,0,0); rl.setSpacing(6)
        ph = QHBoxLayout()
        plbl = QLabel("PREVIEW"); plbl.setStyleSheet("color:#1e1e2e;font-size:10px;font-weight:700;letter-spacing:2px;background:transparent;")
        self.btn_save_one = QPushButton("💾 保存当前"); self.btn_save_one.setObjectName("btnGhost")
        self.btn_save_one.setEnabled(False); self.btn_save_one.clicked.connect(self._save_one)
        ph.addWidget(plbl); ph.addStretch(); ph.addWidget(self.btn_save_one)
        rl.addLayout(ph)
        self.canvas = PreviewCanvas(); self.canvas.pos_changed.connect(self._on_drag)
        rl.addWidget(self.canvas, 1); root.addWidget(rp, 1)

    def _restore(self):
        c = self._cfg
        if c.get("t1_fr") and Path(c["t1_fr"]).exists():  self._load_fr_path(c["t1_fr"])
        if c.get("t1_bg") and Path(c["t1_bg"]).exists():  self._load_bg_path(c["t1_bg"])
        for sld, spn, key, default in [
            (self.sld_cx,    self.spn_cx,    "t1_cx",    50),
            (self.sld_cy,    self.spn_cy,    "t1_cy",    50),
            (self.sld_scale, self.spn_scale, "t1_scale", 40),
        ]:
            v = int(c.get(key, default))
            sld.blockSignals(True); sld.setValue(v); sld.blockSignals(False)
            spn.blockSignals(True); spn.setValue(v/100); spn.blockSignals(False)
        if c.get("t1_batch"):
            for p in c["t1_batch"]:
                if Path(p).exists() and p not in self._batch_paths:
                    self._batch_paths.append(p); self.lst.addItem(Path(p).name)
            self.lbl_count.setText(f"{len(self._batch_paths)} 张")
        self._refresh_btn()

    def _save_state(self):
        self._cfg.update({
            "t1_cx":    self.sld_cx.value(),
            "t1_cy":    self.sld_cy.value(),
            "t1_scale": self.sld_scale.value(),
            "t1_batch": self._batch_paths,
        }); save_cfg(self._cfg)

    def _load_fr(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择相框图", filter="PNG (*.png);;所有文件 (*.*)")
        if p: self._load_fr_path(p)

    def _load_fr_path(self, p):
        self._fr_rgba = Image.open(p).convert("RGBA")
        self.lbl_fr.setText(Path(p).name)
        self._cfg["t1_fr"] = p; save_cfg(self._cfg)
        self._refresh_btn()
        if self._bg_pil: self.canvas.set_images(self._bg_pil, self._fr_rgba); self._apply()

    def _load_bg(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择预览背景图",
                                           filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        if p: self._load_bg_path(p)

    def _load_bg_path(self, p):
        self._bg_pil = Image.open(p).convert("RGB")
        self.lbl_bg.setText(Path(p).name)
        self._cfg["t1_bg"] = p; save_cfg(self._cfg)
        self.btn_save_one.setEnabled(True)
        self.canvas.set_images(self._bg_pil, self._fr_rgba); self._apply()

    def _apply(self):
        cx = self.sld_cx.value()/100; cy = self.sld_cy.value()/100; sc = self.sld_scale.value()/100
        self.canvas.set_placement(cx, cy, sc)
        self.lbl_pos.setText(f"水平 {cx:.3f}  垂直 {cy:.3f}  大小 {sc:.3f}")
        self._save_state()

    def _on_drag(self, cx, cy):
        for sld, spn, v in [(self.sld_cx,self.spn_cx,int(cx*100)),(self.sld_cy,self.spn_cy,int(cy*100))]:
            sld.blockSignals(True); sld.setValue(v); sld.blockSignals(False)
            spn.blockSignals(True); spn.setValue(v/100); spn.blockSignals(False)
        self._apply()

    def _add_batch(self):
        ps, _ = QFileDialog.getOpenFileNames(self, "添加背景图（可多选）",
                                             filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        for p in ps:
            if p not in self._batch_paths: self._batch_paths.append(p); self.lst.addItem(Path(p).name)
        self.lbl_count.setText(f"{len(self._batch_paths)} 张")
        self._refresh_btn(); self._save_state()

    def _clear_batch(self):
        self._batch_paths.clear(); self.lst.clear(); self.lbl_count.setText("0 张")
        self._refresh_btn(); self._save_state()

    def _refresh_btn(self):
        self.btn_run.setEnabled(self._fr_rgba is not None and len(self._batch_paths) > 0)

    def _run(self):
        out = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if not out: return
        self.btn_run.setEnabled(False); self.prog.setVisible(True)
        self.prog.setMaximum(len(self._batch_paths)); self.prog.setValue(0)
        self._worker = FrameBatchWorker(
            self._batch_paths, self._fr_rgba,
            self.sld_cx.value()/100, self.sld_cy.value()/100, self.sld_scale.value()/100, out)
        self._worker.sig_progress.connect(lambda i,n: (self.prog.setValue(i), self.lst.setCurrentRow(i-1)))
        self._worker.sig_done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, saved):
        self.btn_run.setEnabled(True); self.prog.setVisible(False)
        QMessageBox.information(self, "完成", f"已生成 {saved} 个透明模板 PNG")

    def _save_one(self):
        if not self._bg_pil or not self._fr_rgba: return
        p, _ = QFileDialog.getSaveFileName(self, "保存预览结果", "模板预览.png", "PNG (*.png)")
        if not p: return
        r = composite_tab1(self._bg_pil, self._fr_rgba,
                           self.sld_cx.value()/100, self.sld_cy.value()/100, self.sld_scale.value()/100)
        r.save(p, "PNG")

class MainTab(QWidget):
    _LC = {"✅":"#4ade80","❌":"#f87171","⚠️":"#fbbf24",
           "🚀":"#38bdf8","──":"#303040","🏁":"#c084fc","🖼":"#818cf8"}

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg; self.templates: List[str] = []
        self._worker = None; self._build(); self._restore()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0, 8, 0, 0); root.setSpacing(10)
        lp = QWidget(); lp.setObjectName("panel"); lp.setFixedWidth(300)
        ll = QVBoxLayout(lp); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        sc_a = QScrollArea(); sc_a.setWidgetResizable(True)
        sc_a.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); sl = QVBoxLayout(inner)
        sl.setContentsMargins(14,14,10,10); sl.setSpacing(0)

        sl.addWidget(sec("路  径")); sl.addSpacing(8)
        self.row_in  = PathRow("📂", "输入文件夹（照片）")
        self.row_out = PathRow("💾", "输出文件夹")
        sl.addWidget(self.row_in); sl.addSpacing(6); sl.addWidget(self.row_out)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        sl.addWidget(sec("PNG 透明模板  (Tab1 生成)")); sl.addSpacing(8)
        bt = QHBoxLayout(); bt.setSpacing(8)
        self.btn_add_tpl = QPushButton("＋ 添加"); self.btn_add_tpl.setObjectName("btnGreen"); self.btn_add_tpl.setFixedHeight(32)
        self.btn_del_tpl = QPushButton("－ 删除"); self.btn_del_tpl.setObjectName("btnRed");   self.btn_del_tpl.setFixedHeight(32)
        self.btn_add_tpl.clicked.connect(self._add_tpl); self.btn_del_tpl.clicked.connect(self._del_tpl)
        bt.addWidget(self.btn_add_tpl, 1); bt.addWidget(self.btn_del_tpl, 1)
        sl.addLayout(bt); sl.addSpacing(8)
        self.tpl_list = QListWidget(); self.tpl_list.setFixedHeight(110)
        self.tpl_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        sl.addWidget(self.tpl_list)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        sl.addWidget(sec("输出规格")); sl.addSpacing(8)
        self.cmb = QComboBox()
        for p in ["正方形  800×800","正方形  1000×1000","正方形  1200×1200",
                  "竖版 5:7  1500×2100","横版 7:5  2100×1500","自定义…"]:
            self.cmb.addItem(p)
        self.cmb.currentIndexChanged.connect(self._on_preset)
        self.cmb.wheelEvent = lambda e: e.ignore()
        sl.addWidget(self.cmb); sl.addSpacing(10)

        def mk(lo, hi, val, suf):
            s = QSpinBox(); s.setRange(lo,hi); s.setValue(val); s.setSuffix(suf)
            s.wheelEvent = lambda e: e.ignore(); return s

        self.spn_w   = mk(100, 9999, 800,  " px")
        self.spn_h   = mk(100, 9999, 800,  " px")
        self.spn_dpi = mk(72,  600,  300,  " DPI")
        self.spn_q   = mk(80,  100,  95,   " %")

        def lw(txt, w):
            wr = QWidget(); r = QHBoxLayout(wr); r.setContentsMargins(0,0,0,0); r.setSpacing(6)
            l = QLabel(txt); l.setFixedWidth(28)
            l.setStyleSheet("color:#606070;font-size:11px;background:transparent;")
            r.addWidget(l); r.addWidget(w, 1); return wr

        g1 = QHBoxLayout(); g1.setSpacing(10)
        g2 = QHBoxLayout(); g2.setSpacing(10)
        g1.addWidget(lw("宽",  self.spn_w),   1); g1.addWidget(lw("高", self.spn_h),  1)
        g2.addWidget(lw("DPI", self.spn_dpi), 1); g2.addWidget(lw("品质", self.spn_q),1)
        sl.addLayout(g1); sl.addSpacing(8); sl.addLayout(g2); sl.addSpacing(10)

        self.chk_png = QCheckBox("输出 PNG（保留透明通道）")
        self.chk_png.setStyleSheet("color:#9090a8;font-size:12px;")
        sl.addWidget(self.chk_png); sl.addStretch()

        sc_a.setWidget(inner); ll.addWidget(sc_a, 1)

        bot = QWidget(); bot.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(bot); bl.setContentsMargins(14,8,14,12); bl.setSpacing(6)
        self.prog = QProgressBar(); self.prog.setFixedHeight(4); self.prog.setTextVisible(False)
        self.btn_start = QPushButton("🚀  开始批量合成主图")
        self.btn_start.setObjectName("btnPrimary"); self.btn_start.clicked.connect(self._start)
        bl.addWidget(self.prog); bl.addWidget(self.btn_start)
        ll.addWidget(bot); root.addWidget(lp)

        rp = QWidget(); rp.setObjectName("rpanel")
        rl = QVBoxLayout(rp); rl.setContentsMargins(14,14,14,14); rl.setSpacing(10)
        lh = QHBoxLayout(); lh.addWidget(sec("处 理 日 志")); lh.addStretch()
        bc = QPushButton("清空"); bc.setObjectName("btnClear")
        bc.clicked.connect(lambda: self.log_box.clear()); lh.addWidget(bc)
        rl.addLayout(lh)
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("日志将在这里实时显示…")
        rl.addWidget(self.log_box, 1); root.addWidget(rp, 1)

    def _restore(self):
        c = self._cfg
        if c.get("t2_inp"):  self.row_in.set_path(c["t2_inp"])
        if c.get("t2_out"):  self.row_out.set_path(c["t2_out"])
        if c.get("t2_size"): self.cmb.setCurrentIndex(c["t2_size"])
        if c.get("t2_dpi"):  self.spn_dpi.setValue(c["t2_dpi"])
        if c.get("t2_q"):    self.spn_q.setValue(c["t2_q"])
        if c.get("t2_png"):  self.chk_png.setChecked(c["t2_png"])
        if c.get("t2_tpls"):
            for f in c["t2_tpls"]:
                if Path(f).exists() and f not in self.templates:
                    self.templates.append(f); self.tpl_list.addItem(QListWidgetItem(f"  {Path(f).name}"))

    def _save_state(self):
        self._cfg.update({
            "t2_inp":  self.row_in.path(),
            "t2_out":  self.row_out.path(),
            "t2_size": self.cmb.currentIndex(),
            "t2_dpi":  self.spn_dpi.value(),
            "t2_q":    self.spn_q.value(),
            "t2_png":  self.chk_png.isChecked(),
            "t2_tpls": self.templates,
        }); save_cfg(self._cfg)

    _P = {0:(800,800),1:(1000,1000),2:(1200,1200),3:(1500,2100),4:(2100,1500)}
    def _on_preset(self, idx):
        if idx in self._P:
            w, h = self._P[idx]
            for s, v in [(self.spn_w,w),(self.spn_h,h)]:
                s.blockSignals(True); s.setValue(v); s.blockSignals(False)

    def _add_tpl(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "选择 PNG 模板", filter="PNG (*.png);;所有文件 (*.*)")
        for f in fs:
            if f not in self.templates:
                self.templates.append(f); self.tpl_list.addItem(QListWidgetItem(f"  {Path(f).name}"))
        self._save_state()

    def _del_tpl(self):
        for item in reversed(self.tpl_list.selectedItems()):
            r = self.tpl_list.row(item); self.tpl_list.takeItem(r); self.templates.pop(r)
        self._save_state()

    def _log(self, msg):
        color = "#606072"
        for k, c in self._LC.items():
            if msg.startswith(k): color = c; break
        self.log_box.append(f'<span style="color:{color};font-family:Consolas,monospace;">{msg}</span>')
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _on_prog(self, cur, total): self.prog.setMaximum(total); self.prog.setValue(cur)

    def _on_done(self, ok, fail):
        self.btn_start.setEnabled(True); self.btn_start.setText("🚀  开始批量合成主图")
        self.prog.setValue(self.prog.maximum())
        self._log(f"\n🏁  完成 — 成功 {ok} 张  失败 {fail} 张")
        out = self.row_out.path()
        (QMessageBox.information if fail == 0 else QMessageBox.warning)(
            self, "完成",
            f"成功合成 {ok} 张\n\n输出目录：\n{out}" if fail==0
            else f"成功 {ok}  失败 {fail}\n\n{out}")

    def _start(self):
        inp = self.row_in.path(); out = self.row_out.path()
        if not inp or not os.path.isdir(inp): QMessageBox.warning(self,"提示","请选择输入文件夹"); return
        if not out: QMessageBox.warning(self,"提示","请选择输出文件夹"); return
        if not self.templates: QMessageBox.warning(self,"提示","请添加 PNG 模板"); return
        files = [f for f in Path(inp).iterdir()
                 if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("主图_")]
        if not files: QMessageBox.warning(self,"提示","未找到图片"); return
        n = len(files)
        self.prog.setValue(0); self.prog.setMaximum(n)
        self.btn_start.setEnabled(False); self.btn_start.setText("合成中…")
        self._log(f"🚀  开始  {n} 张 · {len(self.templates)} 个模板")
        self._save_state()
        self._worker = MainBatchWorker(
            inp, out, self.templates,
            self.spn_w.value(), self.spn_h.value(),
            self.spn_dpi.value(), self.spn_q.value(),
            self.chk_png.isChecked())
        self._worker.sig_log.connect(self._log)
        self._worker.sig_prog.connect(self._on_prog)
        self._worker.sig_done.connect(self._on_done)
        self._worker.start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("照片处理工具")
        self.setMinimumSize(900, 620); self.resize(1120, 730)
        self._cfg = load_cfg()
        self._build_ui()
        self.setStyleSheet(QSS)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            "Tab1：调好位置生成透明模板 PNG  →  Tab2：批量填入照片合成主图")

    def _build_ui(self):
        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        rl = QVBoxLayout(root); rl.setContentsMargins(14,12,14,10); rl.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("照片处理工具")
        t.setStyleSheet("color:#dddde8;font-size:16px;font-weight:700;")
        s = QLabel("相框模板生成  ·  主图智能合成")
        s.setStyleSheet("color:#28283a;font-size:11px;")
        hdr.addWidget(t); hdr.addStretch(); hdr.addWidget(s)
        rl.addLayout(hdr)

        ln = QFrame(); ln.setObjectName("div"); ln.setFrameShape(QFrame.Shape.HLine)
        rl.addWidget(ln)

        self.tabs = QTabWidget()
        self.tab1 = FrameTab(self._cfg)
        self.tab2 = MainTab(self._cfg)
        self.tabs.addTab(self.tab1, "  📐  Tab1 · 相框模板生成  ")
        self.tabs.addTab(self.tab2, "  🖼   Tab2 · 主图批量合成  ")
        rl.addWidget(self.tabs, 1)

    def closeEvent(self, e): save_cfg(self._cfg); super().closeEvent(e)

def main():
    if sys.platform == "win32":
        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ralo.photo_tool.v2")
        except: pass
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass
    app = QApplication(sys.argv); app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(17,17,19))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(221,221,229))
    p.setColor(QPalette.ColorRole.Base,            QColor(14,14,18))
    p.setColor(QPalette.ColorRole.Text,            QColor(200,200,212))
    p.setColor(QPalette.ColorRole.Button,          QColor(28,28,34))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(200,200,212))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(10,132,255))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255,255,255))
    app.setPalette(p)
    win = MainWindow(); win.show(); sys.exit(app.exec())

if __name__ == "__main__":
    main()
