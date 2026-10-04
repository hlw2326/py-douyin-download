from json import load, dump
from pathlib import Path
from os import getenv
from rich import print

from .settings import Colors, ENCODE, PROJECT_ROOT


class Cookie:
    def __init__(self):
        self.cookies = {}
        # 优先读取项目根目录下的 cookies.json，否则读取用户家目录
        self.local_cookie_path = PROJECT_ROOT / 'cookies.json'
        username = getenv('USERNAME') or 'Administrator'
        self.user_cookie_path = Path(f'C:/Users/{username}/cookies.json')
        if self.local_cookie_path.exists():
            self.cookie_path = self.local_cookie_path
        else:
            self.cookie_path = self.user_cookie_path

    def load_cookies(self):
        # 优先从存在的文件读取
        target_path = self.cookie_path
        if not target_path.exists():
            if self.local_cookie_path.exists():
                target_path = self.local_cookie_path
            elif self.user_cookie_path.exists():
                target_path = self.user_cookie_path
        
        with open(target_path, 'r', encoding=ENCODE) as f:
            self.cookies = load(f)
        self.cookie_path = target_path

    @staticmethod
    def _generate_dict(cookie: str) -> dict:
        '''解析浏览器 Cookie 字符串，保留所有有效键值对（避免遗漏 UIFID 等新风控参数）'''
        cookies = {}
        for item in cookie.split(';'):
            item = item.strip()
            if not item or '=' not in item:
                continue
            key, value = item.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key:
                cookies[key] = value
        return cookies

    def get_uifid(self) -> str | None:
        '''获取 UIFID 风控参数'''
        for k in ('UIFID', 'uifid', 'UIFID_TEMP'):
            if val := self.cookies.get(k):
                return val
        for k, v in self.cookies.items():
            if k.lower() == 'uifid' and v:
                return v
        return None

    def has_uifid(self) -> bool:
        return self.get_uifid() is not None

    def get_verify_fp(self) -> str | None:
        '''获取 verifyFp / fp 风控参数'''
        return (
            self.cookies.get('s_v_web_id')
            or self.cookies.get('verifyFp')
            or self.cookies.get('fp')
        )

    def _check(self) -> None:
        if not self.cookies.get('sessionid_ss') and not self.cookies.get('sessionid'):
            print(f'[{Colors.YELLOW}]⚠️ 当前 Cookie 未检测到登录状态 (缺少 sessionid/sessionid_ss)')
        else:
            print(f'[{Colors.GREEN}]✓ 当前 Cookie 已处于登录状态')

        if not self.has_uifid():
            print(f'[{Colors.YELLOW}]⚠️ 警告：Cookie 中未检测到 UIFID 字段！')
            print(f'[{Colors.YELLOW}]抖音已启用 ArgusSecurityPlugin 校验，缺少 UIFID 会导致接口返回 403 (Blocked by ArgusSecurityPlugin Uifid Not Found)。')
            print(f'[{Colors.YELLOW}]建议：在浏览器打开 www.douyin.com 并登录，按 F12 打开网络 (Network) 面板刷新页面，在任意 /aweme/ 请求的 Headers 中复制完整的 Cookie。')
        else:
            print(f'[{Colors.GREEN}]✓ 已包含 UIFID 风控校验参数')

    def _save_json(self) -> None:
        # 保存到当前路径，并同步保存到项目目录（如果存在）
        paths = {self.cookie_path, self.local_cookie_path, self.user_cookie_path}
        saved = False
        for p in paths:
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, 'w', encoding=ENCODE) as f:
                    dump(self.cookies, f, ensure_ascii=False, indent=4)
                saved = True
            except Exception:
                pass
        if saved:
            print(f'[{Colors.GREEN}]写入 Cookie 成功！')
        else:
            print(f'[{Colors.RED}]保存 Cookie 失败，请检查文件写入权限！')

    def input_save(self) -> None:
        while not (cookie := input('请粘贴 Cookie 内容: ')):
            continue
        self.cookies = self._generate_dict(cookie)
        self._check()
        self._save_json()

    def update(self) -> None:
        '''动态刷新 msToken 和 ttwid'''
        try:
            from ..encrypt_params.msToken import MsToken
            from ..encrypt_params.ttWid import TtWid
            parameters = (MsToken.get_real_ms_token(), TtWid.get_tt_wid())
            for i in parameters:
                if isinstance(i, dict):
                    self.cookies |= i
        except Exception as e:
            print(f'[{Colors.YELLOW}]刷新动态参数失败 (非致命): {e}')

    def _generate_str(self) -> str:
        result = [f'{k}={v}' for k, v in self.cookies.items()]
        return '; '.join(result)
