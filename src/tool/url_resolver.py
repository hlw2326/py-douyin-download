from re import search
from requests import head, exceptions
from rich import print

from ..config import Colors, HEADERS

USER_URL_PATTERN = r'https?://www\.douyin\.com/user/[A-Za-z0-9_-]+'
SHORT_URL_PATTERN = r'https?://v\.douyin\.com/[A-Za-z0-9_-]+/?'
SEC_UID_PATH_PATTERN = r'/(?:share/)?user/([A-Za-z0-9_-]+)'
SEC_UID_QUERY_PATTERN = r'[?&]sec_uid=([A-Za-z0-9_-]+)'

CANONICAL_USER_URL = 'https://www.douyin.com/user/{sec_uid}'


def _follow_short_link(short_url: str, timeout: int = 10) -> str | None:
    '''跟随抖音短链重定向，返回最终 URL。'''
    try:
        response = head(short_url, allow_redirects=True, timeout=timeout, headers=HEADERS)
        return response.url
    except (exceptions.ConnectionError, exceptions.Timeout, exceptions.RequestException) as e:
        print(f'[{Colors.YELLOW}]解析抖音短链失败: {short_url} ({e})')
        return None


def _extract_sec_uid_from_url(url: str) -> str | None:
    '''从抖音相关 URL（含 douyin.com/user/、iesdouyin.com/share/user/、?sec_uid=）中提取 sec_user_id。'''
    if m := search(SEC_UID_PATH_PATTERN, url):
        return m.group(1)
    if m := search(SEC_UID_QUERY_PATTERN, url):
        return m.group(1)
    return None


def resolve_user_url(text: str) -> str | None:
    '''
    从文本/短链/直接 URL 中解析出标准的抖音用户主页 URL。

    支持以下输入形式：
      1. 直接的用户主页 URL: https://www.douyin.com/user/MS4w...
      2. 抖音短链: https://v.douyin.com/xxxx/
      3. 包含上述链接的分享文本（如 "3- 长按复制此条消息... https://v.douyin.com/xxxx/ ..."）

    返回标准用户主页 URL: https://www.douyin.com/user/<sec_user_id>
    无法解析时返回 None。
    '''
    if not text:
        return None
    text = text.strip()

    if direct := search(USER_URL_PATTERN, text):
        return direct.group(0)

    if short := search(SHORT_URL_PATTERN, text):
        if final_url := _follow_short_link(short.group(0)):
            if sec_uid := _extract_sec_uid_from_url(final_url):
                return CANONICAL_USER_URL.format(sec_uid=sec_uid)
            print(f'[{Colors.YELLOW}]短链重定向后未找到 sec_user_id: {final_url}')

    return None


def extract_sec_user_id(text: str) -> str | None:
    '''从输入文本中解析出 sec_user_id。'''
    url = resolve_user_url(text)
    if not url:
        return None
    return _extract_sec_uid_from_url(url)
