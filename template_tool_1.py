"""
相框合成工具 v3  —  批量直出版
pip install PyQt6 pillow numpy
"""

import sys, json, logging
from pathlib import Path
from typing  import Optional, Tuple, List

import numpy as np
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QFrame, QSplitter,
    QStatusBar, QMessageBox, QSlider, QListWidget, QListWidgetItem,
    QProgressBar, QScrollArea, QAbstractItemView, QDoubleSpinBox
)
from PyQt6.QtCore  import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui   import QPixmap, QImage, QCursor, QColor, QPalette

log = logging.getLogger(__name__)
APP_ORG  = "Ralo"
APP_NAME = "FrameComposer"
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ─────────────────────────────────────────────────────────────
# 样式
# ─────────────────────────────────────────────────────────────
QSS = """
* { box-sizing: border-box; outline: none; }
QMainWindow { background: #111113; }
QWidget {
    color: #d8d8e0;
    font-family: "Microsoft YaHei UI","PingFang SC","SF Pro Display",sans-serif;
    font-size: 13px; background: transparent;
}
QWidget#root { background: #111113; }

/* 分区标题 */
QLabel#sec {
    color: #44445a; font-size: 10px; font-weight: 700;
    letter-spacing: 2.5px; background: transparent;
}

/* 分隔线 */
QFrame#div { background: #20202a; border: none; max-height: 1px; }

/* 输入框 */
QLineEdit {
    background: #1c1c22; border: 1px solid #2a2a34;
    border-radius: 7px; padding: 7px 10px;
    color: #a0a0b4; font-size: 12px;
}
QLineEdit:focus { border-color: #2a2a34; }

/* 列表 */
QListWidget {
    background: #181820; border: 1px solid #28283a;
    border-radius: 8px; color: #b8b8cc; padding: 3px; font-size: 12px;
}
QListWidget::item { padding: 6px 10px; border-radius: 5px; }
QListWidget::item:selected { background: #0a84ff; color: #fff; }
QListWidget::item:hover:!selected { background: #22222e; }

/* 滑块 */
QSlider::groove:horizontal { height: 3px; background: #28283a; border-radius: 1px; }
QSlider::handle:horizontal {
    width: 13px; height: 13px; margin: -5px 0;
    background: #c8c8d8; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #ffffff; }
QSlider::sub-page:horizontal { background: #0a84ff; border-radius: 1px; }

/* 数字框 */
QDoubleSpinBox {
    background: #1c1c22; border: 1px solid #2a2a34;
    border-radius: 6px; padding: 5px 6px;
    color: #a8a8c0; font-size: 12px; min-width: 64px; max-width: 64px;
    font-family: "Cascadia Code","Consolas",monospace;
}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #24242e; border: none; width: 15px;
}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #30303e; }

/* 进度条 */
QProgressBar {
    background: #1a1a22; border: none; border-radius: 2px;
    height: 4px; color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0a84ff,stop:1 #5ac8fa);
    border-radius: 2px;
}

/* 按钮 */
QPushButton {
    border-radius: 7px; padding: 8px 14px;
    font-weight: 600; font-size: 13px; border: none;
}
QPushButton#btnAction {
    background: #0a84ff; color: #fff;
    font-size: 13px; font-weight: 700; padding: 11px 0; border-radius: 9px;
}
QPushButton#btnAction:hover   { background: #2d96ff; }
QPushButton#btnAction:pressed { background: #0060df; }
QPushButton#btnAction:disabled { background: #1e1e28; color: #3c3c4e; }

QPushButton#btnGhost {
    background: #1c1c24; color: #8888a8;
    border: 1px solid #2c2c3a; font-size: 12px; padding: 7px 12px;
}
QPushButton#btnGhost:hover { background: #24243a; color: #c0c0d8; }

QPushButton#btnGreen {
    background: #182820; color: #28c454;
    border: 1px solid #284838; font-size: 12px; font-weight: 600; padding: 8px 0;
}
QPushButton#btnGreen:hover { background: #1e3228; border-color: #3a6040; }
QPushButton#btnGreen:disabled { background: #141414; color: #2a4a30; border-color: #1e1e1e; }

QPushButton#btnRed {
    background: #281818; color: #f04030;
    border: 1px solid #402020; font-size: 12px; font-weight: 600; padding: 8px 0;
}
QPushButton#btnRed:hover { background: #321e1e; border-color: #583030; }

QPushButton#btnOrange {
    background: #28200e; color: #ff9f0a;
    border: 1px solid #483010; font-size: 12px; font-weight: 700; padding: 9px 0;
    border-radius: 9px;
}
QPushButton#btnOrange:hover { background: #32280e; border-color: #5c4010; }
QPushButton#btnOrange:disabled { background: #1a1a14; color: #443010; border-color: #1e1e14; }

/* 滚动条 */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 5px; }
QScrollBar::handle:vertical { background: #28283a; border-radius: 2px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #38384a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* 状态栏 */
QStatusBar { background: #0c0c12; border-top: 1px solid #1a1a22; color: #40405a; font-size: 11px; padding: 2px 14px; }

/* Splitter */
QSplitter::handle { background: #1c1c26; }
"""


