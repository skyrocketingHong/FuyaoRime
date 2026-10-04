# iOS 快捷指令：元书输入法

快捷指令使用 iOS 原生动作，每次下载最新的 FuyaoRime 全量包，将解压后的内容写入指定方案目录，再打开元书请求重新部署。无需安装终端或 Python 应用。

此版本不应用 diff，也不根据本地版本跳过下载。下载代理默认留空，版本查询始终直连 GitHub，配置包可通过自选的 HTTP(S) 代理前缀下载。

## 导入与设置

1. 将 `FuyaoRimeYuanshu.shortcut` 通过 AirDrop 或“文件”App 传到 iPhone，打开并添加到“快捷指令”。
2. 按导入提示选择元书当前使用的**本地方案文件夹**。位置通常为“我的 iPhone → 元书（Hamster3）→ RimeUserData → 当前方案目录”，例如 `rime-ice`。不要选择 `RimeUserData` 根目录、键盘目录或 iCloud 目录。
3. 下载代理前缀可以留空；需要转发服务时填写其完整 HTTP(S) 地址，末尾的 `/` 会自动处理。
4. 首次手动运行时，按系统提示允许访问 GitHub、所选代理和方案文件夹。

如果导入时没有出现设置提示，打开快捷指令编辑器，修改开头的“文件”动作和紧随其后的代理“文本”动作。

首次安装 FuyaoRime 时，可以先在 `RimeUserData` 下新建独立的方案目录。首次写入完成后，进入元书“输入方案 → 方案目录切换”选中该目录并重新部署；以后更新仍选择这个目录。

## 更新流程

1. 展开 GitHub `/releases/latest` 的跳转地址。
2. 确认地址属于 FuyaoRime，且标签符合 `vYYYYMMDD`。
3. 下载对应的 `fuyaorime-YYYYMMDD.zip` 全量包。
4. 解压并保存到已授权的方案目录，允许覆盖同名内容。
5. 使用元书的 URL 入口请求重新部署。如果没有自动部署，在元书内手动执行“RIME → 重新部署”。

运行前备份自行修改的配置，同名文件和文件夹可能被覆盖。建议保持前台运行并使用 Wi-Fi；全量包包含语言模型及扩展词库，下载和部署可能耗时较长。

如元书启用了从 iCloud 自动复制文件，需避免云端旧配置在部署时再次覆盖本地更新。具体文件流转以[元书文件管理说明](https://ihsiao.com/apps/hamster/v3/docs/guides/file-manager/)及应用当前设置为准。

可以在 iOS“快捷指令 → 自动化 → 特定时间”中添加“运行快捷指令”动作，但涉及目录授权或打开元书时仍可能要求解锁或确认。先手动完整运行一次，再设置自动化；不能将其视为保证后台完成的定时更新。

## 生成文件

在 Mac 上使用 Python 3 和系统自带的 `shortcuts` 命令：

```bash
python3 updater/build_ios_shortcut.py
```

产物位于 `dist/ios/`：

- `FuyaoRimeYuanshu.shortcut`：经过签名的导入文件。
- `FuyaoRimeYuanshu.source.plist`：可检查的 XML 源文件。
- `FuyaoRimeYuanshu.unsigned.shortcut`：供签名工具使用的二进制源文件。

签名采用 Apple 的 `anyone` 模式。Apple 会接收快捷指令副本用于验证；生成时未写入个人目录书签或联系信息。参见 [Apple 签名说明](https://support.apple.com/zh-cn/guide/shortcuts-mac/apd455c82f02/mac)。

只生成源文件时使用 `python3 updater/build_ios_shortcut.py --unsigned-only`。签名与结构检查不能代替 iPhone 上的目录授权、文件覆盖和元书部署验证。

## 参考

- [元书输入方案与目录结构](https://ihsiao.com/apps/hamster/v3/docs/guides/schema/)
- [Rime 万象更新工具的 iOS 实现](https://github.com/rimeinn/rime-wanxiang-update-tools/tree/main/iOS)：原生解压与保存动作格式。
- [Rime 万象更新工具的跨平台脚本](https://github.com/rimeinn/rime-wanxiang-update-tools/blob/main/Python-%E5%85%A8%E5%B9%B3%E5%8F%B0%E7%89%88%E6%9C%AC/Python/rime-wanxiang-update-all.py)：元书部署 URL。
