import ctypes
import ctypes.wintypes as wintypes

from typing import Optional, cast


class User32:
    """user32.dllのAPIの一部を使いやすくしたクラス。

    現在実装されている関数は以下の通りです。
    関数名の前に"[O]"が付いているものについては戻り値の型や一部処理の省略など簡素化された関数と、DLLオリジナルの関数の二つが実装されており、"O<func_name>"の方がオリジナルになります。

    - FindWindowExW
    - [O]GetWindowRect
    - GetWindowTextLengthW
    - [O]GetWindowTextW
    - IsWindowEnabled
    - MoveWindow
    - SendMessageW
    - SetActivewindow
    - SetFocus
    - SetForegroundWindow
    """

    @staticmethod
    def FindWindowExW(
        hWndParent: Optional[int] = None,
        hWndChildAfter: Optional[int] = None,
        lpszClass: Optional[str] = None,
        lpszWindow: Optional[str] = None,
    ) -> int:
        """クラス名とウィンドウ名が指定した文字列と一致するウィンドウのハンドルを取得します。

        Args:
            hWndParent (Optional[int], optional): 子ウィンドウを検索する親ウィンドウハンドル。
            hWndChildAfter (Optional[int], optional): 子ウィンドウハンドル。
            lpszClass (Optional[str], optional): クラス名またはクラスアトム。
            lpszWindow (Optional[str], optional): ウィンドウ名。

        Returns:
            int: ウィンドウハンドル。
        """
        return ctypes.windll.user32.FindWindowExW(hWndParent, hWndChildAfter, lpszClass, lpszWindow)

    @staticmethod
    def GetWindowRect(hWnd: int) -> tuple[int, int, int, int]:
        """ウィンドウの左上座標, 右下座標を返します。

        DLL本体のGetWindowRectを簡素化しています。
        本来のGetWindowRectを使用したい場合にはOGetWindowRectを使用してください。

        Args:
            hWnd (int): ウィンドウハンドル。

        Returns:
            tuple[int, int, int, int]: (左x座標, 左y座標, 右x座標, 右y座標)のタプル。
        """
        rect = wintypes.RECT()
        if not User32.OGetWindowRect(hWnd, ctypes.pointer(rect)):
            return -1, -1, -1, -1

        return cast(tuple[int, int, int, int], (rect.left, rect.top, rect.right, rect.bottom))

    @staticmethod
    def GetWindowTextLengthW(hWnd: int) -> int:
        """ウィンドウのタイトルテキストの文字数を返します。

        Args:
            hWnd (int): ウィンドウハンドル。

        Returns:
            int: ウィンドウのタイトルテキストの文字数または0。
        """
        return ctypes.windll.user32.GetWindowTextLengthW(hWnd)

    @staticmethod
    def GetWindowTextW(hWnd: int) -> str:
        """ウィンドウのタイトルの文字列を返します。

        DLL本来のGetWindowTextWを簡素化しています。
        本来のGetWindowTextWを使用したい場合にはOGetWindowTextWを使用してください。

        Args:
            hWnd (int): ウィンドウハンドル。

        Returns:
            str: ウィンドウのタイトル。
        """
        text_length = User32.GetWindowTextLengthW(hWnd) + 1
        title = ctypes.create_unicode_buffer(text_length)
        User32.OGetWindowTextW(hWnd, title, text_length)
        return title.value

    @staticmethod
    def IsWindowEnabled(hWnd: int) -> bool:
        """ウィンドウがマウスとキーボードの入力に対して有効になっているかどうかを返します。

        Args:
            hWnd (int): ウィンドウハンドル。

        Returns:
            bool: 有効かどうか。
        """
        return bool(ctypes.windll.user32.IsWindowEnabled(hWnd))

    @staticmethod
    def MoveWindow(hWnd: int, X: int, Y: int, nWidth: int, nHeight: int, bRepaint: bool) -> bool:
        """ウィンドウを指定座標に動かします。

        Args:
            hWnd (int): ウィンドウハンドル。
            X (int): 左上X座標。
            Y (int): 左上Y座標。
            nWidth (int): ウィンドウの幅
            nHeight (int): ウィンドウの高さ
            bRepaint (bool): 再描画の有無。

        Returns:
            bool: 成否。
        """
        return bool(ctypes.windll.user32.MoveWindow(hWnd, X, Y, nWidth, nHeight, bRepaint))

    @staticmethod
    def OGetWindowRect(hWnd: int, lpRect: wintypes.LPRECT) -> bool:
        """DLL本来のGetWindowRectです。

        Args:
            hWnd (int): ウィンドウハンドル。
            lpRect (wintypes.LPRECT): RECT構造体へのポインタ。

        Returns:
            bool: 成否。
        """
        return bool(ctypes.windll.user32.GetWindowRect(hWnd, lpRect))

    @staticmethod
    def OGetWindowTextW(hWnd: int, lpString: ctypes.Array[wintypes.WCHAR], nMaxCount: int) -> int:
        """DLL本来のGetWindowTextWです。

        Args:
            hWnd (int): ウィンドウハンドル。
            lpString (ctypes.Array[wintypes.WCHAR]): テキストを受け取るバッファー。
            nMaxCount (int): バッファにコピーする最大文字数。

        Returns:
            int: コピーされた文字列の長さ、または0。
        """
        return ctypes.windll.user32.GetWindowTextW(hWnd, lpString, nMaxCount)

    @staticmethod
    def SendMessageW(
        hWnd: int,
        Msg: int,
        wParam: int,
        lParam: int,
    ) -> int:
        """指定したメッセージをウィンドウに送信します。

        Args:
            hWnd (int): ウィンドウハンドル。
            Msg (int): 送信するメッセージ。
            wParam (int): 追加のメッセージ固有情報。
            lParam (int): 追加のメッセージ固有情報。

        Returns:
            int: ウィンドウからの応答。
        """
        return ctypes.windll.user32.SendMessageW(hWnd, Msg, wParam, lParam)

    @staticmethod
    def SetActiveWindow(hWnd: int) -> int:
        """ウィンドウをアクティブ化します。

        Args:
            hWnd (int): ウィンドウハンドル。

        Returns:
            int: 以前アクティブだったウィンドウのハンドル。または0。
        """
        return ctypes.windll.user32.SetActiveWindow(hWnd)

    @staticmethod
    def SetFocus(hWnd: int) -> int:
        """キーボードフォーカスをウィンドウに設定します。

        Args:
            hWnd (int): ウィンドウハンドル。

        Returns:
            int: 以前キーボードフォーカスを持っていたウィンドウのハンドル。または0。
        """
        return ctypes.windll.user32.SetFocus(hWnd)

    @staticmethod
    def SetForegroundWindow(hWnd: int) -> bool:
        """ウィンドウを作成したスレッドをフォアグラウンドに移動し、ウィンドウをアクティブにします。

        Args:
            hWnd (int): ウィンドウハンドル。

        Returns:
            bool: 成否。
        """
        return bool(ctypes.windll.user32.SetForegroundWindow(hWnd))
