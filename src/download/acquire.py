from datetime import date
from urllib.parse import urlencode
from requests import exceptions, get
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)
from random import randint
from time import sleep
from rich import print

from ..encrypt_params import get_a_bogus
from ..config import Settings, Colors, Cookie, HEADERS, RETRY_ACCOUNT

POST_API = 'https://www.douyin.com/aweme/v1/web/aweme/post/'


class Acquire:

    def __init__(self, logger=None):
        self.cursor = 0
        self.finished = False
        self.logger = logger

    def _log(self, message: str, color: str = 'white'):
        '''统一日志输出，兼顾 GUI 日志框与控制台'''
        if self.logger:
            try:
                self.logger(message, color)
            except Exception:
                pass
        color_map = {
            'cyan': Colors.CYAN,
            'green': Colors.GREEN,
            'yellow': Colors.YELLOW,
            'red': Colors.RED,
            'magenta': Colors.MAGENTA,
            'white': Colors.WHITE,
            'blue': Colors.CYAN,
        }
        style = color_map.get(color, Colors.WHITE)
        print(f'[{style}]{message}')

    @staticmethod
    def _progress_object():
        return Progress(
            TextColumn('[progress.description]{task.description}', style=Colors.MAGENTA, justify='left'),
            '•',
            BarColumn(bar_width=20),
            '•',
            TimeElapsedColumn(),
            transient=True,
        )

    @staticmethod
    def _deal_url_params(params: dict, cookie: Cookie):
        '''注入 msToken、UIFID、verifyFp 并生成 a_bogus 签名'''
        if 'msToken' in cookie.cookies:
            params['msToken'] = cookie.cookies['msToken']

        # 注入 UIFID（ArgusSecurityPlugin 核心风控字段）
        if uifid := cookie.get_uifid():
            params['uifid'] = uifid

        # 注入 verifyFp 与 fp 参数
        verify_fp = cookie.get_verify_fp()
        if not verify_fp:
            from ..encrypt_params.verifyfp import VerifyFp
            verify_fp = VerifyFp.get_verify_fp()
        params['verifyFp'] = verify_fp
        params['fp'] = verify_fp

        # 使用 mini-racer 调用 JavaScript 计算 a_bogus
        params['a_bogus'] = get_a_bogus(params)

    @staticmethod
    def _wait():
        sleep(randint(15, 35) / 10)

    def _send_get(self, params: dict, settings: Settings, cookie: Cookie, sec_user_id: str = None):
        '''发送请求并返回 JSON 数据'''
        headers = dict(HEADERS)
        if sec_user_id:
            headers['Referer'] = f'https://www.douyin.com/user/{sec_user_id}'
        headers['Cookie'] = cookie._generate_str()

        try:
            response = get(
                POST_API,
                params=params,
                timeout=settings.timeout,
                headers=headers,
            )
            Acquire._wait()
        except (
            exceptions.ProxyError,
            exceptions.SSLError,
            exceptions.ChunkedEncodingError,
            exceptions.ConnectionError,
        ):
            self._log(f'网络异常，请求 {POST_API}?{urlencode(params)} 失败', 'yellow')
            return None
        except exceptions.ReadTimeout:
            self._log(f'网络异常，请求 {POST_API}?{urlencode(params)} 超时', 'yellow')
            return None

        # 检查是否触发 ArgusSecurityPlugin 安全校验拦截
        if response.status_code == 403 or 'ArgusSecurityPlugin' in response.text:
            if 'Uifid Not Found' in response.text:
                self._log('⚠️ [风控拦截] Blocked by ArgusSecurityPlugin Uifid Not Found', 'red')
                self._log('【排查说明】抖音近期开启了 Argus 安全风控，作品接口强制校验 UIFID 参数。', 'yellow')
                self._log('【解决步骤】', 'cyan')
                self._log('  1. 电脑浏览器访问 https://www.douyin.com 并确保处于登录状态。', 'cyan')
                self._log('  2. 按 F12 打开开发者工具，切换到 Network（网络）标签页。', 'cyan')
                self._log('  3. 刷新主页，找到任意 /aweme/ 接口请求。', 'cyan')
                self._log('  4. 复制 Request Headers 中的完整 Cookie 文本，粘贴回本工具保存。', 'cyan')
            else:
                self._log(f'请求被安全防护插件拦截 (HTTP {response.status_code}): {response.text[:200]}', 'yellow')
            return None

        try:
            return response.json()
        except exceptions.JSONDecodeError:
            if response.text:
                self._log(f'响应内容不是有效的 JSON 格式：{response.text[:200]}', 'yellow')
            else:
                self._log('响应内容为空，可能是接口失效或者 Cookie 失效，请尝试更新 Cookie', 'yellow')
            return None

    def _request_items_page(self, sec_user_id: str, settings: Settings, cookie: Cookie):
        '''获取单页作品数据，内置多轮重试机制，更新 self.cursor'''
        data = None
        for attempt in range(1, RETRY_ACCOUNT + 1):
            params = {
                'device_platform': 'webapp',
                'aid': '6383',
                'channel': 'channel_pc_web',
                'sec_user_id': sec_user_id,
                'max_cursor': self.cursor,
                'locate_query': 'false',
                'show_live_replay_strategy': '1',
                'need_time_list': '0' if self.cursor else '1',
                'time_list_query': '0',
                'whale_cut_token': '',
                'cut_version': '1',
                'count': '18',
                'publish_video_strategy_type': '2',
                'pc_client_type': '1',
                'version_code': '170400',
                'version_name': '17.4.0',
                'cookie_enabled': 'true',
                'platform': 'PC',
                'downlink': '10',
            }
            self._deal_url_params(params, cookie)
            data = self._send_get(params=params, settings=settings, cookie=cookie, sec_user_id=sec_user_id)
            if data:
                break

            if attempt < RETRY_ACCOUNT:
                wait_sec = attempt * 2 + randint(1, 2)
                self._log(f'第 {attempt} 次请求未能获取数据，{wait_sec} 秒后重试...', 'yellow')
                sleep(wait_sec)
                cookie.update()

        if not data:
            self._log('获取账号作品数据失败（多次重试均未成功）', 'yellow')
            return None

        try:
            if (items_page := data.get('aweme_list')) is None:
                self._log('该账号为私密账号，需要使用登录后的 Cookie，且登录账号需关注该私密账号', 'yellow')
                self.finished = True
                return None
            else:
                self.cursor = data.get('max_cursor', 0)
                self.finished = not data.get('has_more', False)
                return items_page or [None]
        except KeyError:
            self._log(f'账号作品数据响应内容异常: {data}', 'yellow')
            self.finished = True
            return None

    def _early_stop(self, earliest: date):
        '''如果获取数据的发布日期已经早于限制日期，就不需要再获取下一页的数据了'''
        if earliest > date.fromtimestamp(self.cursor / 1000):
            self.finished = True

    def request_items(self, sec_user_id: str, earliest: date, settings: Settings, cookie: Cookie):
        '''获取账号所有作品数据并返回（带整体进度条）'''
        items = []
        with self._progress_object() as progress:
            progress.add_task('正在获取账号主页数据', total=None)
            self.cursor = 0
            self.finished = False
            while not self.finished:
                if (items_page := self._request_items_page(sec_user_id, settings, cookie)):
                    if not items_page == [None]:
                        items.extend(items_page)
                    self._early_stop(earliest)
                else:
                    self.finished = True
        return items

    def request_items_iterative(self, sec_user_id: str, earliest: date, settings: Settings, cookie: Cookie):
        '''逐页获取账号作品数据（生成器），每次返回一页数据'''
        self.cursor = 0
        self.finished = False
        page_num = 0

        while not self.finished:
            page_num += 1
            self._log(f'正在获取第 {page_num} 页数据...', 'cyan')

            items_page = self._request_items_page(sec_user_id, settings, cookie)

            if items_page is None:
                self.finished = True
                break

            if items_page == [None]:
                self._early_stop(earliest)
                if not self.finished:
                    continue
                else:
                    break

            self._early_stop(earliest)
            if self.finished and not items_page:
                break

            yield items_page, page_num

            if self.finished:
                break
