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
BASENAME = "FuyaoRimeYuanshu"


def identifier(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{REPOSITORY}/shortcuts/{BASENAME}/{name}")).upper()


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

    def if_empty(name, group, value):
        action(name, "conditional", GroupingIdentifier=identifier(group), WFControlFlowMode=0,
               WFCondition=101, WFInput={"Type": "Variable", "Variable": value})

    def end_if(name, group):
        action(name, "conditional", GroupingIdentifier=identifier(group), WFControlFlowMode=2)

    action("instructions", "comment", WFCommentActionText=(
        "FuyaoRime · 元书输入法全量更新\n"
        "选择元书当前使用的本地方案目录：我的 iPhone → 元书（Hamster3）→ RimeUserData → 当前方案文件夹。\n"
        "下方代理文本留空表示直连；填写 HTTP(S) 转发前缀后用于配置包下载，版本查询仍直连 GitHub。\n"
        "只下载全量包，不使用 diff；保存时跳过根目录的 installation.yaml、userdb 和 *.userdb。"
        "其他同名内容可能被覆盖，请先备份自定义配置。"
    ))
    action("folder", "file", WFFile={})
    action("proxy", "gettext", WFTextActionText=text(""), CustomOutputName="下载代理前缀")
    action("latest", "url.expand", URL=REPOSITORY + "/releases/latest")
    action("version", "text.match", text=text(output("latest", "Expanded URL")),
           WFMatchTextPattern=r"(?<=^https://github\.com/skyrocketingHong/FuyaoRime/releases/tag/v)[0-9]{8}$",
           WFMatchTextCaseSensitive=True)
    if_empty("invalid-version", "version-group", output("version", "Matches"))
    action("version-error", "alert", WFAlertActionTitle="无法确认 FuyaoRime 最新版本",
           WFAlertActionMessage="请检查 GitHub 连接后重试。本次没有写入配置文件。",
           WFAlertActionCancelButtonShown=False)
    action("stop-invalid-version", "exit")
    end_if("version-end", "version-group")

    action("raw-download-url", "gettext", WFTextActionText=text(
        output("proxy", "下载代理前缀"), REPOSITORY + "/releases/download/v",
        output("version", "Matches"), "/fuyaorime-", output("version", "Matches"), ".zip",
    ))
    # Replace Text's input must be a WFTextTokenString, not a bare attachment.
    action("trim-download-url", "text.replace", WFInput=text(output("raw-download-url")),
           WFReplaceTextFind=text(r"^\s+|\s+$"), WFReplaceTextReplace=text(""),
           WFReplaceTextRegularExpression=True, WFReplaceTextCaseSensitive=True)
    action("forwarded-download-url", "text.replace", WFInput=text(output("trim-download-url", "Updated Text")),
           WFReplaceTextFind=text(r"^(https?://[^\s]+?)[/\s]*(https://github\.com/skyrocketingHong/FuyaoRime/releases/download/\S+)$"),
           WFReplaceTextReplace=text("$1/$2"), WFReplaceTextRegularExpression=True,
           WFReplaceTextCaseSensitive=True)
    action("download-url", "url", WFURLActionURL=text(output("forwarded-download-url", "Updated Text")),
           CustomOutputName="配置包下载地址")
    action("package", "downloadurl", WFURL=text(output("download-url", "配置包下载地址")), WFHTTPMethod="GET")
    action("extract", "unzip", WFArchive=output("package", "Contents of URL"))
    action("install-items", "repeat.each", WFInput=output("extract", "Files"),
           GroupingIdentifier=identifier("install-items-group"), WFControlFlowMode=0)
    item = {"Value": {"Type": "Variable", "VariableName": "Repeat Item"},
            "WFSerializationType": "WFTextTokenAttachment"}
    item_name = {"Value": {**item["Value"], "Aggrandizements": [
        {"Type": "WFPropertyVariableAggrandizement", "PropertyName": "Name", "PropertyUserInfo": "WFItemName"},
    ]}, "WFSerializationType": "WFTextTokenAttachment"}
    action("protected-item", "text.match", text=text(item_name),
           WFMatchTextPattern=r"^(?:installation(?:\.yaml)?|userdb|.*\.userdb)$",
           WFMatchTextCaseSensitive=False)
    if_empty("writable-item", "protected-group", output("protected-item", "Matches"))
    action("install", "documentpicker.save", WFFolder=output("folder", "File"),
           WFInput=item, WFAskWhereToSave=False, WFSaveFileOverwrite=True, WFFileDestinationPath="")
    end_if("protected-end", "protected-group")
    action("install-items-end", "repeat.each", GroupingIdentifier=identifier("install-items-group"), WFControlFlowMode=2)
    action("deploy", "openurl", WFInput=DEPLOY_URL)

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
    source = args.output_dir / f"{BASENAME}.source.plist"
    workflow = build_workflow()
    source.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_XML, sort_keys=False))
    print(f"Source: {source}", flush=True)
    if args.unsigned_only:
        return
    destination = args.output_dir / f"{BASENAME}.shortcut"
    # The signer accepts a binary .shortcut input and writes reliably on the system volume.
    with tempfile.TemporaryDirectory(prefix="fuyaorime-shortcut-sign-") as directory:
        input_directory = Path(directory) / "source"
        input_directory.mkdir()
        signing_input = input_directory / destination.name
        signing_output = Path(directory) / destination.name
        signing_input.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_BINARY, sort_keys=False))
        subprocess.run(["/usr/bin/shortcuts", "sign", "--mode", "anyone", "--input", str(signing_input),
                        "--output", str(signing_output)], check=True)
        destination.write_bytes(signing_output.read_bytes())
    print(f"Shortcut: {destination}")


if __name__ == "__main__":
    main()
