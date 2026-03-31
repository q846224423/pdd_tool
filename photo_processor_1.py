"""
主图合成工具 v5  —  支持导入相框坐标模板 + 全局记忆
pip install PyQt6 pillow numpy
"""

import sys, os, json, ctypes, logging
from pathlib import Path
from typing  import Optional, List

import numpy as np
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QTextEdit, QFileDialog, QFrame,
    QStatusBar, QMessageBox, QAbstractItemView, QSplitter,
    QSpinBox, QComboBox, QScrollArea
)
from PyQt6.QtCore  import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui   import QColor, QPalette

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
APP_ORG  = "Ralo"
APP_NAME = "CompositeMain"

QSS = """
* { box-sizing: border-box; outline: none; }
QMainWindow { background-color: #111113; }
QWidget {
    color: #dddde5;
    font-family: "Microsoft YaHei UI","PingFang SC","SF Pro Display",sans-serif;
    font-size: 13px; background: transparent;
}
QWidget#centralWidget { background-color: #111113; }
QWidget#leftPanel  { background: #161619; border: 1px solid #24242c; border-radius: 12px; }
QWidget#rightPanel { background: #161619; border: 1px solid #24242c; border-radius: 12px; }

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 5px; }
QScrollBar::handle:vertical { background: #2a2a36; border-radius: 2px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #3a3a48; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QLineEdit {
    background-color: #1e1e24; border: 1px solid #2c2c36;
    border-radius: 7px; padding: 8px 10px; color: #aaaab8; font-size: 12px;
}
QLineEdit:focus { border-color: #2c2c36; }

QListWidget {
    background-color: #1a1a20; border: 1px solid #2c2c36;
    border-radius: 8px; color: #c0c0cc; outline: none; padding: 3px; font-size: 12px;
}
QListWidget::item { padding: 7px 10px; border-radius: 5px; color: #c0c0cc; }
QListWidget::item:selected { background-color: #0a84ff; color: #fff; }
QListWidget::item:hover:!selected { background-color: #2a2a36; }

QPushButton {
    background-color: #2c2c36; color: #e0e0e0;
    border-radius: 7px; padding: 8px 14px;
    font-weight: 600; font-size: 13px; border: none; outline: none;
}
QPushButton:hover { background-color: #3a3a48; }

/* ========================================================= */
/* 开始批量合成按钮 - 立体渐变物理按压样式 */
/* ========================================================= */
QPushButton#btnStart {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2591ff, stop:1 #0073ea);
    border: 1px solid #005bb8;      
    border-top: 1px solid #5ab0ff;  
    color: #ffffff;                 
    font-size: 15px; 
    font-weight: 800;               
    letter-spacing: 2px;            
    padding: 12px 0px;              
    border-radius: 8px;             
}
QPushButton#btnStart:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #47a3ff, stop:1 #0a80f5);
    border-top: 1px solid #7bc0ff;  
}
QPushButton#btnStart:pressed { 
    background: #005ac8;      
    border: 1px solid #00408a;      
    padding-top: 14px; 
    padding-bottom: 10px; 
}
QPushButton#btnStart:disabled { 
    background: #24242c; 
    border: 1px solid #1e1e28;
    color: #505060; 
}
/* ========================================================= */

QPushButton#btnBrowse {
    background-color: #2a2a36; color: #c0c0d0;
    border: 1px solid #4a4a5a; font-size: 12px; padding: 8px 14px;
}
QPushButton#btnBrowse:hover { background-color: #3a3a48; color: #fff; border-color: #6a6a7a; }

QPushButton#btnAdd {
    background-color: rgba(40,196,84,0.15); color: #4ade80;
    border: 1px solid rgba(40,196,84,0.4); font-size: 12px; font-weight: 600;
}
QPushButton#btnAdd:hover { background-color: rgba(40,196,84,0.25); border-color: #4ade80; }

QPushButton#btnDel {
    background-color: rgba(240,64,48,0.15); color: #f87171;
    border: 1px solid rgba(240,64,48,0.4); font-size: 12px; font-weight: 600;
}
QPushButton#btnDel:hover { background-color: rgba(240,64,48,0.25); border-color: #f87171; }

QPushButton#btnImport {
    background-color: rgba(191,90,242,0.13); color: #d070f0;
    border: 1px solid rgba(191,90,242,0.35); font-size: 12px; font-weight: 600;
    padding: 8px 0; border-radius: 7px;
}
QPushButton#btnImport:hover { background-color: rgba(191,90,242,0.24); border-color: #c070e0; }

QPushButton#btnClear {
    background-color: rgba(255,255,255,0.05); color: #a0a0b0;
    border: 1px solid rgba(255,255,255,0.15); padding: 4px 12px;
    font-size: 11px; border-radius: 6px;
}
QPushButton#btnClear:hover { background-color: rgba(255,255,255,0.1); color: #fff; }

QWidget#coordBox {
    background: #1a1a26; border: 1px solid #2c2c42;
    border-radius: 8px;
}
QWidget#botArea { background: transparent; }

QComboBox {
    background-color: #1e1e24; border: 1px solid #2c2c36;
    border-radius: 7px; padding: 7px 10px; color: #aaaab8; font-size: 12px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #20202a; border: 1px solid #32323e;
    color: #c0c0d0; selection-background-color: #0a84ff; outline: none;
}

QSpinBox {
    background-color: #1e1e24; border: 1px solid #2c2c36;
    border-radius: 7px; padding: 7px 8px; color: #aaaab8; font-size: 12px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: #2a2a36; border: none; width: 16px; border-radius: 3px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #4a4a5a; }

QProgressBar {
    background-color: #1a1a22; border: 1px solid #24242c;
    border-radius: 3px; height: 6px; color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0a84ff,stop:1 #5ac8fa);
    border-radius: 2px;
}

QTextEdit {
    background-color: #0e0e14; border: 1px solid #1e1e28;
    border-radius: 9px; color: #808090;
    font-family: "Cascadia Code","Consolas","Courier New",monospace;
    font-size: 11.5px; padding: 10px;
}

QStatusBar {
    background-color: #0c0c12; border-top: 1px solid #1a1a22;
    color: #606070; font-size: 11px; padding: 2px 14px;
}
QFrame#divider { background-color: #2c2c36; border: none; max-height: 1px; }
"""

