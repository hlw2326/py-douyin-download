# 运行时 hook：修复 py_mini_racer DLL 路径
import os
import sys

if hasattr(sys, '_MEIPASS'):
    # PyInstaller 打包后的临时目录
    temp_dir = sys._MEIPASS

    # 将临时目录添加到 DLL 搜索路径（Windows）
    if os.name == 'nt':
        # 方法 1：使用 os.add_dll_directory（Python 3.8+）
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(temp_dir)

        # 方法 2：添加到 PATH 环境变量
        os.environ['PATH'] = temp_dir + os.pathsep + os.environ.get('PATH', '')