# ─────────────────────────────────────────────────────────────
# 模板
# ─────────────────────────────────────────────────────────────

class FrameTemplate:
    def __init__(self):
        self.cx = 0.5; self.cy = 0.5; self.scale = 0.4
        self.ref_w = self.ref_h = 0
        self.left = self.top = self.right = self.bottom = 0
        self.frame_w = self.frame_h = 0
        self.loaded = False

    def record(self, bg, frame_rgba, cx, cy, scale):
        bw, bh = bg.size
        fw = int(bw * scale)
        fh = int(frame_rgba.height * fw / frame_rgba.width)
        left = max(0, min(int(cx * bw - fw / 2), bw - fw))
        top  = max(0, min(int(cy * bh - fh / 2), bh - fh))
        self.cx, self.cy, self.scale = cx, cy, scale
        self.ref_w, self.ref_h = bw, bh
        self.left, self.top = left, top
        self.right  = bw - (left + fw)
        self.bottom = bh - (top  + fh)
        self.frame_w, self.frame_h = fw, fh
        self.loaded = True

    def apply_to(self, bg, frame_rgba):
        """保持比例模式"""
        return self.cx, self.cy, self.scale

    def to_dict(self): return dict(self.__dict__)
    def from_dict(self, d):
        for k, v in d.items():
            if hasattr(self, k): setattr(self, k, v)

    def margin_text(self):
        if not self.loaded: return "—"
        return f"左 {self.left}  右 {self.right}  上 {self.top}  下 {self.bottom}  (px)"


# ─────────────────────────────────────────────────────────────
# 图像处理
# ─────────────────────────────────────────────────────────────

def extract_frame(img):
    if img.mode == "RGBA": return img.copy()
    rgba = img.convert("RGBA")
    arr  = np.array(rgba)
    bg   = np.mean([arr[0,0,:3],arr[0,-1,:3],arr[-1,0,:3],arr[-1,-1,:3]], axis=0).astype(np.uint8)
    arr[np.all(np.abs(arr[:,:,:3].astype(int)-bg.astype(int))<30, axis=2), 3] = 0
    return Image.fromarray(arr, "RGBA")

def composite(bg, frame_rgba, cx, cy, scale):
    bw, bh = bg.size
    fw = int(bw * scale)
    fh = int(frame_rgba.height * fw / frame_rgba.width)
    fr = frame_rgba.resize((fw, fh), Image.LANCZOS)
    left = max(0, min(int(cx*bw - fw/2), bw-fw))
    top  = max(0, min(int(cy*bh - fh/2), bh-fh))
    out  = bg.convert("RGBA").copy()
    out.paste(fr, (left, top), fr)
    return out.convert("RGB")