def load_smart_template(tpl_path: str) -> Image.Image:
    img = Image.open(tpl_path)

    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        rgba_img = img.convert("RGBA")
        extrema = rgba_img.getextrema()
        if extrema[3][0] < 255:
            return rgba_img

    rgba = img.convert("RGBA")
    arr  = np.array(rgba)
    corners = [arr[0,0,:3], arr[0,-1,:3], arr[-1,0,:3], arr[-1,-1,:3]]
    bg_color = np.mean(corners, axis=0).astype(np.uint8)
    diff = np.abs(arr[:,:,:3].astype(int) - bg_color.astype(int))
    mask = np.all(diff < 30, axis=2)
    arr[mask, 3] = 0
    return Image.fromarray(arr, "RGBA")


def composite_from_template(photo: Image.Image, tpl_path: str,
                            cx: float, cy: float, scale: float,
                            out_w: int, out_h: int, dpi: int) -> Image.Image:
    tpl = load_smart_template(tpl_path)
    tw, th = tpl.size

    alpha = np.array(tpl)[:, :, 3]
    rows = np.any(alpha == 0, axis=1)
    cols = np.any(alpha == 0, axis=0)
    if rows.any() and cols.any():
        y1, y2 = int(np.where(rows)[0][0]), int(np.where(rows)[0][-1])
        x1, x2 = int(np.where(cols)[0][0]), int(np.where(cols)[0][-1])
    else:
        x1, y1, x2, y2 = 0, 0, tw, th

    hw, hh = x2 - x1, y2 - y1

    p = photo.convert("RGBA")
    sc = max(hw / p.width, hh / p.height)
    p = p.resize((int(p.width*sc), int(p.height*sc)), Image.LANCZOS)
    lc, tc = (p.width-hw)//2, (p.height-hh)//2
    p = p.crop((lc, tc, lc+hw, tc+hh))

    canvas = Image.new("RGBA", (tw, th), (255,255,255,255))
    canvas.paste(p, (x1, y1))
    result = Image.alpha_composite(canvas, tpl).convert("RGB")
    return result.resize((out_w, out_h), Image.LANCZOS)


