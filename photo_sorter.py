import os
import sys
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal

CONFIG_FILE = "renamer_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"last_prefix": ""}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except:
        pass

class RenameWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, target_dir, suffix):
        super().__init__()
        self.target_dir = target_dir
        self.suffix = suffix

    def run(self):
        renamed_count = 0
        counter = 1
        date_str = datetime.now().strftime("%Y%m%d")

        files = [f for f in os.listdir(self.target_dir) if os.path.isfile(os.path.join(self.target_dir, f))]

        for filename in files:
            file_path = os.path.join(self.target_dir, filename)
            ext = os.path.splitext(filename)[1].lower()

            if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']:
                continue

            while True:
                new_name = f"{self.suffix}_{date_str}_{counter:03d}{ext}"
                target_path = os.path.join(self.target_dir, new_name)
                if not os.path.exists(target_path) or target_path == file_path:
                    break
                counter += 1

            if target_path != file_path:
                try:
                    os.rename(file_path, target_path)
                    self.log_signal.emit(f"成功: {filename} -> {new_name}")
                    renamed_count += 1
                except Exception as e:
                    self.log_signal.emit(f"失败: {filename} ({str(e)})")
            counter += 1

        self.finished_signal.emit(renamed_count)

class PhotoRenamerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("照片批量重命名工具")
        self.resize(600, 450)
        self.setStyleSheet("""
            QWidget { background: #1E1F23; color: #F0F0F2; font-family: 'Microsoft YaHei UI'; font-size: 13px; }
            QLineEdit, QTextEdit { background: #26272C; border: 1px solid #3A3B42; border-radius: 6px; padding: 6px; }
            QPushButton { background: #26272C; border: 1px solid #3A3B42; border-radius: 6px; padding: 6px 16px; }
            QPushButton:hover { background: #2E2F35; border: 1px solid #4A4B52; }
            QPushButton#btn_primary { background: #07C160; border: none; font-weight: bold; color: white; }
            QPushButton#btn_primary:hover { background: #06AD56; }
            QPushButton#btn_primary:disabled { background: #0A3020; color: #2A6040; }
        """)

        self.config = load_config()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        top_layout = QHBoxLayout()
        self.path_entry = QLineEdit()
        self.path_entry.setPlaceholderText("请选择需要重命名的照片文件夹")
        self.path_entry.setReadOnly(True)
        top_layout.addWidget(self.path_entry, stretch=1)

        btn_browse = QPushButton("浏览")
        btn_browse.clicked.connect(self._browse_folder)
        top_layout.addWidget(btn_browse)
        layout.addLayout(top_layout)

        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("重命名首字母/前缀:"))
        self.prefix_input = QLineEdit(self.config.get("last_prefix", ""))
        self.prefix_input.setPlaceholderText("例如: zs")
        prefix_layout.addWidget(self.prefix_input, stretch=1)
        layout.addLayout(prefix_layout)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, stretch=1)

        self.btn_start = QPushButton("开始重命名")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.setFixedHeight(38)
        self.btn_start.clicked.connect(self._start_renaming)
        layout.addWidget(self.btn_start)

        self.worker = None

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择照片文件夹")
        if folder:
            self.path_entry.setText(folder)

    def _start_renaming(self):
        target_dir = self.path_entry.text().strip()
        if not target_dir or not os.path.exists(target_dir):
            QMessageBox.warning(self, "错误", "请先选择有效的文件夹！")
            return

        selected_prefix = self.prefix_input.text().strip()
        if not selected_prefix:
            QMessageBox.warning(self, "错误", "请填写重命名前缀！")
            return

        self.config["last_prefix"] = selected_prefix
        save_config(self.config)

        self.btn_start.setEnabled(False)
        self.btn_start.setText("处理中...")
        self.log_view.clear()
        self.log_view.append("开始执行重命名...\n")

        self.worker = RenameWorker(target_dir, selected_prefix)
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_finished(self, count):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("开始重命名")
        if count == 0:
            self.log_view.append("\n处理完成！没有找到可重命名的图片文件。")
        else:
            self.log_view.append(f"\n处理完成！共重命名了 {count} 个文件。")
        QMessageBox.information(self, "完成", f"重命名完成，共处理 {count} 张照片。")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhotoRenamerApp()
    window.show()
    sys.exit(app.exec())
