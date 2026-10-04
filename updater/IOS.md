# iOS 快捷指令：元书输入法

快捷指令使用 iOS 原生动作，无需安装终端或 Python 应用。推荐将下载与部署分为两步：浏览器负责下载并显示进度，部署快捷指令处理已下载的本地 ZIP，再打开元书请求重新部署。

三个快捷指令都只使用全量包，不根据本地版本跳过下载。下载代理默认留空，版本查询始终直连 GitHub，配置包可通过自选的 HTTP(S) 代理前缀下载。

| 快捷指令 | 功能 |
| :--- | :--- |
| `FuyaoRimeDownload.shortcut` | 查询最新版，拼接全量包地址并交浏览器下载 |
| `FuyaoRimeYuanshuDeploy.shortcut` | 选择本地全量 ZIP，解压、保存到元书方案目录并请求部署 |
| `FuyaoRimeYuanshu.shortcut` | 可选的一体版，在快捷指令内部完成下载与部署 |

## 导入与设置

1. 将下载和部署两个 `.shortcut` 文件通过 AirDrop 或“文件”App 传到 iPhone，打开并添加到“快捷指令”。
2. 下载快捷指令中的代理前缀可以留空；需要转发服务时填写其完整 HTTP(S) 地址，末尾的 `/` 会自动处理。
3. 部署快捷指令需要选择元书当前使用的**本地方案文件夹**。位置通常为“我的 iPhone → 元书（Hamster3）→ RimeUserData → 当前方案目录”，例如 `rime-ice`。不要选择 `RimeUserData` 根目录、键盘目录或 iCloud 目录。
4. 首次运行时，按系统提示允许网络和方案目录访问。

如果导入时没有出现设置提示，在编辑器中修改下载快捷指令开头的代理“文本”动作，以及部署快捷指令开头的“文件”动作。

首次安装 FuyaoRime 时，可以先在 `RimeUserData` 下新建独立的方案目录。首次写入完成后，进入元书“输入方案 → 方案目录切换”选中该目录并重新部署；以后更新仍选择这个目录。

## 更新流程

1. 运行“FuyaoRime 下载配置”。它展开 GitHub `/releases/latest` 的跳转，确认仓库和 `vYYYYMMDD` 标签后，在浏览器中打开对应的全量包地址。
2. 在浏览器中确认下载，等待 `fuyaorime-YYYYMMDD.zip` 完整保存。浏览器可显示下载进度。
3. 运行“FuyaoRime 元书部署”，选择下载好的 ZIP；也可在“文件”App 中共享该 ZIP，选择同名部署快捷指令。已经下载好的包可直接从这一步开始。
4. 部署快捷指令检查文件名，拒绝 diff 包，再解压并保存到已授权的方案目录，允许覆盖同名内容。
5. 打开元书并请求重新部署。如果没有自动部署，在元书内手动执行“RIME → 重新部署”。

部署版不联网下载，不应选择尚未完成的临时下载文件。浏览器为重名文件添加的数字后缀可以保留。

## 一体版的下载等待

一体版使用“获取 URL 内容”下载整个配置包，全量包较大时，这一步可能长时间等待。“获取 Text 的内容”中的 Text 是输入变量的显示名称，不能仅据此认定 URL 类型出错。

若同一台 iPhone 在浏览器中能正常下载，但一体版一直等待，可以使用上面的两步方式。签名和结构校验无法确认具体的 iOS 下载问题，也不能保证一体版完成大文件下载。

运行前备份自行修改的配置，同名文件和文件夹可能被覆盖。建议保持前台运行并使用 Wi-Fi；全量包包含语言模型及扩展词库，下载和部署可能耗时较长。

如元书启用了从 iCloud 自动复制文件，需避免云端旧配置在部署时再次覆盖本地更新。具体文件流转以[元书文件管理说明](https://ihsiao.com/apps/hamster/v3/docs/guides/file-manager/)及应用当前设置为准。

两步更新需要确认浏览器下载并选择本地文件，适合手动执行。一体版可以在 iOS“快捷指令 → 自动化 → 特定时间”中添加“运行快捷指令”动作，但目录授权、下载和打开元书仍可能要求解锁或确认，不能视为保证后台完成的定时更新。

## 生成文件

在 Mac 上使用 Python 3 和系统自带的 `shortcuts` 命令：

```bash
python3 updater/build_ios_shortcut.py
```

产物位于 `dist/ios/`：

- 表格中的三个 `.shortcut` 文件：经过签名的导入文件。
- 对应的 `.source.plist` 文件：可检查的 XML 源文件。
- 对应的 `.unsigned.shortcut` 文件：供签名工具使用的二进制源文件。

签名采用 Apple 的 `anyone` 模式。Apple 会接收快捷指令副本用于验证；生成时未写入个人目录书签或联系信息。参见 [Apple 签名说明](https://support.apple.com/zh-cn/guide/shortcuts-mac/apd455c82f02/mac)。

只生成部署版可使用 `python3 updater/build_ios_shortcut.py --variant deploy`；只生成源文件时添加 `--unsigned-only`。签名与结构检查不能代替 iPhone 上的目录授权、文件覆盖和元书部署验证。

## 参考

- [元书输入方案与目录结构](https://ihsiao.com/apps/hamster/v3/docs/guides/schema/)
- [Rime 万象更新工具的 iOS 实现](https://github.com/rimeinn/rime-wanxiang-update-tools/tree/main/iOS)：原生解压与保存动作格式。
- [Rime 万象更新工具的跨平台脚本](https://github.com/rimeinn/rime-wanxiang-update-tools/blob/main/Python-%E5%85%A8%E5%B9%B3%E5%8F%B0%E7%89%88%E6%9C%AC/Python/rime-wanxiang-update-all.py)：元书部署 URL。