# ─────────────────────────────────────────────────────────────
# 批量线程
# ─────────────────────────────────────────────────────────────

class BatchWorker(QThread):
    sig_progress = pyqtSignal(int, str)
    sig_done     = pyqtSignal(int)
    sig_error    = pyqtSignal(str)

    def __init__(self, bg_paths, frame_rgba, template, out_dir):
        super().__init__()
        self.bg_paths = bg_paths; self.frame_rgba = frame_rgba
        self.template = template; self.out_dir = out_dir

    def run(self):
        saved = 0
        for i, path in enumerate(self.bg_paths):
            try:
                bg = Image.open(path).convert("RGB")
                cx, cy, scale = self.template.apply_to(bg, self.frame_rgba)
                result = composite(bg, self.frame_rgba, cx, cy, scale)
                out = str(Path(self.out_dir) / f"{Path(path).stem}_合成.jpg")
                result.save(out, "JPEG", quality=95)
                saved += 1
                self.sig_progress.emit(i+1, Path(path).name)
            except Exception as e:
                self.sig_error.emit(f"{Path(path).name}: {e}")
        self.sig_done.emit(saved)


# ─────────────────────────────────────────────────────────────
# 预览画布
# ─────────────────────────────────────────────────────────────

class PreviewCanvas(QLabel):
    pos_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background:#0e0e14; border-radius:10px; border:1px solid #20202e;")
        self._bg = self._fr = None
        self._cx = 0.5; self._cy = 0.5; self._scale = 0.4
        self._dragging = False
        self._dr = (0,0,1,1)
        ph = QLabel("请先加载相框图，再添加一张背景图预览", self)
        ph.setStyleSheet("color:#36364a; font-size:12px; background:transparent;")
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ph = ph

    def resizeEvent(self, e):
        self._ph.setGeometry(self.rect()); self._refresh(); super().resizeEvent(e)

    def set_images(self, bg, fr):
        self._bg, self._fr = bg, fr
        self._ph.setVisible(bg is None); self._refresh()

    def set_placement(self, cx, cy, scale):
        self._cx, self._cy, self._scale = cx, cy, scale; self._refresh()

    def _refresh(self):
        if self._bg is None: self.clear(); return
        comp = composite(self._bg, self._fr, self._cx, self._cy, self._scale) \
            if self._fr else self._bg.copy()
        cw, ch = self.width(), self.height()
        if cw < 10 or ch < 10: return
        comp.thumbnail((cw, ch), Image.LANCZOS)
        d = comp.convert("RGB").tobytes("raw","RGB")
        qi = QImage(d, comp.width, comp.height, comp.width*3, QImage.Format.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(qi))
        pw, ph = comp.width, comp.height
        self._dr = ((cw-pw)//2, (ch-ph)//2, pw, ph)

    def mousePressEvent(self, e):
        if e.button()==Qt.MouseButton.LeftButton and self._bg:
            self._dragging=True; self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def mouseMoveEvent(self, e):
        if not self._dragging or not self._bg: return
        dx,dy,pw,ph = self._dr
        self._cx = max(0.01, min(0.99, (e.position().x()-dx)/pw))
        self._cy = max(0.01, min(0.99, (e.position().y()-dy)/ph))
        self._refresh(); self.pos_changed.emit(self._cx, self._cy)

    def mouseReleaseEvent(self, e):
        self._dragging=False; self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))


# ─────────────────────────────────────────────────────────────
# 辅助 UI
# ─────────────────────────────────────────────────────────────

def sec(text):
    l = QLabel(text); l.setObjectName("sec"); return l

def div():
    f = QFrame(); f.setObjectName("div"); f.setFrameShape(QFrame.Shape.HLine); return f


