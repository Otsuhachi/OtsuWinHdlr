import subprocess
import time

from pathlib import Path

from otsutil import Timer
from otsuvalidator import CPath

from .cfg import User32


class Window:
    """ウィンドウを操作するためのクラスです。
    """
    handlers: dict[int, 'Window'] = {}

    def __init__(self, title: str, timeout_seconds: int = 10, span_seconds: float = 0.05) -> None:
        """ウィンドウのタイトルからウィンドウを操作するためのインスタンスを生成します。

        Args:
            title (str): ウィンドウのタイトル。
            timeout_seconds (int, optional): インスタンス生成を失敗とみなすまでの秒数。 Defaults to 10.
            span_seconds (float, optional): ウィンドウが存在するかの確認間隔秒数。 Defaults to 0.05.

        Raises:
            TimeoutError: timeout_seconds秒内に発見できなかった場合に投げられます。
        """
        hdlr = 0
        handlers = Window.handlers
        for _ in Timer(seconds=timeout_seconds).wiggle_begin(span_seconds):
            if (hdlr := User32.FindWindowExW(None, None, None, title)) != 0:
                if hdlr in handlers:
                    Window.refresh()
                    if hdlr in handlers:
                        hdlr = 0
                        continue
                handlers[hdlr] = self
                self.__hdlr = hdlr
                break
        else:
            msg = f'ウィンドウ"{title}"のハンドルを取得できませんでした。'
            raise TimeoutError(msg)

    def close(self) -> int:
        """ウィンドウを閉じます。

        Returns:
            int: 応答。
        """
        res = User32.SendMessageW(self.handler, 0x0010, 0, 0)
        if self.handler in Window.handlers:
            del Window.handlers[self.handler]
        return res

    def join(self, span: float = 0.05) -> None:
        """ウィンドウが閉じるまで処理を待機させます。

        Args:
            span (float, optional): 確認する頻度秒。
        """
        while self:
            time.sleep(span)

    def move(self, x: int, y: int) -> bool:
        """ウィンドウを指定の座標に移動させます。

        Args:
            x (int): 左上X座標。
            y (int): 左上Y座標。

        Returns:
            bool: 成否。
        """
        if not self:
            return False
        w, h = self.size
        return User32.MoveWindow(self.__hdlr, x, y, w, h, True)

    @classmethod
    def refresh(cls) -> None:
        """現在取得しているハンドルから既に無効になっているものを取り除きます。
        """
        for wd in cls.handlers.values():
            if not wd:
                wd.close()

    def resize(self, width: int, height: int) -> bool:
        """ウィンドウを指定のサイズに変更します。

        Args:
            width (int): 幅。
            height (int): 高さ。

        Returns:
            bool: 成否。
        """
        if not self:
            return False
        x, y, *_ = self.rect
        return User32.MoveWindow(self.__hdlr, x, y, width, height, True)

    @property
    def handler(self) -> int:
        """ウィンドウハンドラ。
        """
        return self.__hdlr

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """ウィンドウの左上と右下の座標。

        Returns:
            tuple[int, int, int, int]: (lx, ly, rx, ry)のタプル。
        """
        return User32.GetWindowRect(self.handler)

    @property
    def size(self) -> tuple[int, int]:
        """ウィンドウの幅と高さ。
        """
        if not self:
            return -1, -1
        left, top, right, bottom = self.rect
        return abs(left - right), abs(top - bottom)

    @property
    def title(self) -> str:
        """ウィンドウのタイトル。
        """
        return User32.GetWindowTextW(self.handler)

    def __bool__(self) -> bool:
        if self.handler not in Window.handlers:
            return False
        return User32.IsWindowEnabled(self.__hdlr)

    def __str__(self) -> str:
        return f'{self.handler}: {self.title}(Window)'


class Explorer(Window):
    """ウィンドウの中でも特にエクスプローラを操作するためのクラス。
    """

    def __init__(self, path: Path | str, allow_chdir: bool = False, timeout_seconds: int = 10, span_seconds: float = 0.05) -> None:
        """pathのエクスプローラを開き、操作を行うインスタンスを生成します。

        Args:
            path (Path | str): 操作したいエクスプローラのパス。存在するフォルダのみ受付。
            allow_chdir (bool, optional): エクスプローラのパス変更を許可するかどうか。 不許可の場合は移動した時点でWindow.closeが呼び出される。 Defaults to False.
            timeout_seconds (int, optional): インスタンス生成を失敗とみなすまでの秒数。 Defaults to 10.
            span_seconds (float, optional): ウィンドウが存在するかの確認間隔秒数。 Defaults to 0.05.
        """
        path = CPath(exist_only=True, path_type=Path.is_dir).validate(path)
        subprocess.Popen(['explorer', path]).wait()
        super().__init__(path.name, timeout_seconds, span_seconds)
        self.__allow_chdir = allow_chdir
        self.__first_title = self.title

    def __bool__(self) -> bool:
        if not super().__bool__():
            return False
        if self.__allow_chdir:
            return True
        return User32.GetWindowTextW(self.handler) == self.__first_title

    def __str__(self) -> str:
        return f'{self.handler}: {self.title}(Explorer)'
