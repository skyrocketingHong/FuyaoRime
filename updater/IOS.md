# iOS 快捷指令：元书输入法

`FuyaoRimeYuanshu.shortcut` 是一体更新快捷指令，使用 iOS 原生动作依次完成版本查询、全量包下载、解压覆盖和请求元书部署。无需安装终端或 Python 应用。

每次运行下载最新全量包，不使用 diff，也不根据本地版本跳过下载。下载代理默认留空；填写 HTTP(S) 转发前缀后，它会直接用于配置包下载地址，版本查询仍直连 GitHub。

## 导入与设置

1. 将 `.shortcut` 文件通过 AirDrop 或“文件”App 传到 iPhone，打开并添加到“快捷指令”。更新已有快捷指令时选择替换旧版。
2. 选择元书当前使用的**本地方案文件夹**，通常位于“我的 iPhone → 元书（Hamster3）→ RimeUserData → 当前方案目录”，例如 `rime-ice`。不要选择 `RimeUserData` 根目录、键盘目录或 iCloud 目录。
3. 代理前缀可以留空直连；使用转发服务时填写其完整 HTTP(S) 地址。地址前后的空白和末尾的 `/` 会自动处理，也支持带路径的代理前缀。
4. 首次运行时，按系统提示允许网络和方案目录访问。

如果导入时没有出现设置提示，在编辑器开头修改“文件”动作和“下载代理前缀”文本动作。

首次安装 FuyaoRime 时，可以先在 `RimeUserData` 下新建独立的方案目录。首次写入完成后，进入元书“输入方案 → 方案目录切换”选中该目录并重新部署；以后继续使用同一目录。

## 更新流程

1. 展开 GitHub `/releases/latest` 的跳转，确认仓库和日期版本标签，支持 `vYYYYMMDD` 及同日修订版（如 `v20261010-v2`）；无法确认时停止。
2. 使用完整版本名组合下载地址，例如 `fuyaorime-20261010-v2.zip`，再获取其内容。前缀为空时直接下载。
3. 解压后逐项保存，跳过根目录的 `installation.yaml`、`userdb` 和所有 `*.userdb`。
4. 打开元书并请求重新部署。如果未自动部署，在元书内手动执行“RIME → 重新部署”。

快捷指令不清空所选目录，不执行删除清单。其他同名文件和文件夹可能被覆盖，运行前应备份自行修改的配置。用户数据库保护适用于所选方案根目录，不接管元书自身在部署时进行的键盘和 iCloud 数据同步。

如启用了从 iCloud 自动复制文件，需避免云端旧配置在部署时覆盖本地更新。具体规则以[元书文件管理说明](https://ihsiao.com/apps/hamster/v3/docs/guides/file-manager/)及应用设置为准。

## 运行提示

早期快捷指令只识别八位日期，不支持 `-v2` 等修订号。遇到“无法确认 FuyaoRime 最新版本”时，重新生成或导入新版快捷指令，并替换旧版。

全量包包含语言模型和扩展词库，“获取 URL 内容”可能需要较长时间，建议使用 Wi-Fi 并保持快捷指令在前台。下载速度取决于网络和所选代理；签名成功不代表已完成 iPhone 运行验证。

可在 iOS“快捷指令 → 自动化 → 特定时间”中添加“运行快捷指令”动作。先手动完整运行一次，再设置自动化；目录授权、网络请求和打开元书仍可能要求解锁或确认，不能保证后台完成。

## 生成文件

在 Mac 上使用 Python 3 和系统自带的 `shortcuts` 命令：

```bash
python3 updater/build_ios_shortcut.py
```

产物位于 `dist/ios/`：

- `FuyaoRimeYuanshu.shortcut`：唯一的签名导入文件。
- `FuyaoRimeYuanshu.source.plist`：可检查的 XML 源文件。

只生成源文件时添加 `--unsigned-only`。签名采用 Apple 的 `anyone` 模式：Apple 会接收快捷指令副本用于验证，生成时未写入个人目录书签或联系信息。参见 [Apple 签名说明](https://support.apple.com/zh-cn/guide/shortcuts-mac/apd455c82f02/mac)。

## 参考

- [元书输入方案与目录结构](https://ihsiao.com/apps/hamster/v3/docs/guides/schema/)
- [Rime 万象更新工具的 iOS 实现](https://github.com/rimeinn/rime-wanxiang-update-tools/tree/main/iOS)：原生解压与保存动作格式。
- [Rime 万象更新工具的跨平台脚本](https://github.com/rimeinn/rime-wanxiang-update-tools/blob/main/Python-%E5%85%A8%E5%B9%B3%E5%8F%B0%E7%89%88%E6%9C%AC/Python/rime-wanxiang-update-all.py)：元书部署 URL。
