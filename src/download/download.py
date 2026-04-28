from rich.progress import (
    SpinnerColumn,
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)
from pathlib import Path
from rich import print
from yarl import URL
from asyncio import Semaphore, gather, run, create_task, TimeoutError
from aiohttp import ClientSession, ClientResponse, ClientTimeout
import re

from ..config import Settings, Cookie, Colors, HEADERS
from ..tool import Cleaner, retry_async


class Download:
    @staticmethod
    def _create_save_folder(id: str, settings: Settings):
        '''新建存储文件夹，返回文件夹路径（只用用户ID命名）'''
        folder = settings.save_folder / f'{id}'
        folder.mkdir(exist_ok=True)
        return folder

    @staticmethod
    def _get_next_video_num(save_folder: Path) -> int:
        '''扫描文件夹中已有的视频文件，返回下一个可用序号'''
        max_num = 0
        if save_folder.exists():
            for file in save_folder.iterdir():
                if file.is_file() and file.suffix in ['.mp4', '.mov', '.avi', '.mkv']:
                    # 匹配文件名中的数字，如 "1.mp4" -> 1
                    match = re.match(r'^(\d+)\.', file.name)
                    if match:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num
        return max_num + 1

    @staticmethod
    def _generate_task_video(id: str, desc: str, video_num: int, format: str, url: str, width: int, height: int, save_folder: Path):
        '''生成视频下载任务信息（文件名使用序号）'''
        show = f'视频 {video_num} - {desc[:15]}'
        if not format:
            print(f'[{Colors.RED}]{show} 格式为空，跳过')
            return None
        if not url:
            print(f'[{Colors.RED}]{show} URL为空，跳过')
            return None

        path = save_folder / f'{video_num}.{format.split(".")[-1]}'
        if path.exists():
            print(f'[{Colors.CYAN}]{show} 文件已存在，跳过下载')
        else:
            print(f'[{Colors.CYAN}]{show} 添加到下载队列')
            return (url, path, show, id, width, height)

    @staticmethod
    def _generate_task(items: list[dict], save_folder: Path, settings: Settings, cleaner: Cleaner, start_num: int = 1):
        '''生成下载任务信息列表并返回（返回任务列表和下一个序号）'''
        tasks = []
        video_num = start_num  # 从指定序号开始

        for item in items:
            id = item['id']
            desc = item['desc']
            type = item.get('type')

            if type == '视频':
                url = item['downloads']
                width = item['width']
                height = item['height']
                format = item.get('format')
                # 检查文件是否存在，存在则跳过，不存在则添加到下载队列
                if (task := Download._generate_task_video(
                    id, desc, video_num, format, url, width, height, save_folder)) is not None:
                    tasks.append(task)
                video_num += 1  # 每个视频都增加序号，不管是否下载

        return tasks, video_num

    @staticmethod
    def _progress_object():
        return Progress(
            TextColumn('[progress.description]{task.description}', style=Colors.MAGENTA, justify='left'),
            SpinnerColumn(),
            BarColumn(bar_width=20),
            '[progress.percentage]{task.percentage:>3.1f}%',
            '•',
            DownloadColumn(binary_units=True),
            '•',
            TimeRemainingColumn(),
            transient=True,
        )

    @staticmethod
    async def _save_file(path: Path, show: str, id: str, width: int, height: int,
                         response: ClientResponse, content_length: int, progress: Progress, settings: Settings):
        task_id = progress.add_task(show, total=content_length or None)
        with open(path, 'wb') as f:
            async for chunk in response.content.iter_chunked(settings.chunk_size):
                f.write(chunk)
                progress.update(task_id, advance=len(chunk))
        progress.remove_task(task_id)
        if max(width, height) < 1920:
            color = Colors.YELLOW
        else:
            color = Colors.GREEN
        print(f'[{Colors.GREEN}]{show} [{color}]清晰度：{width}×{height}[{Colors.GREEN}] 下载完成 ({path.stat().st_size / (1024 * 1024):.2f} MB)')

    @staticmethod
    @retry_async
    async def _request_file(url: str, path: Path, show: str, id: str, width: int, height: int,
                            progress: Progress, sem: Semaphore, settings: Settings, cookie: Cookie):
        '''下载 url 对应文件'''
        async with sem:
            try:
                async with ClientSession(
                    headers=HEADERS | {'Cookie': cookie._generate_str()},
                    timeout=ClientTimeout(settings.timeout),
                    proxy=settings.proxy,
                ) as session:
                    async with session.get(URL(url, encoded=True)) as response:
                        if not (content_length := int(response.headers.get('content-length', 0))):
                            print(f'[{Colors.YELLOW}]{show} {url} 响应内容为空')
                        elif response.status != 200 and response.status != 206:
                            print(f'[{Colors.YELLOW}]{show} {url} 响应状态码异常 {response.status}')
                        else:
                            await Download._save_file(path, show, id, width, height,
                                                      response, content_length, progress, settings)
                            return True
            except TimeoutError:
                print(f'[{Colors.YELLOW}]{show} {url} 响应超时')

    @staticmethod
    async def _download_file(task_info: tuple, progress: Progress, sem: Semaphore,
                             settings: Settings, cookie: Cookie):
        await Download._request_file(*task_info, progress, sem, settings, cookie)

    @staticmethod
    async def _download_files(tasks_info: list, progress: Progress, settings: Settings, cookie: Cookie):
        '''串行下载每个文件，每个文件单独显示进度'''
        sem = Semaphore(1)  # 串行下载，同时只下载一个文件
        for task_info in tasks_info:
            await Download._download_file(task_info, progress, sem, settings, cookie)

    @staticmethod
    def download_files(items: list[dict], account_id: str, account_mark: str,
                       settings: Settings, cleaner: Cleaner, cookie: Cookie, start_num: int = 1):
        '''下载作品文件（串行模式，每个视频单独显示进度，start_num指定起始序号）'''
        print(f'[{Colors.CYAN}]\n开始下载作品文件\n')
        save_folder = Download._create_save_folder(account_id, settings)
        print(f'[{Colors.CYAN}]保存目录: {save_folder}')

        # 生成下载任务（会自动检查每个文件是否存在）
        tasks_info, next_num = Download._generate_task(items, save_folder, settings, cleaner, start_num)
        if not tasks_info:
            print(f'[{Colors.YELLOW}]本页没有需要下载的文件（可能都已存在）')
            return next_num  # 返回下一个序号
        print(f'[{Colors.CYAN}]共 {len(tasks_info)} 个文件待下载（序号 {start_num}-{next_num-1}）\n')
        with Download._progress_object() as progress:
            run(Download._download_files(tasks_info, progress, settings, cookie))
        return next_num  # 返回下一个可用序号
