import ctypes
import subprocess

from ctypes import wintypes
from pathlib import Path
from typing import Self

from otsutil import Timer, pathLike
from otsuvalidator import CPath
from otsuwinAPI import Kernel32, User32
from otsuwinAPI.constants import nCmdShow


class WindowHandlerRetrievalException(Exception):
    pass


class Window:
    handlers: dict[int, Self] = {}

    def __init__(
        self,
        title: str,
        timeout_seconds: float = 10,
        *,
        hWndParent: int | None = None,
        hWndChildAfter: int | None = None,
        lpszClass: str | None = None,
    ) -> None:
        """ウィンドウを操作するためのインスタンスを生成する。

        Args:
            title (str): ウィンドウのタイトル。
            timeout_seconds (float, optional): 失敗とみなすまでの秒数。 Defaults to 10.
            hWndParent (int | None, optional): 子ウィンドウを検索する親ウィンドウハンドル。
            hWndChildAfter (int | None, optional): 子ウィンドウハンドル。
            lpszClass (str | None, optional): クラス名またはクラスアトム。

        Raises:
            WindowHandlerRetrievalException: ウィンドウのハンドラ取得に失敗した場合。
        """
        # title: {pid: (tid, hWnd)}
        enum_windows: dict[str, dict[int, tuple[int, int]]] = {}
        msg = f'名前が"{title}"のウィンドウを発見できませんでした。({{}})'

        def callback(hWnd: int, lParam: int) -> bool:
            if User32.IsWindowVisible(hWnd):
                tid, pid = User32.GetWindowThreadProcessIdEz(hWnd)
                title = User32.GetWindowTextWEz(hWnd)
                if (d := enum_windows.get(title, None)) is None:
                    d = enum_windows[title] = {}
                d[pid] = (tid, hWnd)
            return True

        handlers = Window.handlers
        pointer = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        proc = pointer(callback)
        for _ in Timer(seconds=timeout_seconds).wiggle_begin():
            hWnd = User32.FindWindowExW(
                hWndParent=hWndParent,
                hWndChildAfter=hWndChildAfter,
                lpszClass=lpszClass,
                lpszWindow=title,
            )
            if hWnd == 0:
                continue
            tid = pid = None
            if hWnd in handlers:
                User32.EnumWindows(proc, 0)
                if (data := enum_windows.get(title, None)) is None:
                    msg = msg.format("data not found")
                    raise WindowHandlerRetrievalException(msg)
                for pid, (tid, hWnd) in data.items():
                    if hWnd in handlers:
                        continue
                    break
                else:
                    continue
            if hWnd in handlers:
                msg = msg.format("hWnd is duplicate")
                raise WindowHandlerRetrievalException(msg)
            if pid is None or tid is None:
                tid, pid = User32.GetWindowThreadProcessIdEz(hWnd)
            self.__handler = hWnd
            self.__process_id = pid
            self.__thread_id = tid
            self.__max_min = False
            self.__first_title = title
            handlers[hWnd] = self
            return
        msg = msg.format("timeout")
        raise WindowHandlerRetrievalException(msg)

    def __bool__(self) -> bool:
        if (hWnd := self.handler) not in Window.handlers:
            return False
        return User32.IsWindowEnabled(hWnd)

    def __str__(self) -> str:
        process_id = self.process_id
        thread_id = self.thread_id
        hWnd = self.handler
        return f"{self.__class__.__name__}({self.title}): {process_id=}, {thread_id=}, {hWnd=}"

    @property
    def first_title(self) -> str:
        """インスタンス生成時のタイトル。"""
        return self.__first_title

    @property
    def handler(self) -> int:
        """ウィンドウハンドラ。"""
        return self.__handler

    @property
    def process_id(self) -> int:
        """プロセスID。"""
        return self.__process_id

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """ウィンドウの左上と右下の座標。

        Returns:
            tuple[int, int, int, int]: (lx, ly, rx, ry)のタプル。
        """
        return User32.GetWindowRectEz(self.handler)

    @property
    def size(self) -> tuple[int, int]:
        """ウィンドウの幅と高さ。"""
        left, top, right, bottom = self.rect
        width = abs(left - right)
        height = abs(top - bottom)
        return (width, height)

    @property
    def title(self) -> str:
        """ウィンドウのタイトル。"""
        return User32.GetWindowTextWEz(self.handler)

    @property
    def thread_id(self) -> int:
        """スレッドID。"""
        return self.__thread_id

    @classmethod
    def refresh(cls) -> None:
        """現在取得しているウィンドウハンドルから既に無効になっているものを除外する。"""
        values = [x for x in cls.handlers.values()]
        for wd in values:
            if not wd:
                wd.close()

    def close(self) -> int:
        """ウィンドウを閉じる。

        Returns:
            int: 応答。
        """
        res = User32.SendMessageW(self.handler, 0x0010, 0, 0)
        Window.handlers.pop(self.handler, None)
        return res

    def join(self, span: float = 0.05) -> None:
        """ウィンドウの終了を待つ。

        Args:
            span (float, optional): 終了確認を行う間隔。 Defaults to 0.05.
        """
        t = Timer(seconds=span)
        while self:
            t.begin()
        self.close()

    def maximized(self) -> bool:
        """ウィンドウを最大化する。

        Returns:
            bool: 以前の表示状態。
        """
        self.__max_min = True
        return User32.ShowWindow(self.handler, nCmdShow.SW_MAXIMIZE)

    def minimize(self, keep_active: bool = False) -> bool:
        """ウィンドウを最小化する。

        Args:
            keep_active (bool, optional): ウィンドウのアクティブを継続するか。 Defaults to False.

        Returns:
            bool: 以前の表示状態。
        """
        self.__max_min = True
        value = nCmdShow.SW_SHOWMINIMIZED if keep_active else nCmdShow.SW_MINIMIZE
        return User32.ShowWindow(self.handler, value)

    def move_top(self) -> bool:
        """ウィンドウをZオーダーの先頭に移動する。

        Returns:
            bool: 成否。
        """
        return User32.BringWindowToTop(self.handler)

    def move_window(self, x: int, y: int, n_width: int, n_height: int) -> bool:
        """ウィンドウの左上座標と幅、高さを指定してウィンドウを再描画する。

        Args:
            x (int): 左上X座標。
            y (int): 左上Y座標。
            n_width (int): 幅。
            n_height (int): 高さ

        Returns:
            bool: 成否。
        """
        if not self:
            self.close()
            return False
        return User32.MoveWindow(self.handler, x, y, n_width, n_height, True)

    def normal(self) -> bool:
        """ウィンドウをアクティブ化して表示する。

        最大化、または最小化されたウィンドウに対して使用した場合、元のサイズと位置を復元する。

        Returns:
            bool: 以前の表示状態。
        """
        value = nCmdShow.SW_RESTORE if self.__max_min else nCmdShow.SW_NORMAL
        return User32.ShowWindow(self.handler, value)

    def set_foreground(self, allow_attach: bool = False) -> bool:
        """フォアグラウンドに移動させる。

        allow_attachを有効にすることで成功率が上がるが、予期せぬ不具合を招く可能性がある点に注意。

        Args:
            allow_attach (bool, optional): スレッドのアタッチを許可するか。

        Returns:
            bool: 成否。
        """
        if not allow_attach:
            return User32.SetForegroundWindow(self.handler)
        cur_thread_id = Kernel32.GetCurrentThreadId()
        my_thread_id = User32.GetWindowThreadProcessId(self.handler)
        User32.AttachThreadInput(cur_thread_id, my_thread_id, True)
        res = User32.SetForegroundWindow(self.handler)
        User32.AttachThreadInput(cur_thread_id, my_thread_id, False)
        return res

    def set_position(self, x: int, y: int) -> bool:
        """ウィンドウを指定の座標に移動させる。

        Args:
            x (int): 左上X座標。
            y (int): 左上Y座標。

        Returns:
            bool: 成否。
        """
        if not self:
            self.close()
            return False
        w, h = self.size
        return User32.MoveWindow(self.handler, x, y, w, h, True)

    def set_size(self, width: int, height: int) -> bool:
        """ウィンドウを指定のサイズに変更する。

        Args:
            width (int): 幅。
            height (int): 高さ。

        Returns:
            bool: 成否。
        """
        if not self:
            self.close()
            return False
        x, y, *_ = self.rect
        return User32.MoveWindow(self.handler, x, y, width, height, True)


