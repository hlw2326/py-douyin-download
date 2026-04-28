from rich import print
from rich.prompt import Prompt
from textwrap import dedent
import subprocess
from time import sleep
from random import randint

from .config import Account, load_settings, Cookie, Colors, PROJECT_ROOT
from .tool import Cleaner
from .download import Acquire, Download, Parse


class Scheduler:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.cookie = Cookie()
        self.cleaner = Cleaner()

    def _deal_account(self, num: int, account: Account):
        for i in (
            f'\n开始处理第 {num} 个账号' if num else '开始处理账号',
            f'账号标识：{account.mark or "空"}',
            f'最早发布日期：{account.earliest or "空"}，最晚发布日期：{account.latest or "空"}'
        ):
            print(f'[{Colors.CYAN}]{i}')
        items = Acquire().request_items(account.sec_user_id, account.earliest_date, self.settings, self.cookie)
        if items:
            print(f'[{Colors.CYAN}]\n开始提取作品数据')
            Parse.extract_account(account, items[0], self.cleaner)
            print(f'[{Colors.CYAN}]账号昵称：{account.name}；账号 ID：{account.id}')
            items = Parse.extract_items(items, account.earliest_date, account.latest_date,
                                        self.settings, self.cleaner)
            print(f'[{Colors.CYAN}]当前账号作品数量: {len(items)}')
            Download.download_files(items, account.id, account.mark,
                                    self.settings, self.cleaner, self.cookie)
            return True

    def _deal_accounts(self):
        accounts = self.settings.accounts
        print(f'[{Colors.CYAN}]共有 {len(accounts)} 个账号的作品等待下载')
        for num, account in enumerate(accounts, start=1):
            if num % 5 == 0:
                sleep_time = randint(20, 180)
                print(f'[{Colors.CYAN}]已处理 {num-1} 个账号，等待 {sleep_time} 秒后继续')
                sleep(sleep_time)
            self.cookie.update()
            self._deal_account_iterative(num, account)

    def run(self):
        tips = dedent(
            f'''
            {'='*25}
            1. 复制粘贴写入 Cookie
            2. 修改配置文件(Linux)
            {'='*25}
            3. 批量下载账号作品(配置文件)
            {'='*25}

            请选择运行模式：''')
        while (mode := Prompt.ask(f'[{Colors.CYAN}]{tips}', choices=['q', '1', '2', '3'], default='3')) != 'q':
            if mode == '1':
                self.cookie.input_save()
            elif mode == '2':
                if not (filepath := PROJECT_ROOT / 'settings_mine.json').exists():
                    filepath = PROJECT_ROOT / 'settings_default.json'
                subprocess.run(['xdg-open', str(filepath)])
                try:
                    subprocess.run(['xdg-open', str(PROJECT_ROOT / '已下载账号信息.json')])
                except:
                    pass
                input()
                self.settings = load_settings()
            elif mode == '3':
                self.cookie.load_cookies()
                self._deal_accounts()
        print(f'[{Colors.WHITE}]程序结束运行')

    def _deal_account_iterative(self, num: int, account: Account):
        '''逐页获取并下载模式'''
        for i in (
            f'\n开始处理第 {num} 个账号（逐页模式）' if num else '开始处理账号（逐页模式）',
            f'账号标识：{account.mark or "空"}',
            f'最早发布日期：{account.earliest or "空"}，最晚发布日期：{account.latest or "空"}'
        ):
            print(f'[{Colors.CYAN}]{i}')

        acquire = Acquire()
        account_extracted = False
        next_video_num = 1  # 下一个视频序号

        # 逐页获取并下载
        for items_page, page_num in acquire.request_items_iterative(
            account.sec_user_id, account.earliest_date, self.settings, self.cookie
        ):
            if not items_page:
                continue

            # 第一次提取账号信息
            if not account_extracted:
                print(f'[{Colors.CYAN}]\n开始提取账号信息')
                Parse.extract_account(account, items_page[0], self.cleaner)
                print(f'[{Colors.CYAN}]账号昵称：{account.name}；账号 ID：{account.id}')
                account_extracted = True

            # 提取这一页的作品数据
            items = Parse.extract_items(items_page, account.earliest_date, account.latest_date,
                                       self.settings, self.cleaner)

            if items:
                print(f'[{Colors.CYAN}]第 {page_num} 页有效作品数量: {len(items)}')

                # 下载这一页的文件，传入起始序号，返回下一个序号
                next_video_num = Download.download_files(items, account.id, account.mark,
                                       self.settings, self.cleaner, self.cookie, next_video_num)
            else:
                print(f'[{Colors.YELLOW}]第 {page_num} 页没有符合条件作品')

        # 全部下载完成
        total_downloaded = next_video_num - 1
        if total_downloaded > 0:
            print(f'[{Colors.CYAN}]{"="*50}')
            print(f'[{Colors.GREEN}]全部下载完成! 共下载 {total_downloaded} 个视频')
            print(f'[{Colors.CYAN}]{"="*50}')
            return True
        elif account_extracted:
            print(f'[{Colors.YELLOW}]账号有效但没有符合条件作品')
            return True
