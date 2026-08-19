# signin_demo

东莞理工学院课程签到命令行工具，支持保存多个账号、启动时切换账号，以及直接运行的 Windows 单文件版本。
使用之后可以给我star吗！

> 使用本工具产生的风险由使用者自行承担。请遵守学校和课程的相关规定。

## 直接使用 EXE

下载 [`dist/ulearning-cmd.exe`](dist/ulearning-cmd.exe) 后双击运行，无需安装 Python 或其他依赖。

首次运行时输入账号和密码。登录成功后，程序会在 EXE 同目录生成 `ulearning-cmd.json`。该文件包含明文密码，请勿上传、转发或交给他人。

已有多个账号时，启动菜单支持：

- 输入账号前的序号进行切换；
- 直接回车继续使用当前账号；
- 输入 `N` 添加新账号。

也可以在命令行中直接指定账号：

```powershell
.\dist\ulearning-cmd.exe dgut账号
```

## 使用 Python 运行

需要 Python 3 和 `requests`：

```powershell
python -m pip install requests
python ulearning-cmd.py
```

也可以运行 `a.bat`。该脚本会自动使用自身目录中的 `ulearning-cmd.py`，并支持传递账号参数：

```powershell
.\a.bat dgut账号
```

## 配置文件

`ulearning-cmd.json` 中：

- `users` 保存所有账号；
- `activeUser` 表示默认账号；
- `activeUser` 必须与 `users` 中的账号键一致。

旧配置中带 `dgut` 前缀的 `activeUser` 与纯学号键不一致时，程序会自动迁移。

## 本地构建 EXE

```powershell
python -m pip install requests pyinstaller
python -m PyInstaller --clean --noconfirm --onefile --console --name ulearning-cmd ulearning-cmd.py
```

生成文件位于 `dist/ulearning-cmd.exe`。

## 测试

账号切换测试只使用临时配置，不会登录或签到：

```powershell
python -B test_accounts.py
```
