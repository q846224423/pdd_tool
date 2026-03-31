"""
照片处理工具 — 纯净透明通道·矩形精准填满版
════════════════════════════════════════════════════════════════
Tab 1：相框背景合成 (精准凿穿背景中心，生成 PNG 模板)
Tab 2：主图智能合成 (Cover模式消除留白，全透明底板保留图层细节)

需安装：pip install PyQt6 pillow numpy scipy
════════════════════════════════════════════════════════════════
"""

import sys, os, json, ctypes, logging
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QFrame,
    QStatusBar, QMessageBox, QSlider, QListWidget, QListWidgetItem,
    QProgressBar, QScrollArea, QAbstractItemView, QDoubleSpinBox,
    QTabWidget, QSpinBox, QTextEdit, QLineEdit, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QCursor, QColor, QPalette

# 导入 scipy 进行连通域精准分析
try:
    from scipy.ndimage import label
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
CONFIG_FILE = Path(__file__).parent / "photo_tool_config.json"

# ══════════════════════════════════════════════════════════════
# UI 辅助工具函数
# ══════════════════════════════════════════════════════════════
def sec(text):
    l = QLabel(text)
    l.setObjectName("sec")
    return l

def div():
    f = QFrame()
    f.setObjectName("div")
    f.setFrameShape(QFrame.Shape.HLine)
    return f

def load_cfg() -> dict:
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception: pass
    return {}

def save_cfg(d: dict):
    try: CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e: log.warning(f"配置保存失败: {e}")

# ══════════════════════════════════════════════════════════════
# 样式表
# ══════════════════════════════════════════════════════════════
QSS = """
* { box-sizing: border-box; outline: none; }
QMainWindow { background: #111113; }
QWidget { color: #dddde5; font-family: "Microsoft YaHei UI",sans-serif; font-size: 13px; background: transparent; }
QTabWidget::pane { border: none; margin-top: 2px; }
QTabBar::tab { background: #1a1a22; color: #606075; padding: 9px 28px; border-radius: 8px 8px 0 0; margin-right: 3px; }
QTabBar::tab:selected { background: #22222e; color: #dddde5; }
QWidget#panel { background: #161619; border: 1px solid #24242c; border-radius: 12px; }
QLabel#sec { color: #505068; font-size: 10px; font-weight: 700; letter-spacing: 2.5px; }
QFrame#div { background: #26263a; max-height: 1px; }
QLineEdit, QSpinBox, QDoubleSpinBox { background: #1e1e28; border: 1px solid #2c2c3c; border-radius: 7px; padding: 7px; color: #a8a8c0; }
QListWidget { background: #1a1a22; border: 1px solid #2c2c3c; border-radius: 8px; color: #b8b8cc; }
QProgressBar { background: #1a1a22; border-radius: 2px; height: 4px; color: transparent; }
QProgressBar::chunk { background: #0a84ff; border-radius: 2px; }
QTextEdit { background: #0e0e16; border: 1px solid #1e1e2a; border-radius: 9px; color: #707080; font-family: Consolas, monospace; }
QPushButton { background: #24242e; color: #c8c8dc; border-radius: 7px; padding: 8px 14px; font-weight: 600; }
QPushButton:hover { background: #30303e; color: #fff; }
QPushButton#btnPrimary { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #2591ff,stop:1 #0073ea); color: #fff; }
QPushButton#btnGhost { background: #1e1e2a; color: #8080a0; border: 1px solid #32323e; }
QPushButton#btnGreen { background: rgba(40,196,84,0.13); color: #4ade80; }
QPushButton#btnRed { background: rgba(240,64,48,0.13); color: #f87171; }
"""

# ══════════════════════════════════════════════════════════════
# Tab 1 专用：凿穿合成逻辑
# ══════════════════════════════════════════════════════════════
def frame_composite_with_punch(bg: Image.Image, frame_rgba: Image.Image, cx: float, cy: float, scale: float) -> Image.Image:
    bw, bh = bg.size
    fw = int(bw * scale)
    fh = int(frame_rgba.height * fw / frame_rgba.width)
    if fw <= 0 or fh <= 0: return bg.convert("RGBA")

    fr_resized = frame_rgba.resize((fw, fh), Image.LANCZOS)
    left = max(0, min(int(cx*bw - fw/2), bw-fw))
    top  = max(0, min(int(cy*bh - fh/2), bh-fh))

    out = bg.convert("RGBA").copy()
    fr_alpha = fr_resized.getchannel("A")
    full_mask = Image.new("L", (bw, bh), 255)
    full_mask.paste(fr_alpha, (left, top))

    out.paste(fr_resized, (left, top), fr_resized)
    out.putalpha(full_mask)
    return out