# ─────────────────────────────────────────────────────────────
# 主窗口
# ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("相框合成工具")
        self.setMinimumSize(1020, 620)
        self.resize(1200, 740)
        self._bg_pil      = None   # 预览用背景图
        self._frame_rgba  = None
        self._result      = None
        self._template    = FrameTemplate()
        self._batch_paths : List[str] = []
        self._worker      = None
        self._frame_path   = ""
        self._prev_bg_path = ""
        self._settings    = QSettings(APP_ORG, APP_NAME)
        self._build_ui()
        self.setStyleSheet(QSS)
        self.setStatusBar(QStatusBar())
        self._load_settings()
        self._status("就绪")

    # ── 设置持久化 ────────────────────────────────────────────
    def _load_settings(self):
        s = self._settings
        # 相框图路径
        fr = s.value("frame_path","")
        if fr and Path(fr).exists():
            from PIL import Image as _I
            self._frame_rgba = __import__("__main__").extract_frame(_I.open(fr))
            self.lbl_fr.setText(Path(fr).name)
            if self._bg_pil: self._sync_canvas()
        # 预览背景图路径
        bg = s.value("prev_bg_path","")
        if bg and Path(bg).exists():
            from PIL import Image as _I
            self._bg_pil = _I.open(bg).convert("RGB")
            self.lbl_prev_bg.setText(Path(bg).name)
            if self._frame_rgba: self._sync_canvas()
        # 滑块位置
        cx    = s.value("cx",    0.50, type=float)
        cy    = s.value("cy",    0.50, type=float)
        scale = s.value("scale", 0.40, type=float)
        for sld,spn,v in [(self.sld_cx,self.spn_cx,int(cx*100)),
                          (self.sld_cy,self.spn_cy,int(cy*100)),
                          (self.sld_scale,self.spn_scale,int(scale*100))]:
            sld.blockSignals(True); sld.setValue(v); sld.blockSignals(False)
            spn.blockSignals(True); spn.setValue(v/100); spn.blockSignals(False)
        # 批量列表
        batch = s.value("batch_paths",[])
        if isinstance(batch, str): batch = [batch]
        for p in batch:
            if Path(p).exists() and p not in self._batch_paths:
                self._batch_paths.append(p)
                self.lst_batch.addItem(QListWidgetItem(Path(p).name))
        self.lbl_count.setText(f"{len(self._batch_paths)} 张待合成")
        self._check_run_ready()

    def _save_settings(self):
        s = self._settings
        s.setValue("frame_path",   getattr(self,"_frame_path",""))
        s.setValue("prev_bg_path", getattr(self,"_prev_bg_path",""))
        s.setValue("cx",    self.sld_cx.value()/100)
        s.setValue("cy",    self.sld_cy.value()/100)
        s.setValue("scale", self.sld_scale.value()/100)
        s.setValue("batch_paths", self._batch_paths)

    def closeEvent(self, e):
        self._save_settings(); super().closeEvent(e)

    # ── 构建 UI ───────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setContentsMargins(16,14,16,10); rl.setSpacing(10)

        # 顶栏
        hdr = QHBoxLayout()
        t = QLabel("相框合成"); t.setStyleSheet("color:#dddde8;font-size:16px;font-weight:700;")
        s = QLabel("拖拽定位 · 模板记录 · 批量输出")
        s.setStyleSheet("color:#2e2e40;font-size:11px;")
        hdr.addWidget(t); hdr.addStretch(); hdr.addWidget(s)
        rl.addLayout(hdr)

        sp = QSplitter(Qt.Orientation.Horizontal); sp.setHandleWidth(1)

        # ════ 左控制面板 ════
        lw = QWidget()
        lw.setStyleSheet(
            "QWidget#lp{background:#161619;border:1px solid #22222e;border-radius:12px;}")
        lw.setObjectName("lp"); lw.setFixedWidth(310)
        ll = QVBoxLayout(lw); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        # 滚动内容
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); sl = QVBoxLayout(inner)
        sl.setContentsMargins(16,16,12,12); sl.setSpacing(0)

        # —— 第一步：加载相框 ——
        sl.addWidget(sec("第一步  ·  相框图"))
        sl.addSpacing(8)
        fr_row = QHBoxLayout(); fr_row.setSpacing(8)
        self.lbl_fr = QLabel("未选择")
        self.lbl_fr.setStyleSheet("color:#606070;font-size:11.5px;background:transparent;")
        self.lbl_fr.setWordWrap(True)
        btn_fr = QPushButton("选择相框图"); btn_fr.setObjectName("btnGhost")
        btn_fr.clicked.connect(self._load_frame)
        fr_row.addWidget(self.lbl_fr,1); fr_row.addWidget(btn_fr)
        sl.addLayout(fr_row)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        # —— 第二步：预览调位置 ——
        sl.addWidget(sec("第二步  ·  调整位置（预览图可直接拖拽）"))
        sl.addSpacing(8)

        # 预览背景图选择（只用于预览）
        prev_row = QHBoxLayout(); prev_row.setSpacing(8)
        self.lbl_prev_bg = QLabel("未选择预览背景")
        self.lbl_prev_bg.setStyleSheet("color:#606070;font-size:11px;background:transparent;")
        self.lbl_prev_bg.setWordWrap(True)
        btn_prev = QPushButton("选背景预览"); btn_prev.setObjectName("btnGhost")
        btn_prev.clicked.connect(self._load_preview_bg)
        prev_row.addWidget(self.lbl_prev_bg,1); prev_row.addWidget(btn_prev)
        sl.addLayout(prev_row)
        sl.addSpacing(10)

        # 滑块 + 数字框
        def slider_row(lbl_txt, lo, hi, default):
            row = QHBoxLayout(); row.setSpacing(8)
            lbl = QLabel(lbl_txt)
            lbl.setFixedWidth(48)
            lbl.setStyleSheet("color:#666678;font-size:11.5px;background:transparent;")
            sld = QSlider(Qt.Orientation.Horizontal)
            sld.setRange(lo, hi); sld.setValue(default)
            spn = QDoubleSpinBox()
            spn.setRange(lo/100, hi/100); spn.setDecimals(3)
            spn.setSingleStep(0.005); spn.setValue(default/100)
            row.addWidget(lbl); row.addWidget(sld,1); row.addWidget(spn)
            return row, sld, spn

        r1,self.sld_cx,   self.spn_cx    = slider_row("水平", 1, 99, 50)
        r2,self.sld_cy,   self.spn_cy    = slider_row("垂直", 1, 99, 50)
        r3,self.sld_scale,self.spn_scale = slider_row("大小", 5, 98, 40)
        sl.addLayout(r1); sl.addSpacing(6)
        sl.addLayout(r2); sl.addSpacing(6)
        sl.addLayout(r3); sl.addSpacing(10)

        # 双向绑定
        def link(sld, spn, fn):
            sld.valueChanged.connect(lambda v: [
                spn.blockSignals(True), spn.setValue(v/100), spn.blockSignals(False), fn(v)])
            spn.valueChanged.connect(lambda v: [
                sld.blockSignals(True), sld.setValue(int(round(v*100))), sld.blockSignals(False), fn(int(round(v*100)))])
        link(self.sld_cx,    self.spn_cx,    self._on_cx)
        link(self.sld_cy,    self.spn_cy,    self._on_cy)
        link(self.sld_scale, self.spn_scale, self._on_scale)

        # 边距提示
        self.lbl_margins = QLabel("—")
        self.lbl_margins.setStyleSheet("color:#40405a;font-size:10.5px;background:transparent;")
        self.lbl_margins.setWordWrap(True)
        sl.addWidget(self.lbl_margins)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        # —— 第三步：保存模板 ——
        sl.addWidget(sec("第三步  ·  保存位置模板"))
        sl.addSpacing(8)

        self.btn_save_tpl = QPushButton("📐  保存当前位置为模板")
        self.btn_save_tpl.setObjectName("btnOrange")
        self.btn_save_tpl.setEnabled(False)
        self.btn_save_tpl.clicked.connect(self._save_template)
        sl.addWidget(self.btn_save_tpl)
        sl.addSpacing(8)

        tpl_io = QHBoxLayout(); tpl_io.setSpacing(8)
        btn_exp = QPushButton("导出 JSON"); btn_exp.setObjectName("btnGhost")
        btn_imp = QPushButton("导入 JSON"); btn_imp.setObjectName("btnGhost")
        btn_exp.clicked.connect(self._export_tpl)
        btn_imp.clicked.connect(self._import_tpl)
        tpl_io.addWidget(btn_exp,1); tpl_io.addWidget(btn_imp,1)
        sl.addLayout(tpl_io)
        sl.addSpacing(8)

        self.lbl_tpl = QLabel("尚无模板")
        self.lbl_tpl.setStyleSheet("color:#40405a;font-size:10.5px;background:transparent;")
        self.lbl_tpl.setWordWrap(True)
        sl.addWidget(self.lbl_tpl)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        # —— 第四步：批量 ——
        sl.addWidget(sec("第四步  ·  批量添加背景图"))
        sl.addSpacing(8)

        add_clr = QHBoxLayout(); add_clr.setSpacing(8)
        btn_add = QPushButton("＋  添加图片"); btn_add.setObjectName("btnGreen")
        btn_add.setFixedHeight(34); btn_add.clicked.connect(self._add_batch)
        btn_clr = QPushButton("清空"); btn_clr.setObjectName("btnRed")
        btn_clr.setFixedHeight(34); btn_clr.setFixedWidth(54)
        btn_clr.clicked.connect(self._clear_batch)
        add_clr.addWidget(btn_add,1); add_clr.addWidget(btn_clr)
        sl.addLayout(add_clr)
        sl.addSpacing(8)

        self.lst_batch = QListWidget()
        self.lst_batch.setFixedHeight(110)
        self.lst_batch.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        sl.addWidget(self.lst_batch)
        sl.addSpacing(6)

        self.lbl_count = QLabel("0 张待合成")
        self.lbl_count.setStyleSheet("color:#40405a;font-size:11px;background:transparent;")
        sl.addWidget(self.lbl_count)
        sl.addStretch()

        scroll.setWidget(inner)
        ll.addWidget(scroll,1)

        # 底部固定按钮区
        bot = QWidget(); bot.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(bot); bl.setContentsMargins(16,8,16,14); bl.setSpacing(6)

        self.prog = QProgressBar(); self.prog.setFixedHeight(4)
        self.prog.setTextVisible(False); self.prog.setVisible(False)
        bl.addWidget(self.prog)

        self.btn_run = QPushButton("🚀  开始批量合成")
        self.btn_run.setObjectName("btnAction")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run_batch)
        bl.addWidget(self.btn_run)

        ll.addWidget(bot)
        sp.addWidget(lw)

        # ════ 右预览区 ════
        rw = QWidget()
        rlay = QVBoxLayout(rw); rlay.setContentsMargins(10,0,0,0); rlay.setSpacing(6)

        phdr = QHBoxLayout()
        phdr.addWidget(QLabel("PREVIEW") if False else self._make_preview_label())
        self.lbl_pos = QLabel("—")
        self.lbl_pos.setStyleSheet("color:#30304a;font-size:11px;background:transparent;")
        phdr.addStretch(); phdr.addWidget(self.lbl_pos)
        rlay.addLayout(phdr)

        self.canvas = PreviewCanvas()
        self.canvas.pos_changed.connect(self._on_drag)
        rlay.addWidget(self.canvas,1)
        sp.addWidget(rw)

        sp.setSizes([310, 890])
        rl.addWidget(sp,1)

    def _make_preview_label(self):
        l = QLabel("PREVIEW")
        l.setStyleSheet("color:#28283a;font-size:10px;font-weight:700;letter-spacing:2px;background:transparent;")
        return l

    # ── 工具 ─────────────────────────────────────────────────
    def _status(self, msg): self.statusBar().showMessage(msg)

    def _sync_canvas(self):
        self.canvas.set_images(self._bg_pil, self._frame_rgba)
        self._apply_placement()

    def _apply_placement(self, cx=None, cy=None, scale=None):
        if cx    is None: cx    = self.sld_cx.value()    / 100
        if cy    is None: cy    = self.sld_cy.value()    / 100
        if scale is None: scale = self.sld_scale.value() / 100
        self.canvas.set_placement(cx, cy, scale)
        self.lbl_pos.setText(f"水平 {cx:.3f}  垂直 {cy:.3f}  大小 {scale:.3f}")
        if self._bg_pil and self._frame_rgba:
            self._result = composite(self._bg_pil, self._frame_rgba, cx, cy, scale)

    def _check_save_tpl_ready(self):
        ok = self._frame_rgba is not None and self._bg_pil is not None
        self.btn_save_tpl.setEnabled(ok)

    def _check_run_ready(self):
        ok = (self._frame_rgba is not None
              and self._template.loaded
              and len(self._batch_paths) > 0)
        self.btn_run.setEnabled(ok)

    # ── 加载 ─────────────────────────────────────────────────
    def _load_frame(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择相框图",
            filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        if not path: return
        self._frame_rgba = extract_frame(Image.open(path))
        self._frame_path = path
        self.lbl_fr.setText(Path(path).name)
        self._status(f"相框图: {Path(path).name}（已自动抠图）")
        self._check_save_tpl_ready()
        if self._bg_pil: self._sync_canvas()

    def _load_preview_bg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择一张背景图（仅用于预览）",
            filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        if not path: return
        self._bg_pil = Image.open(path).convert("RGB")
        self._prev_bg_path = path
        self.lbl_prev_bg.setText(Path(path).name)
        self._status(f"预览背景: {Path(path).name}  {self._bg_pil.width}×{self._bg_pil.height}")
        self._check_save_tpl_ready()
        self._sync_canvas()

    # ── 滑块 ─────────────────────────────────────────────────
    def _on_cx(self, v):    self._apply_placement(cx=v/100)
    def _on_cy(self, v):    self._apply_placement(cy=v/100)
    def _on_scale(self, v): self._apply_placement(scale=v/100)

    def _on_drag(self, cx, cy):
        for sld, spn, v in [(self.sld_cx,self.spn_cx,int(cx*100)),
                            (self.sld_cy,self.spn_cy,int(cy*100))]:
            sld.blockSignals(True); sld.setValue(v); sld.blockSignals(False)
            spn.blockSignals(True); spn.setValue(v/100); spn.blockSignals(False)
        self._apply_placement(cx, cy, self.sld_scale.value()/100)

    # ── 模板 ─────────────────────────────────────────────────
    def _save_template(self):
        cx = self.sld_cx.value()/100
        cy = self.sld_cy.value()/100
        sc = self.sld_scale.value()/100
        self._template.record(self._bg_pil, self._frame_rgba, cx, cy, sc)
        t = self._template
        self.lbl_margins.setText(t.margin_text())
        self.lbl_tpl.setText(
            f"✅ 已保存\n"
            f"参考图 {t.ref_w}×{t.ref_h}\n"
            f"左{t.left} 右{t.right} 上{t.top} 下{t.bottom} px")
        self._status(f"模板已保存  ·  {t.margin_text()}")
        self._check_run_ready()

    def _export_tpl(self):
        if not self._template.loaded:
            QMessageBox.information(self,"提示","请先保存模板"); return
        p,_ = QFileDialog.getSaveFileName(self,"导出模板","frame_template.json","JSON (*.json)")
        if not p: return
        with open(p,"w",encoding="utf-8") as f:
            json.dump(self._template.to_dict(), f, ensure_ascii=False, indent=2)
        self._status(f"已导出: {p}")

    def _import_tpl(self):
        p,_ = QFileDialog.getOpenFileName(self,"导入模板",filter="JSON (*.json)")
        if not p: return
        with open(p,"r",encoding="utf-8") as f:
            self._template.from_dict(json.load(f))
        self._template.loaded = True
        t = self._template
        self.lbl_tpl.setText(
            f"✅ 已导入\n参考图 {t.ref_w}×{t.ref_h}\n左{t.left} 右{t.right} 上{t.top} 下{t.bottom} px")
        self.lbl_margins.setText(t.margin_text())
        for sld,spn,v in [(self.sld_cx,self.spn_cx,int(t.cx*100)),
                          (self.sld_cy,self.spn_cy,int(t.cy*100)),
                          (self.sld_scale,self.spn_scale,int(t.scale*100))]:
            sld.blockSignals(True); sld.setValue(v); sld.blockSignals(False)
            spn.blockSignals(True); spn.setValue(v/100); spn.blockSignals(False)
        if self._bg_pil and self._frame_rgba:
            self._apply_placement(t.cx, t.cy, t.scale)
        self._check_run_ready()
        self._status(f"模板已导入: {Path(p).name}")

    # ── 批量 ─────────────────────────────────────────────────
    def _add_batch(self):
        paths,_ = QFileDialog.getOpenFileNames(
            self,"添加背景图（可多选）",
            filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        for p in paths:
            if p not in self._batch_paths:
                self._batch_paths.append(p)
                self.lst_batch.addItem(QListWidgetItem(Path(p).name))
        n = len(self._batch_paths)
        self.lbl_count.setText(f"{n} 张待合成")
        self._check_run_ready()
        self._status(f"批量列表: {n} 张")

    def _clear_batch(self):
        self._batch_paths.clear(); self.lst_batch.clear()
        self.lbl_count.setText("0 张待合成")
        self._check_run_ready()

    def _run_batch(self):
        out = QFileDialog.getExistingDirectory(self,"选择输出文件夹")
        if not out: return
        self.btn_run.setEnabled(False)
        self.prog.setVisible(True)
        self.prog.setMaximum(len(self._batch_paths))
        self.prog.setValue(0)
        self._worker = BatchWorker(
            self._batch_paths, self._frame_rgba, self._template, out)
        self._worker.sig_progress.connect(self._on_progress)
        self._worker.sig_done.connect(self._on_done)
        self._worker.sig_error.connect(lambda m: self._status(f"⚠ {m}"))
        self._worker.start()

    def _on_progress(self, i, name):
        self.prog.setValue(i)
        self._status(f"合成中 ({i}/{len(self._batch_paths)}): {name}")
        if i-1 < self.lst_batch.count():
            self.lst_batch.setCurrentRow(i-1)

    def _on_done(self, saved):
        self.btn_run.setEnabled(True)
        self.prog.setVisible(False)
        self._status(f"✅ 完成，共输出 {saved} 张")
        QMessageBox.information(self,"完成",f"批量合成完成！\n共输出 {saved} 张。")


# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────

def main():
    import ctypes
    if sys.platform == "win32":
        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ralo.frame.v3")
        except: pass
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(17,17,19))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(216,216,224))
    p.setColor(QPalette.ColorRole.Base,            QColor(14,14,18))
    p.setColor(QPalette.ColorRole.Text,            QColor(192,192,208))
    p.setColor(QPalette.ColorRole.Button,          QColor(28,28,34))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(200,200,216))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(10,132,255))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255,255,255))
    app.setPalette(p)
    win = MainWindow(); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
