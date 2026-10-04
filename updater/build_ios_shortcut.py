#!/usr/bin/env python3
"""Build the native iOS shortcut for updating FuyaoRime in Yuanshu."""

import argparse
from pathlib import Path
import plistlib
import subprocess
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/skyrocketingHong/FuyaoRime"
DEPLOY_URL = "hamster3://dev.fuxiao.app.hamster3/rime?action=deploy"


def identifier(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{REPOSITORY}/shortcuts/{name}")).upper()


def output(name, label="Text"):
    return {
        "Value": {"Type": "ActionOutput", "OutputUUID": identifier(name), "OutputName": label},
        "WFSerializationType": "WFTextTokenAttachment",
    }


def text(*parts):
    value = ""
    attachments = {}
    for part in parts:
        if isinstance(part, str):
            value += part
        else:
            # Shortcuts ranges use UTF-16 offsets, including for non-ASCII labels.
            offset = len(value.encode("utf-16-le")) // 2
            attachments[f"{{{offset}, 1}}"] = part["Value"]
            value += "\ufffc"
    return {
        "Value": {"string": value, "attachmentsByRange": attachments},
        "WFSerializationType": "WFTextTokenString",
    }


def build_workflow():
    actions = []

    def action(name, kind, **parameters):
        actions.append({
            "WFWorkflowActionIdentifier": "is.workflow.actions." + kind,
            "WFWorkflowActionParameters": {"UUID": identifier(name), **parameters},
        })

    def condition(name, group, mode, value=None):
        parameters = {"GroupingIdentifier": identifier(group), "WFControlFlowMode": mode}
        if value is not None:
            parameters.update(WFCondition=100, WFInput={"Type": "Variable", "Variable": value})
        action(name, "conditional", **parameters)

    action("instructions", "comment", WFCommentActionText=(
        "FuyaoRime · 元书输入法全量更新\n"
        "运行前，请把下方文件夹设为元书当前使用的本地方案目录："
        "我的 iPhone → 元书（Hamster3）→ RimeUserData → 当前方案文件夹。"
        "不要选择 RimeUserData 根目录或 iCloud 目录。\n"
        "代理前缀留空表示直连；需要转发下载时填写 HTTP(S) 前缀。\n"
        "每次运行下载最新全量包并覆盖同名文件，不使用 diff，不清空目录。"
        "最后打开元书并请求重新部署。请先备份自己修改过的配置。"
    ))
    action("folder", "file", WFFile={})
    action("proxy", "gettext", WFTextActionText="")
    action("trim-proxy", "text.replace", WFInput=output("proxy"),
           WFReplaceTextFind="/+$", WFReplaceTextReplace="",
           WFReplaceTextRegularExpression=True, WFReplaceTextCaseSensitive=True)
    condition("proxy-if", "proxy-group", 0, output("trim-proxy", "Updated Text"))
    action("proxy-prefix", "gettext", WFTextActionText=text(output("trim-proxy", "Updated Text"), "/"))
    condition("proxy-else", "proxy-group", 1)
    action("direct-prefix", "gettext", WFTextActionText="")
    condition("download-prefix", "proxy-group", 2)
    action("latest", "url.expand", URL=REPOSITORY + "/releases/latest")
    action("version", "text.match", text=text(output("latest", "Expanded URL")),
           WFMatchTextPattern=r"(?<=^https://github\.com/skyrocketingHong/FuyaoRime/releases/tag/v)[0-9]{8}$",
           WFMatchTextCaseSensitive=True)
    condition("version-if", "version-group", 0, output("version", "Matches"))
    action("download-url", "gettext", WFTextActionText=text(
        output("download-prefix", "If Result"), REPOSITORY + "/releases/download/v",
        output("version", "Matches"), "/fuyaorime-", output("version", "Matches"), ".zip",
    ))
    action("package", "downloadurl", WFURL=text(output("download-url")), WFHTTPMethod="GET")
    action("extract", "unzip", WFArchive=output("package", "Contents of URL"))
    action("install", "documentpicker.save", WFFolder=output("folder", "File"),
           WFInput=output("extract", "Files"), WFAskWhereToSave=False,
           WFSaveFileOverwrite=True, WFFileDestinationPath="")
    action("deploy", "openurl", WFInput=DEPLOY_URL)
    condition("version-else", "version-group", 1)
    action("version-error", "alert", WFAlertActionTitle="无法确认 FuyaoRime 最新版本",
           WFAlertActionMessage="请检查 GitHub 连接后重试。本次没有写入配置文件。",
           WFAlertActionCancelButtonShown=False)
    condition("version-end", "version-group", 2)

    return {
        "WFWorkflowName": "FuyaoRime 元书更新",
        "WFWorkflowClientVersion": "5111.0.1",
        "WFWorkflowMinimumClientVersion": 3010,
        "WFWorkflowMinimumClientVersionString": "3010",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 946986751, "WFWorkflowIconGlyphNumber": 61440},
        "WFWorkflowActions": actions,
        "WFWorkflowInputContentItemClasses": [],
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowHasShortcutInputVariables": False,
        "WFQuickActionSurfaces": [],
        "WFWorkflowTypes": ["WFWorkflowTypeShowInSearch"],
        "WFWorkflowImportQuestions": [
            {"ParameterKey": "WFFile", "Category": "Parameter", "ActionIndex": 1,
             "Text": "选择元书当前使用的本地方案文件夹（我的 iPhone → 元书 → RimeUserData → 当前方案目录）",
             "DefaultValue": {}},
            {"ParameterKey": "WFTextActionText", "Category": "Parameter", "ActionIndex": 2,
             "Text": "GitHub 下载代理前缀，可留空直连；仅影响配置包下载", "DefaultValue": ""},
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist" / "ios")
    parser.add_argument("--unsigned-only", action="store_true", help="Only emit the inspectable source plist")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = args.output_dir / "FuyaoRimeYuanshu.source.plist"
    workflow = build_workflow()
    source.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_XML, sort_keys=False))
    print(f"Source: {source}", flush=True)
    if not args.unsigned_only:
        unsigned = args.output_dir / "FuyaoRimeYuanshu.unsigned.shortcut"
        unsigned.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_BINARY, sort_keys=False))
        destination = args.output_dir / "FuyaoRimeYuanshu.shortcut"
        # Sign on the system volume before copying to an external checkout.
        with tempfile.TemporaryDirectory(prefix="fuyaorime-shortcut-sign-") as directory:
            signing_input = Path(directory) / "input.shortcut"
            signing_output = Path(directory) / "output.shortcut"
            signing_input.write_bytes(unsigned.read_bytes())
            subprocess.run(["/usr/bin/shortcuts", "sign", "--mode", "anyone", "--input", str(signing_input),
                            "--output", str(signing_output)], check=True)
            destination.write_bytes(signing_output.read_bytes())
        print(f"Shortcut: {destination}")


if __name__ == "__main__":
    main()