# ══════════════════════════════════════════════════════════════
# Tab 2 专用：实心矩形孔洞精准识别算法
# ══════════════════════════════════════════════════════════════
def extract_transparent_region(tpl_rgba: Image.Image, logger_callback=None) -> Optional[Tuple[int, int, int, int]]:
    arr = np.array(tpl_rgba)
    if arr.shape[2] < 4: return None
    alpha = arr[:, :, 3]

    transparent_mask = (alpha == 0)
    if not np.any(transparent_mask):
        if logger_callback: logger_callback(f"   ⚠️ 未检测到透明区域")
        return None

    if SCIPY_AVAILABLE:
        labeled, num = label(transparent_mask)
        sizes = np.bincount(labeled.ravel())
        sizes[0] = 0

        regions = []
        w, h = tpl_rgba.size
        for lid in range(1, num + 1):
            region = (labeled == lid)
            rows = np.any(region, axis=1)
            cols = np.any(region, axis=0)
            if not rows.any() or not cols.any(): continue

            y1, y2 = np.where(rows)[0][[0, -1]]
            x1, x2 = np.where(cols)[0][[0, -1]]

            # 计算实心密度：实际透明像素 / 外接矩形面积
            bbox_area = (x2 - x1 + 1) * (y2 - y1 + 1)
            actual_area = sizes[lid]
            density = actual_area / bbox_area if bbox_area > 0 else 0

            # 记录中心距离（用于多孔洞时优先选中间的）
            dist = np.sqrt(((x1+x2)/2 - w/2)**2 + ((y1+y2)/2 - h/2)**2)

            # 筛选：实心度 > 0.85 且面积适中（排除线条和背景）
            if density > 0.85 and actual_area > (w * h * 0.01):
                regions.append({'box': (x1, y1, x2, y2), 'dist': dist, 'density': density})

        if not regions:
            if logger_callback: logger_callback("   ⚠️ 未锁定实心填充位，使用默认最大透明区")
            largest_label = np.argmax(sizes)
            region = (labeled == largest_label)
            rows, cols = np.any(region, axis=1), np.any(region, axis=0)
            return (np.where(cols)[0][0], np.where(rows)[0][0], np.where(cols)[0][-1], np.where(rows)[0][-1])

        # 取最靠近中心的实心块
        best = min(regions, key=lambda x: x['dist'])
        x1, y1, x2, y2 = best['box']
        if logger_callback:
            logger_callback(f"   🎯 精准识别孔洞: ({x1},{y1})->({x2},{y2}) 实心度:{best['density']:.2f}")
        return (x1, y1, x2, y2)
    else:
        rows, cols = np.any(transparent_mask, axis=1), np.any(transparent_mask, axis=0)
        return (np.where(cols)[0][0], np.where(rows)[0][0], np.where(cols)[0][-1], np.where(rows)[0][-1])


# ================== 仅展示关键修改处（完整工程你已给出） ==================

def main_composite(photo: Image.Image, tpl_path: str, out_w: int, out_h: int, dpi: int,
                   fill_mode: str = 'contain', logger_callback=None) -> Image.Image:
    tpl_rgba = Image.open(tpl_path).convert("RGBA")
    tw, th = tpl_rgba.size

    coords = extract_transparent_region(tpl_rgba, logger_callback)
    x1, y1, x2, y2 = coords if coords else (0, 0, tw, th)

    hw, hh = x2 - x1 + 1, y2 - y1 + 1
    p = photo.convert("RGBA")
    pw, ph = p.size

    # --- Cover 填充 ---
    if fill_mode == 'stretch':
        p_final = p.resize((hw, hh), Image.LANCZOS)
    else:
        sc = max(hw / pw, hh / ph)
        nw, nh = int(pw * sc), int(ph * sc)
        p_resized = p.resize((nw, nh), Image.LANCZOS)
        lc, tc = (nw - hw) // 2, (nh - hh) // 2
        p_final = p_resized.crop((lc, tc, lc + hw, tc + hh))

    # ✅ 关键：透明底
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    canvas.paste(p_final, (x1, y1))

    # 叠加模板（保留透明）
    out = Image.alpha_composite(canvas, tpl_rgba)

    # ✅ 关键：不再 convert RGB
    return out.resize((out_w, out_h), Image.LANCZOS)


