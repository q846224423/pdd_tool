@echo off
echo ==========================================
echo   开始批量打包：自定义 EXE 名称
echo ==========================================

:: 安装依赖
pip install pyinstaller openpyxl PyQt6 requests opencv-python

:: 清理旧文件
rmdir /s /q build
rmdir /s /q dist
del *.spec

:: ai标题
echo 正在打包 ai_title.exe ...
pyinstaller --noconsole --onefile --icon=logo.ico -n "ai_title" ai_title.py

:: 分类工具
echo 正在打包 分类工具.exe ...
pyinstaller --noconsole --onefile --icon=logo.ico -n "photo_sort" photo_sorter.py

:: AI处理（包含cv2）
echo 正在打包 AI_PS.exe ...
pyinstaller --noconsole --onefile --collect-all cv2 --icon=logo.ico -n "AI_PS" photo_processor.py

:: 测试工具
echo 正在打包 ai_mb.exe ...
pyinstaller --noconsole --onefile --icon=logo.ico -n "ai_mb" template_tool.py

echo ==========================================
echo   打包全部完成！1
echo ==========================================
pause
