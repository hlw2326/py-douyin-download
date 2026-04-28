import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from datetime import datetime, timedelta
from threading import Thread
from pathlib import Path
from json import dump

from .config import Account, Settings, Cookie, Colors, PROJECT_ROOT, ENCODE
from .download import Acquire, Download, Parse
from .tool import Cleaner, resolve_user_url


class DouyinDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("抖音视频下载器")
        self.root.geometry("700x650")
        self.root.resizable(True, True)

        self.cookie = Cookie()
        self.cleaner = Cleaner()
        self.is_downloading = False

        self._setup_ui()
        self._load_existing_cookie()

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # Cookie 区域
        ttk.Label(main_frame, text="Cookie:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        row += 1
        self.cookie_text = scrolledtext.ScrolledText(
            main_frame, height=4, wrap=tk.WORD, font=('Consolas', 9))
        self.cookie_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        main_frame.columnconfigure(1, weight=1)
        row += 1

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))
        ttk.Button(btn_frame, text="保存 Cookie", command=self._save_cookie).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="清空", command=self._clear_cookie).pack(side=tk.LEFT)
        row += 1

        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1

        # 账号配置区域
        ttk.Label(main_frame, text="账号主页链接:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        row += 1
        self.url_entry = ttk.Entry(main_frame, font=('Consolas', 9))
        self.url_entry.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        self.url_entry.insert(0, "https://www.douyin.com/user/")
        row += 1

        # 日期范围
        date_frame = ttk.Frame(main_frame)
        date_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(date_frame, text="最早日期:").pack(side=tk.LEFT)
        self.earliest_entry = ttk.Entry(date_frame, width=12)
        self.earliest_entry.pack(side=tk.LEFT, padx=(5, 20))
        self.earliest_entry.insert(0, "2016/09/20")
        ttk.Label(date_frame, text="最晚日期:").pack(side=tk.LEFT)
        self.latest_entry = ttk.Entry(date_frame, width=12)
        self.latest_entry.pack(side=tk.LEFT, padx=(5, 0))
        default_latest = (datetime.now() - timedelta(days=1)).strftime("%Y/%m/%d")
        self.latest_entry.insert(0, default_latest)
        row += 1

        # 下载选项
        options_frame = ttk.LabelFrame(main_frame, text="下载选项", padding="10")
        options_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        self.download_videos = tk.BooleanVar(value=True)
        self.download_images = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="下载视频", variable=self.download_videos).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(options_frame, text="下载图集", variable=self.download_images).pack(side=tk.LEFT, padx=(0, 20))

        # 时长上限
        self.limit_duration = tk.BooleanVar(value=True)
        self.duration_seconds = tk.StringVar(value="20")
        ttk.Checkbutton(options_frame, text="跳过超过", variable=self.limit_duration).pack(side=tk.LEFT)
        self.duration_entry = ttk.Spinbox(
            options_frame, from_=1, to=3600, width=5,
            textvariable=self.duration_seconds)
        self.duration_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Label(options_frame, text="秒的视频").pack(side=tk.LEFT)
        row += 1

        # 保存文件夹
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        ttk.Label(folder_frame, text="保存文件夹:").pack(side=tk.LEFT)
        self.folder_entry = ttk.Entry(folder_frame)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        self.folder_entry.insert(0, str(Path.home() / 'Desktop'))
        ttk.Button(folder_frame, text="浏览", command=self._browse_folder, width=8).pack(side=tk.LEFT)
        row += 1

        # 开始下载按钮
        self.start_btn = ttk.Button(main_frame, text="开始下载", command=self._start_download)
        self.start_btn.grid(row=row, column=0, columnspan=3, pady=(0, 15))
        row += 1

        # 日志区域
        ttk.Label(main_frame, text="下载日志:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        row += 1
        self.log_text = scrolledtext.ScrolledText(
            main_frame, height=12, wrap=tk.WORD, font=('Consolas', 9), state='disabled')
        self.log_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        main_frame.rowconfigure(row, weight=1)
        row += 1

        # 清空日志按钮
        ttk.Button(main_frame, text="清空日志", command=self._clear_log).grid(
            row=row, column=0, columnspan=3, pady=(5, 0))

    def _load_existing_cookie(self):
        cookie_path = self.cookie.cookie_path
        if cookie_path.exists():
            try:
                self.cookie.load_cookies()
                cookie_str = self.cookie._generate_str()
                self.cookie_text.delete(1.0, tk.END)
                self.cookie_text.insert(1.0, cookie_str)
                self._log("已加载已保存的 Cookie")
            except Exception as e:
                self._log(f"加载 Cookie 失败: {e}")

    def _save_cookie(self):
        cookie_str = self.cookie_text.get(1.0, tk.END).strip()
        if not cookie_str:
            messagebox.showwarning("警告", "请输入 Cookie")
            return
        try:
            self.cookie.cookies = self.cookie._generate_dict(cookie_str)
            self.cookie._check()
            self.cookie._save_json()
            messagebox.showinfo("成功", "Cookie 保存成功！")
        except Exception as e:
            messagebox.showerror("错误", f"保存 Cookie 失败: {e}")

    def _clear_cookie(self):
        self.cookie_text.delete(1.0, tk.END)

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=str(Path.home() / 'Desktop'))
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)

    def _log(self, message: str, color: str = 'black'):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n', (color,))
        self.log_text.tag_config(color, foreground=color)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def _clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def _validate_inputs(self):
        raw_input = self.url_entry.get().strip()
        if not raw_input or raw_input == "https://www.douyin.com/user/":
            messagebox.showwarning("警告", "请输入账号主页链接")
            return None

        # 自动识别分享文本/短链，解析为标准用户主页 URL
        url = resolve_user_url(raw_input)
        if not url:
            messagebox.showerror(
                "错误",
                "无法从输入中识别抖音用户链接。\n"
                "支持以下格式：\n"
                "  · https://www.douyin.com/user/MS4w...\n"
                "  · https://v.douyin.com/xxxx/\n"
                "  · 包含上述链接的分享文本"
            )
            return None

        if url != raw_input:
            self._log(f"已解析链接: {url}", 'green')
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)

        # 如果内存中没有 Cookie，尝试加载
        if not self.cookie.cookies:
            # 先尝试从已保存的文件加载
            cookie_path = self.cookie.cookie_path
            if cookie_path.exists():
                try:
                    self.cookie.load_cookies()
                    self._log("已自动加载已保存的 Cookie", 'green')
                except Exception:
                    pass

            # 如果还是没有，尝试从文本框生成
            if not self.cookie.cookies:
                cookie_str = self.cookie_text.get(1.0, tk.END).strip()
                if cookie_str:
                    try:
                        self.cookie.cookies = self.cookie._generate_dict(cookie_str)
                        self._log("已从文本框加载 Cookie", 'green')
                    except:
                        pass

            # 最后检查
            if not self.cookie.cookies:
                messagebox.showwarning("警告", "请先设置 Cookie")
                return None

        earliest = self.earliest_entry.get().strip()
        latest = self.latest_entry.get().strip()

        account = Account(
            mark="GUI账号",
            url=url,
            earliest=earliest if earliest else None,
            latest=latest if latest else None
        )

        save_folder = self.folder_entry.get().strip() or str(Path.home() / 'Desktop')

        max_duration = 0
        if self.limit_duration.get():
            try:
                max_duration = int(self.duration_seconds.get().strip() or 0)
                if max_duration < 0:
                    max_duration = 0
            except ValueError:
                messagebox.showwarning("警告", "时长上限必须是整数秒")
                return None

        settings = Settings(
            accounts=(account,),
            save_folder=Path(save_folder),
            download_videos=self.download_videos.get(),
            download_images=self.download_images.get(),
            max_video_duration=max_duration,
        )

        return account, settings

    def _start_download(self):
        if self.is_downloading:
            messagebox.showinfo("提示", "正在下载中，请等待完成")
            return

        result = self._validate_inputs()
        if not result:
            return

        account, settings = result

        self.is_downloading = True
        self.start_btn.config(state='disabled')
        self._log("=" * 50, 'cyan')
        self._log(f"开始处理账号: {account.url}", 'cyan')
        self._log(f"最早日期: {account.earliest or '空'}", 'cyan')
        self._log(f"最晚日期: {account.latest or '空'}", 'cyan')
        self._log(f"下载视频: {'是' if settings.download_videos else '否'}", 'cyan')
        self._log(f"下载图集: {'是' if settings.download_images else '否'}", 'cyan')
        if settings.max_video_duration > 0:
            self._log(f"跳过超过 {settings.max_video_duration} 秒的视频", 'cyan')
        self._log("=" * 50, 'cyan')

        Thread(target=self._download_thread, args=(account, settings), daemon=True).start()

    def _download_thread(self, account: Account, settings: Settings):
        try:
            self.cookie.update()
            self._log("\n使用逐页下载模式", 'blue')

            acquire = Acquire()
            account_extracted = False
            total_downloaded = 0
            next_video_num = 1  # 下一个视频序号

            for items_page, page_num in acquire.request_items_iterative(
                account.sec_user_id, account.earliest_date, settings, self.cookie
            ):
                if not items_page:
                    continue

                # 第一次提取账号信息
                if not account_extracted:
                    self._log(f"\n开始提取账号信息", 'blue')
                    Parse.extract_account(account, items_page[0], self.cleaner)
                    self._log(f"账号昵称: {account.name} | 账号 ID: {account.id}", 'green')
                    account_extracted = True

                # 提取这一页的作品数据
                items = Parse.extract_items(
                    items_page, account.earliest_date, account.latest_date,
                    settings, self.cleaner
                )

                if items:
                    self._log(f"第 {page_num} 页有效作品: {len(items)} 个", 'green')

                    # 下载这一页的文件，传入起始序号，返回下一个序号
                    next_video_num = Download.download_files(
                        items, account.id, account.mark,
                        settings, self.cleaner, self.cookie, next_video_num
                    )
                    total_downloaded = next_video_num - 1  # 总下载数
                else:
                    self._log(f"第 {page_num} 页没有符合条件作品", 'yellow')

            # 全部下载完成
            if total_downloaded > 0:
                self._log(f"\n" + "=" * 50, 'cyan')
                self._log(f"全部下载完成! 共下载 {total_downloaded} 个视频", 'green')
                self._log("=" * 50, 'cyan')
            elif account_extracted:
                self._log("\n账号有效但没有符合条件作品", 'yellow')

        except Exception as e:
            self._log(f"\n下载过程出错: {e}", 'red')
        finally:
            self.is_downloading = False
            self.root.after(0, lambda: self.start_btn.config(state='normal'))


def run_gui():
    root = tk.Tk()
    app = DouyinDownloaderGUI(root)
    root.mainloop()


if __name__ == '__main__':
    run_gui()
