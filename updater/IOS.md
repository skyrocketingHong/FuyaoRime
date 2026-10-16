# 元书自动更新

`FuyaoRimeYuanshu.shortcut` 每次下载最新全量包，覆盖所选方案目录并请求元书重新部署。

## 首次设置

1. 将 `.shortcut` 文件通过 AirDrop 或“文件”App 传到 iPhone，打开并添加到“快捷指令”。更新旧版时选择替换。
2. 选择元书当前使用的**本地方案文件夹**，例如“我的 iPhone → 元书（Hamster3）→ RimeUserData → rime-ice”。不要选 `RimeUserData` 根目录、键盘目录或 iCloud 目录。
3. 下载代理留空即可直连。需要转发服务时填写完整 HTTP(S) 前缀；它只影响配置包下载，版本查询仍直连 GitHub。

没有出现设置提示时，在快捷指令编辑器开头修改“文件”和“下载代理前缀”动作。首次安装可在 `RimeUserData` 下新建方案文件夹；更新完成后，在元书“输入方案 → 方案目录切换”中选中它。

## 运行更新

运行快捷指令，按提示允许网络和目录访问，等待下载、解压和覆盖完成。全量包较大，建议使用 Wi-Fi 并保持快捷指令在前台。

完成后会打开元书并请求部署。若未自动执行，在元书中手动选择“RIME → 重新部署”。

更新保留原有目录及根目录的 `installation.yaml`、`userdb` 和所有 `*.userdb`；其他同名配置会被覆盖，请先备份自定义内容。启用 iCloud 自动复制时，云端旧配置可能覆盖本地更新，见[文件管理说明](https://ihsiao.com/apps/hamster/v3/docs/guides/file-manager/)。

## 自动化与字体

先手动运行成功，再在“快捷指令 → 自动化 → 特定时间”中添加“运行快捷指令”。执行时可能需要解锁或确认授权。

字体在元书中单独设置，见[字体清单](../FONTS.md)。

<details>
<summary>在 Mac 上生成快捷指令</summary>

需要 Python 3 和系统自带的 `shortcuts` 命令。在仓库根目录运行：

```bash
python3 updater/build_ios_shortcut.py
```

导入文件为 `dist/ios/FuyaoRimeYuanshu.shortcut`，同时输出可检查的 `FuyaoRimeYuanshu.source.plist`。只生成源文件时添加 `--unsigned-only`。

</details>