# ================== 保存部分（第二个关键修改） ==================




# ══════════════════════════════════════════════════════════════
# 后台工作线程
# ══════════════════════════════════════════════════════════════
class FrameBatchWorker(QThread):
    sig_progress = pyqtSignal(int, str); sig_done = pyqtSignal(int)
    def __init__(self, bg_paths, frame_rgba, cx, cy, scale, out_dir):
        super().__init__(); self.bg_paths, self.frame_rgba = bg_paths, frame_rgba
        self.cx, self.cy, self.scale, self.out_dir = cx, cy, scale, out_dir
    def run(self):
        saved = 0
        for i, path in enumerate(self.bg_paths):
            try:
                bg = Image.open(path).convert("RGB")
                r = frame_composite_with_punch(bg, self.frame_rgba, self.cx, self.cy, self.scale)
                out = str(Path(self.out_dir) / f"{Path(path).stem}_透明模板.png")
                r.save(out, "PNG"); saved += 1
                self.sig_progress.emit(i+1, Path(path).name)
            except Exception: pass
        self.sig_done.emit(saved)

class MainBatchWorker(QThread):
    sig_log = pyqtSignal(str)
    sig_prog = pyqtSignal(int, int)
    sig_done = pyqtSignal(int, int)

    def __init__(self, inp, out, templates, out_w, out_h, dpi, quality, fill_mode):
        super().__init__()
        self.inp, self.out, self.templates = inp, out, templates
        self.out_w, self.out_h, self.dpi, self.quality, self.fill_mode = out_w, out_h, dpi, quality, fill_mode

    def run(self):
        files = [f for f in Path(self.inp).iterdir()
                 if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("主图_")]

        total, ok, fail = len(files), 0, 0
        Path(self.out).mkdir(parents=True, exist_ok=True)

        for i, src in enumerate(files):
            self.sig_log.emit(f"── [{i+1}/{total}] {src.name}")
            try:
                photo = Image.open(src).convert("RGB")

                for tp_str in self.templates:
                    r = main_composite(
                        photo, tp_str,
                        self.out_w, self.out_h,
                        self.dpi,
                        self.fill_mode,
                        logger_callback=lambda msg: self.sig_log.emit(msg)
                    )

                    # ✅ 改为 PNG
                    name = f"主图_{src.stem}_{Path(tp_str).stem}.png"
                    r.save(str(Path(self.out) / name), "PNG")

                    self.sig_log.emit(f"✅ {name}")

                ok += 1

            except Exception as e:
                self.sig_log.emit(f"❌ 失败: {e}")
                fail += 1

            self.sig_prog.emit(i + 1, total)

        self.sig_done.emit(ok, fail)

# ══════════════════════════════════════════════════════════════
# UI 组件 (修复预览内存 Bug)
# ══════════════════════════════════════════════════════════════
class PathRow(QWidget):
    def __init__(self, icon, placeholder, parent=None):
        super().__init__(parent); lay=QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(8)
        ico=QLabel(icon); ico.setFixedWidth(20); ico.setStyleSheet("color:#606070;")
        self.edit=QLineEdit(); self.edit.setPlaceholderText(placeholder); self.edit.setReadOnly(True)
        btn=QPushButton("浏览"); btn.setObjectName("btnGhost"); btn.setFixedWidth(52); btn.clicked.connect(self._browse)
        lay.addWidget(ico); lay.addWidget(self.edit,1); lay.addWidget(btn)
    def _browse(self):
        d=QFileDialog.getExistingDirectory(self,"选择文件夹")
        if d: self.edit.setText(d)
    def path(self): return self.edit.text().strip()

