# Source Mod Manager

**起源引擎 (Source Engine) 模组解析与启动管理器** —— 一键扫描、校验并运行放在模组文件夹下的所有适用于起源引擎的模组：**Half-Life 2 模组、Garry's Mod (GMod) 附加组件、Counter-Strike: Source (CS:S) 内容与地图**。

- 纯 Python 标准库实现，零第三方运行时依赖（图形界面使用 Tkinter）
- 提供命令行 (CLI) 与图形界面 (GUI) 两种用法
- GitHub Actions 云编译，自动产出 Windows / Linux 可直接运行的程序

## 它能做什么

| 能力 | 说明 |
| --- | --- |
| 自动定位 Steam | 读取 Windows 注册表或常见安装路径；也可手动指定并记住 |
| 解析起源引擎模组 | 扫描 `steamapps/sourcemods/`，解析 `gameinfo.txt`，自动识别引擎类型（HL2 / GMod / CS:S / TF2 / Portal…）并校验完整性 |
| 解析 GMod 附加组件 | 扫描 `GarrysMod/garrysmod/addons/`，识别目录型 addon 与 `.gma` 打包组件，校验可加载内容 |
| 扫描地图 | 扫描 HL2 / GMod / CS:S 安装目录下的全部 `.bsp` 地图 |
| 一键启动 | 自动调用正确引擎的可执行文件：模组用 `-game <模组名>`，地图直接 `+map <图名>` 进图 |
| 地图安装 | 把 `.bsp` 复制到任意游戏或模组的地图目录，自动检测重名 |
| JSON 输出 | `scan --json` 便于脚本化集成 |

## 工作原理与技术边界（重要）

起源引擎的每个模组本质上是独立的引擎程序，**不存在"在一个模组内部直接运行所有模组"这种机制** —— GMod 附加组件只能由 Garry's Mod 加载，CS:S 地图只能由 CS:S 加载，HL2 模组由 HL2 引擎加载。

因此本工具实现的是**现实中可行的完整功能**：解析并校验模组文件夹下的全部适用模组，识别各自引擎，然后调用正确的引擎二进制来运行它们。启动游戏时请保持 Steam 客户端运行（起源引擎受 Steam DRM 保护）。

## 快速开始

### 方式一：下载云编译好的程序（推荐 Windows 用户）

1. 前往本仓库 **Releases** 页（或 Actions 页面 Artifacts）下载：
   - `SourceModManagerGUI.exe` —— 图形界面版
   - `SourceModManagerCLI.exe` —— 命令行版
2. 首次使用先告诉工具 Steam 位置（会自动记住）：
   ```bat
   SourceModManagerCLI.exe scan --steam "D:/Steam"
   ```
3. 之后直接双击 `SourceModManagerGUI.exe` 即可。

### 方式二：使用 Python 源码运行

需要 Python 3.8+（含 Tkinter）：

```bash
# 扫描全部模组
python -m source_mod_manager scan

# 指定 Steam 目录（会记住）
python -m source_mod_manager scan --steam "C:/Program Files (x86)/Steam"

# 启动某个模组 / 组件 / 地图
python -m source_mod_manager launch my_mod
python -m source_mod_manager launch cool_addon
python -m source_mod_manager launch de_dust2.bsp

# 启动后直接进图
python -m source_mod_manager launch my_mod --map d1_trainstation_01

# 安装地图到目标游戏/模组
python -m source_mod_manager install-map ./newmap.bsp --target gmod

# 打开图形界面
python -m source_mod_manager gui
```

> 若模块方式不可用（如直接运行源码），请先 `pip install -e .` 或在 `src` 目录下运行。

## 命令参考

```
source-mod-manager [--steam <Steam路径>] <子命令>

子命令：
  scan [--json]                 扫描并解析全部模组
  launch <名称> [--engine hl2|gmod|css] [--map <图名>] [--kind <类型>]
                                启动模组/组件/地图
  install-map <地图.bsp> [--target hl2|gmod|css|mod:<模组名>] [--force]
                                安装地图
  gui                           打开图形界面
  steam                         显示定位到的 Steam 目录
```

`install-map --target` 可选值运行 `scan` 后可见；`mod:<模组名>` 表示装进某个模组自己的 maps 目录。

## 云编译 (GitHub Actions)

每次推送到 `main`（或打 `v*` 标签）都会自动：

1. 在 Ubuntu 上运行全部单元测试；
2. 在 Windows / Ubuntu 上分别用 PyInstaller **云编译**出 `SourceModManagerGUI` 与 `SourceModManagerCLI` 并上传构建产物；
3. 推送形如 `v1.0.0` 的标签时，自动创建 GitHub Release 并附带编译好的程序。

## 项目结构

```
source-mod-manager/
├── src/source_mod_manager/
│   ├── detector.py     # 模组解析：sourcemods / GMod addons / 地图扫描
│   ├── launcher.py     # 启动器：组装命令并调用正确引擎
│   ├── installer.py    # 地图安装器
│   ├── cli.py          # 命令行入口
│   ├── gui.py          # Tkinter 图形界面
│   └── config.py       # Steam 路径记忆
├── tests/              # 单元测试（CI 自动运行）
├── .github/workflows/build.yml  # 云编译流水线
├── run_cli.py          # PyInstaller CLI 入口
└── run_gui.py          # PyInstaller GUI 入口
```

## 常见问题

**找不到 Steam？** 用 `--steam` 手动指定一次即可，路径会被记住在 `~/.source_mod_manager/config.json`。

**提示模组"无效"？** 说明该目录缺少 `gameinfo.txt` 或没有可加载内容，通常是残留下载或放错位置的文件夹。

**启动没反应？** 请确认 Steam 已在运行，且对应游戏（HL2 / GMod / CS:S）已安装。

## 许可证

MIT License。仅供学习与个人使用，与 Valve 无关；Half-Life 2、Garry's Mod、Counter-Strike: Source 均为其各自权利人的商标。
