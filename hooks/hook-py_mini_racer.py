from PyInstaller.utils.hooks import get_package_paths
import os

# 获取 py_mini_racer 的路径
_, pkg_dir = get_package_paths('py_mini_racer')
dll_path = os.path.join(pkg_dir, 'mini_racer.dll')

# 关键：将 DLL 放到根目录，这样单文件模式下解压到临时目录根目录
binaries = [(dll_path, '.')]

# 也添加为数据文件
datas = [(dll_path, '.')]