def composite_fixed_coords(photo: Image.Image, tpl_path: str,
                           coords: list,
                           out_w: int, out_h: int, dpi: int) -> Image.Image:
    tpl = load_smart_template(tpl_path)
    tw, th = tpl.size
    xs = [p[0] for p in coords]; ys = [p[1] for p in coords]
    x1,y1,x2,y2 = min(xs),min(ys),max(xs),max(ys)
    hw, hh = x2-x1, y2-y1
    p = photo.convert("RGBA")
    sc = max(hw/p.width, hh/p.height)
    p = p.resize((int(p.width*sc), int(p.height*sc)), Image.LANCZOS)
    lc,tc = (p.width-hw)//2, (p.height-hh)//2
    p = p.crop((lc, tc, lc+hw, tc+hh))
    canvas = Image.new("RGBA",(tw,th),(255,255,255,255))
    canvas.paste(p,(x1,y1))
    return Image.alpha_composite(canvas,tpl).convert("RGB").resize((out_w,out_h),Image.LANCZOS)


class Worker(QThread):
    sig_log  = pyqtSignal(str)
    sig_prog = pyqtSignal(int, int)
    sig_done = pyqtSignal(int, int)

    def __init__(self, inp, out, templates, out_w, out_h, dpi, quality,
                 coord_mode, cx, cy, scale, fixed_coords):
        super().__init__()
        self.inp, self.out = inp, out
        self.templates = templates
        self.out_w, self.out_h, self.dpi, self.quality = out_w, out_h, dpi, quality
        self.coord_mode   = coord_mode
        self.cx, self.cy, self.scale = cx, cy, scale
        self.fixed_coords = fixed_coords

    def run(self):
        files = [f for f in Path(self.inp).iterdir()
                 if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("主图_")]
        total = len(files); ok = fail = 0
        Path(self.out).mkdir(parents=True, exist_ok=True)
        for i, src in enumerate(files):
            self.sig_log.emit(f"\n── [{i+1}/{total}]  {src.name}")
            try:
                photo = Image.open(src).convert("RGB")
                for tp_str in self.templates:
                    tp = Path(tp_str)
                    if not tp.exists():
                        self.sig_log.emit(f"⚠️  模板不存在: {tp.name}"); continue
                    suf  = f"_{tp.stem}" if len(self.templates) > 1 else ""
                    name = f"主图_{src.stem}{suf}.jpg"
                    self.sig_log.emit(f"🖼   {tp.name}  →  {name}")
                    if self.coord_mode == "template":
                        r = composite_from_template(
                            photo, tp_str, self.cx, self.cy, self.scale,
                            self.out_w, self.out_h, self.dpi)
                    else:
                        r = composite_fixed_coords(
                            photo, tp_str, self.fixed_coords,
                            self.out_w, self.out_h, self.dpi)
                    r.save(str(Path(self.out)/name), "JPEG",
                           quality=self.quality, dpi=(self.dpi,self.dpi))
                    self.sig_log.emit(f"✅  {name}")
                ok += 1
            except Exception as e:
                self.sig_log.emit(f"❌  {e}"); fail += 1
            self.sig_prog.emit(i+1, total)
        self.sig_done.emit(ok, fail)


class NoScrollSpinBox(QSpinBox):
    def wheelEvent(self, e): e.ignore()

class NoScrollComboBox(QComboBox):
    def wheelEvent(self, e): e.ignore()

