@echo off
chcp 65001 >nul
echo ========================================
echo 抖音下载器 - 打包调试脚本
echo ========================================
echo.

echo [1/3] 检查 PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller 未安装，正在安装...
    pip install pyinstaller
) else (
    echo PyInstaller 已安装
)
echo.

echo [2/3] 清理旧的打包文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo 清理完成
echo.

echo [3/3] 开始打包 (简化版)...
pyinstaller build_simple.spec
echo.

if exist "dist\抖音下载器.exe" (
    echo ========================================
    echo 打包成功！
    echo 输出文件: dist\抖音下载器.exe
    echo ========================================
    echo.
    echo 测试运行 exe...
    echo.
    "dist\抖音下载器.exe" --help
) else (
    echo ========================================
    echo 打包失败，请检查上方错误信息
    echo ========================================
)
echo.
pause