class PreviewCanvas(QLabel):
    pos_changed = pyqtSignal(float, float)
    def __init__(self, parent=None):
        super().__init__(parent); self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(380, 280); self.setStyleSheet("background:#0e0e16;border-radius:10px;")
        self._bg=self._fr=None; self._cx=0.5; self._cy=0.5; self._sc=0.4
        self._dragging=False; self._temp_data = None
    def set_images(self, bg, fr): self._bg,self._fr = bg, fr; self._refresh()
    def set_placement(self, cx, cy, sc): self._cx,self._cy,self._sc = cx, cy, sc; self._refresh()
    def _refresh(self):
        if self._bg is None or self.width()<10: return
        comp = frame_composite_with_punch(self._bg, self._fr, self._cx, self._cy, self._sc) if self._fr else self._bg.copy()
        comp.thumbnail((self.width(), self.height()), Image.LANCZOS)
        self._temp_data = comp.convert("RGBA").tobytes("raw", "RGBA")
        qi = QImage(self._temp_data, comp.width, comp.height, comp.width*4, QImage.Format.Format_RGBA8888)
        self.setPixmap(QPixmap.fromImage(qi))
        self._dr=((self.width()-comp.width)//2,(self.height()-comp.height)//2,comp.width,comp.height)
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton and self._bg: self._dragging=True
    def mouseMoveEvent(self,e):
        if self._dragging and self._bg:
            dx,dy,pw,ph=self._dr
            self._cx=max(0.01,min(0.99,(e.position().x()-dx)/pw))
            self._cy=max(0.01,min(0.99,(e.position().y()-dy)/ph))
            self._refresh(); self.pos_changed.emit(self._cx, self._cy)
    def mouseReleaseEvent(self,e): self._dragging=False

class FrameTab(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent); self._cfg, self._fr_rgba, self._bg_pil, self._batch_paths = cfg, None, None, []
        self._build()
    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0,8,0,0)
        lp = QWidget(); lp.setObjectName("panel"); lp.setFixedWidth(300); ll = QVBoxLayout(lp)
        inner = QWidget(); sl = QVBoxLayout(inner)
        sl.addWidget(sec("1. 透明相框图 (必须 PNG)")); hr = QHBoxLayout(); self.lbl_fr = QLabel("未选")
        btn_fr = QPushButton("选择"); btn_fr.setObjectName("btnGhost"); btn_fr.clicked.connect(self._load_fr)
        hr.addWidget(self.lbl_fr,1); hr.addWidget(btn_fr); sl.addLayout(hr)
        sl.addWidget(sec("2. 预览背景图")); pr = QHBoxLayout(); self.lbl_prev = QLabel("未选")
        btn_prev = QPushButton("选择"); btn_prev.setObjectName("btnGhost"); btn_prev.clicked.connect(self._load_bg)
        pr.addWidget(self.lbl_prev,1); pr.addWidget(btn_prev); sl.addLayout(pr)
        def add_sld(txt):
            r=QHBoxLayout(); r.addWidget(QLabel(txt)); s=QSlider(Qt.Orientation.Horizontal); s.setRange(1,99); s.setValue(50)
            sp=QDoubleSpinBox(); sp.setRange(0.01,0.99); sp.setSingleStep(0.01); sp.setValue(0.5)
            r.addWidget(s,1); r.addWidget(sp); return r,s,sp
        r1,self.s1,self.p1=add_sld("H:"); r2,self.s2,self.p2=add_sld("V:"); r3,self.s3,self.p3=add_sld("S:")
        sl.addLayout(r1); sl.addLayout(r2); sl.addLayout(r3)
        sl.addWidget(sec("3. 批量生成透明模板")); hr2 = QHBoxLayout()
        b_a = QPushButton("+添加背景图"); b_a.setObjectName("btnGreen"); b_a.clicked.connect(self._add)
        hr2.addWidget(b_a,1); sl.addLayout(hr2)
        self.lst = QListWidget(); sl.addWidget(self.lst)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(inner); ll.addWidget(sc)
        self.prog = QProgressBar(); self.prog.setVisible(False)
        btn_go = QPushButton("🚀 开始生成带洞模板"); btn_go.setObjectName("btnPrimary"); btn_go.clicked.connect(self._run)
        ll.addWidget(self.prog); ll.addWidget(btn_go); root.addWidget(lp)
        self.canvas = PreviewCanvas(); self.canvas.pos_changed.connect(self._on_drag); root.addWidget(self.canvas,1); self._link()
    def _link(self):
        def lnk(s,p,f):
            s.valueChanged.connect(lambda v:[p.blockSignals(True),p.setValue(v/100),p.blockSignals(False),f()])
            p.valueChanged.connect(lambda v:[s.blockSignals(True),s.setValue(int(v*100)),s.blockSignals(False),f()])
        lnk(self.s1,self.p1,self._apply); lnk(self.s2,self.p2,self._apply); lnk(self.s3,self.p3,self._apply)
    def _apply(self): self.canvas.set_placement(self.s1.value()/100, self.s2.value()/100, self.s3.value()/100)
    def _on_drag(self,cx,cy): self.p1.setValue(cx); self.p2.setValue(cy); self._apply()
    def _load_fr(self):
        p,_=QFileDialog.getOpenFileName(self, filter="PNG (*.png)");
        if p: self._fr_rgba = Image.open(p).convert("RGBA"); self.lbl_fr.setText(Path(p).name); self._apply()
    def _load_bg(self):
        p,_=QFileDialog.getOpenFileName(self);
        if p: self._bg_pil = Image.open(p).convert("RGB"); self.lbl_prev.setText(Path(p).name); self.canvas.set_images(self._bg_pil, self._fr_rgba); self._apply()
    def _add(self): ps,_=QFileDialog.getOpenFileNames(self); self._batch_paths.extend(ps); self.lst.addItems([Path(x).name for x in ps])
    def _run(self):
        out = QFileDialog.getExistingDirectory(self)
        if not out or not self._fr_rgba: return
        self.prog.setVisible(True); self._worker = FrameBatchWorker(self._batch_paths, self._fr_rgba, self.s1.value()/100, self.s2.value()/100, self.s3.value()/100, out)
        self._worker.sig_done.connect(lambda: self.prog.setVisible(False)); self._worker.start()