class StatCard(QFrame):
    def __init__(self, title, val="—", color="#0a84ff", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self._color = color; self._apply()
        lay = QVBoxLayout(self); lay.setContentsMargins(10,14,10,14); lay.setSpacing(4)
        self._v = QLabel(val); self._v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._v.setStyleSheet(f"color:{color};font-size:28px;font-weight:800;background:transparent;border:none;")
        t = QLabel(title); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("color:#606070;font-size:10px;font-weight:600;letter-spacing:2px;background:transparent;border:none;")
        lay.addWidget(self._v); lay.addWidget(t)

    def _apply(self):
        self.setStyleSheet(f"QFrame#statCard{{background:#181820;border:1px solid #24242e;border-top:2px solid {self._color};border-radius:10px;}}")

    def set_value(self, v): self._v.setText(str(v))

class PathRow(QWidget):
    def __init__(self, icon, placeholder, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(8)
        ico = QLabel(icon); ico.setFixedWidth(20)
        ico.setStyleSheet("font-size:15px;background:transparent;color:#707080;")
        self.edit = QLineEdit(); self.edit.setPlaceholderText(placeholder)
        self.edit.setReadOnly(True)
        btn = QPushButton("浏览"); btn.setObjectName("btnBrowse")
        btn.setFixedWidth(54); btn.clicked.connect(self._browse)
        lay.addWidget(ico); lay.addWidget(self.edit,1); lay.addWidget(btn)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self,"选择文件夹")
        if d: self.edit.setText(d)

    def path(self): return self.edit.text().strip()
    def set_path(self, p): self.edit.setText(p)

def divider():
    f = QFrame(); f.setObjectName("divider"); f.setFrameShape(QFrame.Shape.HLine); return f

def sec(text):
    l = QLabel(text)
    l.setStyleSheet("color:#606070;font-size:10px;font-weight:700;letter-spacing:2.5px;background:transparent;")
    return l


class MainWindow(QMainWindow):
    _LC = {
        "✅":"#4ade80","❌":"#f87171","⚠️":"#fbbf24",
        "🚀":"#38bdf8","──":"#404050","🏁":"#c084fc","🖼":"#818cf8",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("主图合成工具")
        self.setMinimumSize(860, 620)
        self.resize(1020, 720)
        self.templates: List[str] = []
        self._worker: Optional[Worker] = None

        self._coord_mode   = "fixed"
        self._tpl_cx       = 0.5
        self._tpl_cy       = 0.5
        self._tpl_scale    = 0.4
        self._fixed_coords = [(316,195),(967,194),(965,1138),(316,1130)]
        self._tpl_json_path = ""

        self._settings = QSettings(APP_ORG, APP_NAME)
        self._build_ui()
        self.setStyleSheet(QSS)
        self.setStatusBar(QStatusBar())
        self._load_settings()
        self.statusBar().showMessage("就绪")

    def _load_settings(self):
        s = self._settings
        inp = s.value("inp_dir", "")
        out = s.value("out_dir", "")
        if inp: self.row_in.set_path(inp)
        if out: self.row_out.set_path(out)

        saved_tpls = s.value("templates", [])
        if isinstance(saved_tpls, str): saved_tpls = [saved_tpls]
        for f in saved_tpls:
            if Path(f).exists() and f not in self.templates:
                self.templates.append(f)
                self.tpl_list.addItem(QListWidgetItem(f"  {Path(f).name}"))
        self.c_tpl.set_value(len(self.templates))

        tpl_json = s.value("tpl_json_path","")
        if tpl_json and Path(tpl_json).exists():
            self._load_tpl_json(tpl_json, silent=True)

        idx = s.value("preset_idx", 0, type=int)
        self.cmb.setCurrentIndex(idx)
        self.spn_w.setValue(s.value("out_w", 800, type=int))
        self.spn_h.setValue(s.value("out_h", 800, type=int))
        self.spn_dpi.setValue(s.value("out_dpi", 300, type=int))
        self.spn_q.setValue(s.value("out_q", 95, type=int))

    def _save_settings(self):
        s = self._settings
        s.setValue("inp_dir",      self.row_in.path())
        s.setValue("out_dir",      self.row_out.path())
        s.setValue("templates",    self.templates)
        s.setValue("tpl_json_path",self._tpl_json_path)
        s.setValue("preset_idx",   self.cmb.currentIndex())
        s.setValue("out_w",        self.spn_w.value())
        s.setValue("out_h",        self.spn_h.value())
        s.setValue("out_dpi",      self.spn_dpi.value())
        s.setValue("out_q",        self.spn_q.value())

    def closeEvent(self, e):
        self._save_settings(); super().closeEvent(e)

    def _build_ui(self):
        cw = QWidget(); cw.setObjectName("centralWidget")
        self.setCentralWidget(cw)
        root = QVBoxLayout(cw)
        root.setContentsMargins(16,14,16,10); root.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("主图合成工具"); t.setStyleSheet("color:#fff;font-size:16px;font-weight:700;")
        s = QLabel("批量 · 多模板 · 300 DPI"); s.setStyleSheet("color:#606070;font-size:11px;")
        hdr.addWidget(t); hdr.addStretch(); hdr.addWidget(s)
        root.addLayout(hdr)

        cards = QHBoxLayout(); cards.setSpacing(8)
        self.c_total = StatCard("待处理","—","#0a84ff")
        self.c_ok    = StatCard("已成功","—","#28c454")
        self.c_fail  = StatCard("失败","—","#f04030")
        self.c_tpl   = StatCard("模板","0","#bf5af2")
        for c in (self.c_total,self.c_ok,self.c_fail,self.c_tpl):
            cards.addWidget(c,1)
        root.addLayout(cards)

        sp = QSplitter(Qt.Orientation.Horizontal); sp.setHandleWidth(1)
        sp.setStyleSheet("QSplitter::handle{background:#1e1e28;}")

        left_outer = QWidget()
        lo = QVBoxLayout(left_outer); lo.setContentsMargins(0,0,6,0); lo.setSpacing(0)
        left = QWidget(); left.setObjectName("leftPanel")
        ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        si = QWidget(); sl = QVBoxLayout(si)
        sl.setContentsMargins(16,16,16,12); sl.setSpacing(0)

        sl.addWidget(sec("路  径")); sl.addSpacing(10)
        self.row_in  = PathRow("📂","输入文件夹（照片）")
        self.row_out = PathRow("💾","输出文件夹")
        sl.addWidget(self.row_in); sl.addSpacing(8); sl.addWidget(self.row_out)
        sl.addSpacing(18); sl.addWidget(divider()); sl.addSpacing(18)

        sl.addWidget(sec("模  板")); sl.addSpacing(10)
        btn_tpl = QHBoxLayout(); btn_tpl.setSpacing(8)

        self.btn_add = QPushButton("＋  添加模板"); self.btn_add.setObjectName("btnAdd"); self.btn_add.setFixedHeight(36)
        self.btn_sel_all = QPushButton("☑  全选"); self.btn_sel_all.setObjectName("btnBrowse"); self.btn_sel_all.setFixedHeight(36)
        self.btn_del = QPushButton("－  删除选中"); self.btn_del.setObjectName("btnDel"); self.btn_del.setFixedHeight(36)

        btn_tpl.addWidget(self.btn_add,3); btn_tpl.addWidget(self.btn_sel_all,2); btn_tpl.addWidget(self.btn_del,2)
        sl.addLayout(btn_tpl); sl.addSpacing(8)

        self.tpl_list = QListWidget(); self.tpl_list.setFixedHeight(110)
        self.tpl_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        sl.addWidget(self.tpl_list)

        # 核心修正位置：必须在 tpl_list 创建后，才能进行事件绑定
        self.btn_add.clicked.connect(self._add_tpl)
        self.btn_sel_all.clicked.connect(self.tpl_list.selectAll)
        self.btn_del.clicked.connect(self._del_tpl)

        sl.addSpacing(18); sl.addWidget(divider()); sl.addSpacing(18)

        sl.addWidget(sec("照片放置坐标")); sl.addSpacing(10)

        self.btn_import_coord = QPushButton("📥  从相框工具导入坐标模板 (.json)")
        self.btn_import_coord.setObjectName("btnImport")
        self.btn_import_coord.setFixedHeight(36)
        self.btn_import_coord.clicked.connect(self._import_coord)
        sl.addWidget(self.btn_import_coord); sl.addSpacing(8)

        coord_box = QWidget(); coord_box.setObjectName("coordBox")
        cb_lay = QVBoxLayout(coord_box); cb_lay.setContentsMargins(12,10,12,10); cb_lay.setSpacing(4)

        self.lbl_coord_mode = QLabel("当前模式：固定像素坐标（默认）")
        self.lbl_coord_mode.setStyleSheet("color:#8888a0;font-size:11px;background:transparent;font-weight:600;")
        self.lbl_coord_file = QLabel("未导入")
        self.lbl_coord_file.setStyleSheet("color:#505068;font-size:10.5px;background:transparent;")
        self.lbl_coord_file.setWordWrap(True)
        self.lbl_coord_detail = QLabel("")
        self.lbl_coord_detail.setStyleSheet("color:#404055;font-size:10px;background:transparent;")
        self.lbl_coord_detail.setWordWrap(True)
        cb_lay.addWidget(self.lbl_coord_mode)
        cb_lay.addWidget(self.lbl_coord_file)
        cb_lay.addWidget(self.lbl_coord_detail)
        sl.addWidget(coord_box)
        sl.addSpacing(18); sl.addWidget(divider()); sl.addSpacing(18)

        sl.addWidget(sec("输出规格")); sl.addSpacing(10)
        self.cmb = NoScrollComboBox()
        for p in ["正方形  800×800","正方形  1000×1000","正方形  1200×1200",
                  "竖版 5:7  1500×2100","横版 7:5  2100×1500","自定义…"]:
            self.cmb.addItem(p)
        self.cmb.currentIndexChanged.connect(self._on_preset)
        sl.addWidget(self.cmb); sl.addSpacing(10)

        g1 = QHBoxLayout(); g1.setSpacing(10)
        g2 = QHBoxLayout(); g2.setSpacing(10)

        def mk_spin(lo,hi,val,suf):
            s=NoScrollSpinBox(); s.setRange(lo,hi); s.setValue(val); s.setSuffix(suf); return s

        self.spn_w   = mk_spin(100,9999,800," px")
        self.spn_h   = mk_spin(100,9999,800," px")
        self.spn_dpi = mk_spin(72,600,300," DPI")
        self.spn_q   = mk_spin(80,100,95," %")

        def labeled(lt,widget):
            w=QWidget(); r=QHBoxLayout(w); r.setContentsMargins(0,0,0,0); r.setSpacing(6)
            l=QLabel(lt); l.setStyleSheet("color:#707080;font-size:11px;background:transparent;"); l.setFixedWidth(30)
            r.addWidget(l); r.addWidget(widget,1); return w

        g1.addWidget(labeled("宽",self.spn_w),1); g1.addWidget(labeled("高",self.spn_h),1)
        g2.addWidget(labeled("DPI",self.spn_dpi),1); g2.addWidget(labeled("品质",self.spn_q),1)
        sl.addLayout(g1); sl.addSpacing(8); sl.addLayout(g2); sl.addSpacing(16)
        sl.addStretch()

        scroll.setWidget(si); ll.addWidget(scroll,1)

        bot = QWidget()
        bot.setObjectName("botArea")
        bl = QVBoxLayout(bot); bl.setContentsMargins(16,8,16,14); bl.setSpacing(8)

        self.btn_start = QPushButton("🚀  开始批量合成")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self._start)

        self.prog = QProgressBar(); self.prog.setFixedHeight(6); self.prog.setTextVisible(False); self.prog.setVisible(False)

        bl.addWidget(self.btn_start); bl.addWidget(self.prog)
        ll.addWidget(bot); lo.addWidget(left); sp.addWidget(left_outer)

        right_outer = QWidget()
        ro = QVBoxLayout(right_outer); ro.setContentsMargins(6,0,0,0); ro.setSpacing(0)
        right = QWidget(); right.setObjectName("rightPanel")
        rl = QVBoxLayout(right); rl.setContentsMargins(16,14,16,14); rl.setSpacing(10)
        log_hdr = QHBoxLayout()
        log_hdr.addWidget(sec("处 理 日 志")); log_hdr.addStretch()
        bc = QPushButton("清空"); bc.setObjectName("btnClear")
        bc.clicked.connect(lambda: self.log_box.clear())
        log_hdr.addWidget(bc); rl.addLayout(log_hdr)
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("日志将在这里实时显示…")
        rl.addWidget(self.log_box,1); ro.addWidget(right); sp.addWidget(right_outer)

        sp.setSizes([390,630]); root.addWidget(sp,1)

    _P = {0:(800,800),1:(1000,1000),2:(1200,1200),3:(1500,2100),4:(2100,1500)}
    def _on_preset(self,idx):
        if idx in self._P:
            w,h=self._P[idx]
            for s,v in [(self.spn_w,w),(self.spn_h,h)]:
                s.blockSignals(True); s.setValue(v); s.blockSignals(False)

    def _add_tpl(self):
        fs,_=QFileDialog.getOpenFileNames(self,"选择模板图",filter="图片 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*.*)")
        for f in fs:
            if f not in self.templates:
                self.templates.append(f)
                self.tpl_list.addItem(QListWidgetItem(f"  {Path(f).name}"))
        self.c_tpl.set_value(len(self.templates))

    def _del_tpl(self):
        for item in reversed(self.tpl_list.selectedItems()):
            r=self.tpl_list.row(item); self.tpl_list.takeItem(r); self.templates.pop(r)
        self.c_tpl.set_value(len(self.templates))

    def _import_coord(self):
        p,_=QFileDialog.getOpenFileName(self,"选择相框工具导出的坐标模板",filter="JSON (*.json)")
        if not p: return
        self._load_tpl_json(p, silent=False)

    def _load_tpl_json(self, path: str, silent=False):
        try:
            with open(path,"r",encoding="utf-8") as f:
                d = json.load(f)
            cx    = float(d.get("cx",    0.5))
            cy    = float(d.get("cy",    0.5))
            scale = float(d.get("scale", 0.4))
            ref_w = int(d.get("ref_w", 0))
            ref_h = int(d.get("ref_h", 0))
            left  = int(d.get("left",  0))
            top   = int(d.get("top",   0))
            right = int(d.get("right", 0))
            bottom= int(d.get("bottom",0))
            fw    = int(d.get("frame_w",0))
            fh    = int(d.get("frame_h",0))

            self._tpl_cx, self._tpl_cy, self._tpl_scale = cx, cy, scale
            self._coord_mode    = "template"
            self._tpl_json_path = path

            self.lbl_coord_mode.setText("✅  坐标模式：相框比例坐标（已导入）")
            self.lbl_coord_mode.setStyleSheet("color:#4ade80;font-size:11px;background:transparent;font-weight:600;")
            self.lbl_coord_file.setText(f"文件：{Path(path).name}")
            self.lbl_coord_detail.setText(
                f"cx={cx:.3f}  cy={cy:.3f}  scale={scale:.3f}\n"
                f"参考图 {ref_w}×{ref_h}  |  "
                f"左{left} 右{right} 上{top} 下{bottom} px  |  相框 {fw}×{fh}")
            if not silent:
                self.statusBar().showMessage(f"✅ 坐标模板已导入: {Path(path).name}")
        except Exception as e:
            if not silent:
                QMessageBox.warning(self,"导入失败",f"读取坐标模板失败：\n{e}")

    def _log(self, msg):
        color="#808090"
        for k,c in self._LC.items():
            if msg.startswith(k): color=c; break
        self.log_box.append(f'<span style="color:{color};font-family:Consolas,monospace;">{msg}</span>')
        sb=self.log_box.verticalScrollBar(); sb.setValue(sb.maximum())

    def _on_prog(self,cur,total):
        self.prog.setMaximum(total); self.prog.setValue(cur)
        self.statusBar().showMessage(f"合成中  {cur} / {total}")

    def _on_done(self,ok,fail):
        self.c_ok.set_value(ok); self.c_fail.set_value(fail)
        self.btn_start.setEnabled(True); self.btn_start.setText("开始批量合成")
        self.prog.setVisible(False)
        self.statusBar().showMessage(f"完成  ·  成功 {ok}  失败 {fail}")
        self._log(f"\n🏁  完成 — 成功 {ok} 张  失败 {fail} 张")
        msg = f"成功合成 {ok} 张\n\n输出目录：\n{self.row_out.path()}"
        (QMessageBox.information if fail==0 else QMessageBox.warning)(
            self,"完成", msg if fail==0 else f"成功 {ok}  失败 {fail}\n\n{self.row_out.path()}")

    def _start(self):
        inp=self.row_in.path(); out=self.row_out.path()
        if not inp or not os.path.isdir(inp):
            QMessageBox.warning(self,"提示","请选择输入文件夹"); return
        if not out:
            QMessageBox.warning(self,"提示","请选择输出文件夹"); return
        if not self.templates:
            QMessageBox.warning(self,"提示","请添加模板"); return
        files=[f for f in Path(inp).iterdir()
               if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("主图_")]
        if not files:
            QMessageBox.warning(self,"提示","未找到图片"); return

        selected_items = self.tpl_list.selectedItems()
        if selected_items:
            active_templates = [self.templates[self.tpl_list.row(i)] for i in selected_items]
        else:
            active_templates = self.templates

        if self._coord_mode == "template":
            mode_desc = f"比例坐标  cx={self._tpl_cx:.3f}  cy={self._tpl_cy:.3f}  scale={self._tpl_scale:.3f}"
        else:
            mode_desc = f"固定像素坐标  {self._fixed_coords}"

        n=len(files)
        self.c_total.set_value(n); self.c_ok.set_value("—"); self.c_fail.set_value("—")
        self.prog.setVisible(True)
        self.prog.setValue(0); self.prog.setMaximum(n)
        self.btn_start.setEnabled(False); self.btn_start.setText("合成中…")

        self._log(f"🚀  开始  {n} 张 · 使用 {len(active_templates)} 个模板")
        self._log(f"    坐标模式: {mode_desc}")

        self._worker=Worker(
            inp, out, active_templates,
            self.spn_w.value(), self.spn_h.value(),
            self.spn_dpi.value(), self.spn_q.value(),
            self._coord_mode,
            self._tpl_cx, self._tpl_cy, self._tpl_scale,
            self._fixed_coords
        )
        self._worker.sig_log.connect(self._log)
        self._worker.sig_prog.connect(self._on_prog)
        self._worker.sig_done.connect(self._on_done)
        self._worker.start()
        self._save_settings()


def main():
    if sys.platform=="win32":
        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ralo.composite.v5")
        except: pass
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass

    app=QApplication(sys.argv)
    app.setStyle("Fusion")
    p=QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(17,17,19))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(221,221,229))
    p.setColor(QPalette.ColorRole.Base,            QColor(14,14,18))
    p.setColor(QPalette.ColorRole.Text,            QColor(200,200,212))
    p.setColor(QPalette.ColorRole.Button,          QColor(28,28,34))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(200,200,212))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(10,132,255))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255,255,255))
    app.setPalette(p)
    win=MainWindow(); win.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()
