from json import load, dump
from json.decoder import JSONDecodeError
from re import match
from datetime import date, timedelta, datetime
from rich import print
from dataclasses import dataclass
from pathlib import Path
from os import name as os_name
import sys

def _resolve_project_root() -> Path:
    '''用户可写资源目录：开发模式为源码根目录，PyInstaller 冻结后为 exe 所在目录。'''
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def _resolve_bundle_root() -> Path:
    '''只读打包资源目录：开发模式为源码根目录，PyInstaller 冻结后为 _MEIPASS。'''
    if meipass := getattr(sys, '_MEIPASS', None):
        return Path(meipass)
    return Path(__file__).parent.parent.parent


PROJECT_ROOT = _resolve_project_root()
BUNDLE_ROOT = _resolve_bundle_root()
ENCODE = 'UTF-8-SIG' if os_name == 'nt' else 'UTF-8'
REFERER = 'https://www.douyin.com/'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
HEADERS = {
    'Referer': REFERER,
    'User-Agent': USER_AGENT,
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
}
PHONE_USER_AGENT = 'com.ss.android.ugc.trill/494+Mozilla/5.0+(Linux;+Android+12;+2112123G+Build/SKQ1.211006.001;+wv)+AppleWebKit/537.36+(KHTML,+like+Gecko)+Version/4.0+Chrome/107.0.5304.105+Mobile+Safari/537.36'
RETRY_ACCOUNT: int = 3
RETRY_FILE: int = 2

class Colors:
    WHITE = '#aaaaaa'
    CYAN = 'bright_cyan'
    RED = 'bright_red'
    YELLOW = 'bright_yellow'
    GREEN = 'bright_green'
    MAGENTA = 'bright_magenta'


@dataclass
class Account:
    mark: str
    url: str
    earliest: str
    latest: str
    sec_user_id: str = None
    earliest_date: date = date(2016, 9, 20)
    latest_date: date = date.today() - timedelta(days=1)
    id: str = None
    name: str = None

    def __post_init__(self):
        self.sec_user_id = self._extract_sec_user_id()
        if self.earliest:
            self.earliest_date = self._generate_date_earliest()
        if self.latest:
            self.latest_date = self._generate_date_latest()

    def _extract_sec_user_id(self) -> str | None:
        match_url = match(r'https://www\.douyin\.com/user/([A-Za-z0-9_-]+)(\?.*)?', self.url)
        if match_url:
            return match_url.group(1)
        print(f'[{Colors.RED}]参数 accounts 中账号 {self.mark} 的 url {self.url} 错误，提取 sec_user_id 失败！')
        sys.exit()

    def _generate_date_earliest(self) -> date:
        try:
            return datetime.strptime(self.earliest, '%Y/%m/%d').date()
        except ValueError:
            print(f'[{Colors.YELLOW}]作品最早发布日期 {self.earliest} 无效')
            return self.earliest_date

    def _generate_date_latest(self) -> date:
        try:
            return datetime.strptime(self.latest, '%Y/%m/%d').date()
        except ValueError:
            print(f'[{Colors.YELLOW}]作品最晚发布日期无效 {self.latest}')
            return self.latest_date


@dataclass(frozen=True)
class Settings:
    accounts: tuple[Account]
    save_folder: Path = PROJECT_ROOT
    download_videos: bool = True
    download_images: bool = False
    name_format: tuple[str] = ('create_time', 'id', 'type', 'desc')
    split: str = '-'
    date_format: str = '%Y-%m-%d'
    proxy: str = None
    file_description_max_length: int = 64
    chunk_size: int = 1024 * 1024
    timeout: int = 60 * 5
    concurrency: int = 5
    max_video_duration: int = 36  # 视频时长上限（秒），0 表示不限制；超过则跳过。默认 36 秒


def get_settings_filepath() -> Path:
    '''获取当前使用的配置文件路径'''
    if (PROJECT_ROOT / 'settings_mine.json').exists():
        return PROJECT_ROOT / 'settings_mine.json'
    return PROJECT_ROOT / 'settings_default.json'


def load_settings() -> Settings:
    filepath = get_settings_filepath()
    try:
        with open(filepath, encoding=ENCODE) as f:
            data = load(f)
    except JSONDecodeError:
        print(f'[{Colors.RED}]配置文件 {filepath.name} 格式错误，请检查 JSON 格式！')
        sys.exit()

    accounts = tuple(Account(**a) for a in data.get("accounts", []))
    data_without_accounts = {k: v for k, v in data.items() if k != "accounts"}
    if 'save_folder' in data_without_accounts:
        data_without_accounts['save_folder'] = Path(data_without_accounts.get('save_folder'))
    if 'name_format' in data_without_accounts:
        data_without_accounts['name_format'] = tuple(data_without_accounts.get('name_format'))
    if 'max_video_duration' in data_without_accounts:
        try:
            data_without_accounts['max_video_duration'] = int(data_without_accounts['max_video_duration'])
        except (ValueError, TypeError):
            data_without_accounts['max_video_duration'] = 36
    else:
        data_without_accounts['max_video_duration'] = 36
    return Settings(accounts=accounts, **data_without_accounts)


def save_max_video_duration(seconds: int) -> bool:
    '''将跳过视频时长限制写入配置文件 (优先写入 settings_mine.json，否则写入 settings_default.json)'''
    filepath = get_settings_filepath()
    try:
        data = {}
        if filepath.exists():
            with open(filepath, 'r', encoding=ENCODE) as f:
                data = load(f)
        data['max_video_duration'] = int(seconds)
        with open(filepath, 'w', encoding=ENCODE) as f:
            dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f'[{Colors.YELLOW}]写入配置文件失败: {e}')
        return False


if __name__ == '__main__':
    print(load_settings())
    input()