class MainTab(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent); self._cfg, self.templates = cfg, []
        self._build()
    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0,8,0,0)
        lp = QWidget(); lp.setObjectName("panel"); lp.setFixedWidth(300); ll = QVBoxLayout(lp)
        self.p_in=PathRow("📂","照片目录"); self.p_out=PathRow("💾","输出目录")
        ll.addWidget(sec("1. 路径设置")); ll.addWidget(self.p_in); ll.addWidget(self.p_out)
        ll.addWidget(sec("2. 添加 Tab1 生成的透明模板")); bt = QHBoxLayout(); b_a=QPushButton("+添加"); b_a.setObjectName("btnGreen"); b_a.clicked.connect(self._add)
        bt.addWidget(b_a,1); ll.addLayout(bt); self.lst = QListWidget(); ll.addWidget(self.lst)
        sz=QHBoxLayout(); self.sp_w=QSpinBox(); self.sp_h=QSpinBox();
        for sp in (self.sp_w,self.sp_h): sp.setRange(100,5000); sp.setValue(800)
        sz.addWidget(QLabel("宽:")); sz.addWidget(self.sp_w); sz.addWidget(QLabel("高:")); sz.addWidget(self.sp_h)
        ll.addLayout(sz); self.cb_stretch=QCheckBox("拉伸填满"); ll.addWidget(self.cb_stretch); ll.addStretch()
        self.prog=QProgressBar(); self.prog.setTextVisible(False); ll.addWidget(self.prog); btn_go=QPushButton("🚀 开始智能填充"); btn_go.setObjectName("btnPrimary"); btn_go.clicked.connect(self._start)
        ll.addWidget(btn_go); root.addWidget(lp); self.log = QTextEdit(); self.log.setReadOnly(True); root.addWidget(self.log, 1)
    def _add(self): fs,_=QFileDialog.getOpenFileNames(self, filter="PNG (*.png)"); self.templates.extend(fs); self.lst.addItems([Path(x).name for x in fs])
    def _start(self):
        m = 'stretch' if self.cb_stretch.isChecked() else 'contain'
        self._worker = MainBatchWorker(self.p_in.path(), self.p_out.path(), self.templates, self.sp_w.value(), self.sp_h.value(), 300, 95, m)
        self._worker.sig_log.connect(lambda msg: self.log.append(msg))
        self._worker.sig_prog.connect(lambda c,t: [self.prog.setMaximum(t), self.prog.setValue(c)])
        self._worker.start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("透明通道闭环填充工具 - 矩形精准版"); self.resize(1100, 750); self._cfg = load_cfg()
        root = QWidget(); self.setCentralWidget(root); rl = QVBoxLayout(root)
        self.tabs = QTabWidget(); self.tab1 = FrameTab(self._cfg); self.tab2 = MainTab(self._cfg)
        self.tabs.addTab(self.tab1, " 📐 Tab1 相框背景合成 "); self.tabs.addTab(self.tab2, " 🖼 Tab2 主图智能填充 ")
        rl.addWidget(self.tabs); self.setStyleSheet(QSS)
    def closeEvent(self, e): save_cfg(self._cfg); super().closeEvent(e)

if __name__ == "__main__":
    if sys.platform == "win32": ctypes.windll.user32.SetProcessDPIAware()
    app = QApplication(sys.argv); app.setStyle("Fusion"); win = MainWindow(); win.show(); sys.exit(app.exec())