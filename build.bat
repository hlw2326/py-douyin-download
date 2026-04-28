@echo off
chcp 65001 >nul
echo ========================================
echo 抖音下载器 - 打包脚本
echo ========================================
echo.

echo 请选择打包方式:
echo   1. 单文件 exe (一个文件，但可能有 DLL 问题)
echo   2. 文件夹模式 (推荐，更稳定)
echo.
set /p choice="请输入选择 (1 或 2，默认 2): "

if "%choice%"=="" set choice=2

echo.
echo [1/4] 检查 PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller 未安装，正在安装...
    pip install pyinstaller
) else (
    echo PyInstaller 已安装
)
echo.

echo [2/4] 清理旧的打包文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo 清理完成
echo.

if "%choice%"=="1" (
    echo [3/4] 开始打包 (单文件模式)...
    pyinstaller build_exe.spec
) else (
    echo [3/4] 开始打包 (文件夹模式)...
    pyinstaller build_folder.spec
)
echo.

if "%choice%"=="1" (
    if exist "dist\抖音下载器.exe" (
        echo ========================================
        echo 打包成功！
        echo 输出文件: dist\抖音下载器.exe
        echo ========================================
    ) else (
        echo ========================================
        echo 打包失败，请尝试文件夹模式 (选项 2)
        echo ========================================
    )
) else (
    if exist "dist\抖音下载器\抖音下载器.exe" (
        echo ========================================
        echo 打包成功！
        echo 输出目录: dist\抖音下载器\
        echo 主文件: dist\抖音下载器\抖音下载器.exe
        echo ========================================
    ) else (
        echo ========================================
        echo 打包失败，请检查错误信息
        echo ========================================
    )
)
echo.
echo 按任意键打开输出文件夹...
pause >nul
explorer dist