class RecycleBinFolder(Window):
    """ゴミ箱専用のExplorerに近いクラス。

    Explorerとの違いはごみ箱しか開かない点とパスの移動を許可しない点。
    """

    def __init__(self, timeout_seconds: float = 10,suffix:str|None='エクスプローラー') -> None:
        """ごみ箱の操作を行うインスタンスを生成する。

        suffixを有効にした場合、"{title} - {suffix}"というウィンドウ名を検索する。

        Args:
            timeout_seconds (float, optional): 失敗とみなすまでの秒数。 Defaults to 10.
            suffix (str | None, optional): 末尾に付けるアプリケーション名。 Defaults to 'エクスプローラー'.
        """
        title = "ごみ箱"
        if suffix is not None and suffix.strip()!='':
            title=f'{title} - {suffix}'
        try:
            super().__init__(title, 1)
            return
        except:
            subprocess.Popen(["explorer", "shell:RecycleBinFolder"]).wait()
            super().__init__(title, timeout_seconds)

    def __bool__(self) -> bool:
        if not super().__bool__():
            return False
        return User32.GetWindowTextWEz(self.handler) == self.first_title

    def __str__(self) -> str:
        process_id = self.process_id
        thread_id = self.thread_id
        hWnd = self.handler
        return f"ごみ箱: {process_id=}, {thread_id=}, {hWnd=}"


