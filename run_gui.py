"""PyInstaller 打包入口：图形界面版。"""

from pathlib import Path

from source_mod_manager.config import get_steam_override
from source_mod_manager.detector import find_steam_path


def main() -> int:
    steam = find_steam_path(get_steam_override())
    if steam is None:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "未找到 Steam",
            "无法定位 Steam 安装目录。\n"
            "请先用命令行指定一次：\n"
            '  SourceModManagerCLI.exe scan --steam "你的Steam路径"\n'
            "例如：D:/Steam",
        )
        root.destroy()
        return 1
    from source_mod_manager.gui import run_gui
    run_gui(steam)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
