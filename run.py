import sys
from src.scheduler import Scheduler
from src.gui import run_gui

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--gui':
        run_gui()
    elif len(sys.argv) > 1 and sys.argv[1] == '--cli':
        Scheduler().run()
    else:
        print("""
使用方法:
  python run.py --gui   启动图形界面 (推荐)
  python run.py --cli   启动命令行模式
        """)
        choice = input("请选择模式 (1=GUI, 2=CLI, 默认=GUI): ").strip()
        if choice == '2':
            Scheduler().run()
        else:
            run_gui()
