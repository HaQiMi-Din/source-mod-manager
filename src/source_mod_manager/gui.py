"""Tkinter 图形界面：扫描结果列表 + 启动 / 安装地图 / 打开目录。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from .detector import SourceMod, scan_all
from .installer import install_map, list_install_targets
from .launcher import LaunchError, launch


def run_gui(steam: Path) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    mods: Dict[str, SourceMod] = {}          # tree item id -> SourceMod
    last_scan_path = Path.home() / ".source_mod_manager" / "last_scan.txt"

    def refresh() -> None:
        result = scan_all(steam)
        tree.delete(*tree.get_children())
        mods.clear()
        groups = [
            ("起源引擎模组 (sourcemods)", result["sourcemods"]),
            ("GMod 附加组件 (addons)", result["gmod_addons"]),
            ("地图 (.bsp)", result["maps"]),
        ]
        for label, items in groups:
            parent = tree.insert("", "end", text=label, open=True)
            for m in items:
                status = "OK" if m.valid else "无效"
                iid = tree.insert(
                    parent, "end", text=m.name,
                    values=(m.kind_label, m.engine, status, f"{m.size_mb:.1f} MB"),
                )
                mods[iid] = m
        try:
            last_scan_path.parent.mkdir(parents=True, exist_ok=True)
            lines = []
            for label, items in groups:
                lines.append(f"== {label} ==")
                lines += [m.summary for m in items]
            last_scan_path.write_text("\n".join(lines), encoding="utf-8")
        except OSError:
            pass
        status_var.set(
            f"扫描完成：模组 {len(result['sourcemods'])} · "
            f"GMod 组件 {len(result['gmod_addons'])} · 地图 {len(result['maps'])}"
        )

    def selected() -> Optional[SourceMod]:
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个模组 / 附加组件 / 地图")
            return None
        return mods.get(sel[0])

    def do_launch() -> None:
        m = selected()
        if m is None:
            return
        if not m.valid:
            if not messagebox.askyesno("警告", f"{m.name} 解析不完整，仍尝试启动吗？"):
                return
        try:
            proc = launch(steam, m)
        except LaunchError as exc:
            messagebox.showerror("启动失败", str(exc))
            return
        status_var.set(f"已启动 {m.name} (PID {proc.pid})，请保持 Steam 运行")

    def do_install_map() -> None:
        m = selected()
        if m is None or m.kind != "map_file":
            messagebox.showinfo("提示", "请先选择一张地图(.bsp)，再点击「安装地图」")
            return
        targets = list_install_targets(steam)
        if not targets:
            messagebox.showerror("无目标", "没有可用的安装目标，请确认已安装 HL2 / GMod / CS:S。")
            return

        win = tk.Toplevel(root)
        win.title("选择安装目标")
        win.transient(root)
        win.grab_set()
        tk.Label(win, text=f"把 {m.name}.bsp 安装到哪里？", anchor="w").pack(fill="x", padx=12, pady=8)
        var = tk.StringVar(value=targets[0].key)
        for t in targets:
            tk.Radiobutton(win, text=f"[{t.key}] {t.label}", variable=var,
                           value=t.key, anchor="w").pack(fill="x", padx=20)

        def ok() -> None:
            for t in targets:
                if t.key == var.get():
                    try:
                        dest = install_map(m.path, t, force=True)
                    except Exception as exc:  # noqa: BLE001 - GUI 兜底提示
                        messagebox.showerror("安装失败", str(exc))
                        break
                    messagebox.showinfo("完成", f"已安装到:\n{dest}")
                    refresh()
                    break
            win.destroy()

        tk.Button(win, text="安装", command=ok).pack(pady=8)

    def do_open_dir() -> None:
        m = selected()
        if m is None:
            return
        target = m.path if m.path.is_dir() else m.path.parent
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(target)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except OSError as exc:
            messagebox.showerror("无法打开目录", str(exc))

    root = tk.Tk()
    root.title("Source Mod Manager")
    root.geometry("880x580")

    top = tk.Frame(root)
    top.pack(fill="x", padx=8, pady=8)
    tk.Button(top, text="刷新扫描", command=refresh).pack(side="left")
    tk.Button(top, text="启动", command=do_launch).pack(side="left", padx=4)
    tk.Button(top, text="安装地图…", command=do_install_map).pack(side="left")
    tk.Button(top, text="打开所在目录", command=do_open_dir).pack(side="left", padx=4)
    tk.Label(top, text=f"Steam: {steam}", fg="#666").pack(side="right")

    tree = ttk.Treeview(root, columns=("kind", "engine", "status", "size"),
                        show="tree headings")
    tree.heading("#0", text="名称")
    tree.heading("kind", text="类型")
    tree.heading("engine", text="引擎")
    tree.heading("status", text="状态")
    tree.heading("size", text="大小")
    tree.column("#0", width=320)
    tree.column("kind", width=160)
    tree.column("engine", width=90)
    tree.column("status", width=80)
    tree.column("size", width=90)
    tree.pack(fill="both", expand=True, padx=8, pady=(0, 4))
    tree.bind("<Double-1>", lambda _e: do_launch())

    status_var = tk.StringVar(value="就绪，点击「刷新扫描」开始")
    tk.Label(root, textvariable=status_var, anchor="w", fg="#333").pack(fill="x", padx=8, pady=(0, 6))

    refresh()
    root.mainloop()
