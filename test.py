import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QMessageBox, QTextEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from rembg import remove
from PIL import Image

class MattingThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, input_path, output_path):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path

    def run(self):
        try:
            self.log_signal.emit("正在进行智能抠图（首次运行会自动下载预训练模型）...")

            with open(self.input_path, 'rb') as i:
                input_data = i.read()

            output_data = remove(input_data)

            with open(self.output_path, 'wb') as o:
                o.write(output_data)

            self.log_signal.emit(f"处理成功！透明背景图片已保存至: {self.output_path}")
            self.finished_signal.emit(True, "处理完成")

        except Exception as e:
            self.log_signal.emit(f"发生错误: {str(e)}")
            self.finished_signal.emit(False, str(e))

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.input_path = ""
        self.output_path = ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('AI 智能抠图工具')
        self.resize(500, 350)

        layout = QVBoxLayout()

        self.btn_select = QPushButton('选择包含相框的图片')
        self.lbl_file = QLabel('未选择图片')
        self.btn_select.clicked.connect(self.select_image)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.btn_select)
        file_layout.addWidget(self.lbl_file)
        layout.addLayout(file_layout)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.btn_start = QPushButton('开始提取并背景透明化')
        self.btn_start.setMinimumHeight(40)
        self.btn_start.clicked.connect(self.start_processing)
        layout.addWidget(self.btn_start)

        self.setLayout(layout)

    def select_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if file_name:
            self.input_path = file_name
            self.lbl_file.setText(os.path.basename(file_name))

    def log_message(self, message):
        self.log_output.append(message)

    def process_finished(self, success, message):
        self.btn_start.setEnabled(True)
        if success:
            QMessageBox.information(self, "成功", "抠图完毕，背景已透明化！")
        else:
            QMessageBox.critical(self, "错误", f"处理失败:\n{message}")

    def start_processing(self):
        if not self.input_path:
            QMessageBox.warning(self, "提示", "请先选择需要处理的图片！")
            return

        self.btn_start.setEnabled(False)
        self.log_output.clear()
        self.log_message("初始化处理线程...")

        output_dir = os.path.dirname(self.input_path)
        base_name = os.path.splitext(os.path.basename(self.input_path))[0]
        self.output_path = os.path.join(output_dir, f"{base_name}_transparent.png")

        self.processor = MattingThread(self.input_path, self.output_path)
        self.processor.log_signal.connect(self.log_message)
        self.processor.finished_signal.connect(self.process_finished)
        self.processor.start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())