class Explorer(Window):
    def __init__(
        self,
        path: pathLike,
        allow_chdir: bool = False,
        timeout_seconds: float = 10,
        *,
        title: str | None = None,
        suffix:str|None="エクスプローラー"
    ) -> None:
        """pathの操作を行うインスタンスを生成する。

        suffixを有効にした場合、"{title} - {suffix}"というウィンドウ名を検索する。

        Args:
            path (pathLike): 操作したいエクスプローラのパス。存在するフォルダのみ受付。
            allow_chdir (bool, optional): エクスプローラのパス変更を許可するかどうか。 不許可の場合は移動した時点でWindow.closeが呼び出される。 Defaults to False.
            timeout_seconds (float, optional): インスタンス生成を失敗とみなすまでの秒数。 Defaults to 10.
            title (str | None, optional): ウィンドウタイトル。デスクトップなど、開くパスとタイトルが一致しない場合に指定する。
            suffix (str | None, optional): 末尾に付けるアプリケーション名。 Defaults to 'エクスプローラー'.
        """
        path = CPath(exist_only=True, path_type=Path.is_dir).validate(path)
        title = title if title else path.name
        if suffix is not None and suffix.strip()!='':
            title=f'{title} - {suffix}'
        try:
            super().__init__(title, 1)
        except:
            subprocess.Popen(["explorer", path]).wait()
            super().__init__(title, timeout_seconds)
        self.__allow_chdir = allow_chdir

    def __bool__(self) -> bool:
        if not super().__bool__():
            return False
        if self.allow_chdir:
            return True
        return User32.GetWindowTextWEz(self.handler) == self.first_title

    @property
    def allow_chdir(self) -> bool:
        """エクスプローラのパス変更を許可するか。"""
        return self.__allow_chdir
