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
VARIANTS = {
    "download": ("FuyaoRimeDownload", "FuyaoRime 下载配置"),
    "deploy": ("FuyaoRimeYuanshuDeploy", "FuyaoRime 元书部署"),
    "update": ("FuyaoRimeYuanshu", "FuyaoRime 元书更新"),
}


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


def build_workflow(variant="update"):
    actions = []
    questions = []

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

    def install(package):
        action("extract", "unzip", WFArchive=package)
        action("install", "documentpicker.save", WFFolder=output("folder", "File"),
               WFInput=output("extract", "Files"), WFAskWhereToSave=False,
               WFSaveFileOverwrite=True, WFFileDestinationPath="")
        action("deploy", "openurl", WFInput=DEPLOY_URL)

    instructions = (
        "先运行“FuyaoRime 下载配置”，在浏览器中完成全量包下载，"
        "再运行“FuyaoRime 元书部署”选择下载好的 ZIP。\n"
        "部署目录应为：我的 iPhone → 元书（Hamster3）→ RimeUserData → 当前方案文件夹。"
        "不要选择 RimeUserData 根目录或 iCloud 目录。\n"
        "仅使用全量包，不支持 diff；同名内容可能被覆盖，请先备份自定义配置。"
    )
    if variant == "update":
        instructions = "此一体版在快捷指令内下载大文件。若下载长期等待，请改用下载与部署两个独立快捷指令。\n" + instructions
    action("instructions", "comment", WFCommentActionText=instructions)

    if variant != "download":
        questions.append({"ParameterKey": "WFFile", "Category": "Parameter", "ActionIndex": len(actions),
                          "Text": "选择元书当前使用的本地方案文件夹（我的 iPhone → 元书 → RimeUserData → 当前方案目录）",
                          "DefaultValue": {}})
        action("folder", "file", WFFile={})

    if variant == "deploy":
        shortcut_input = {"Value": {"Type": "ExtensionInput"}, "WFSerializationType": "WFTextTokenAttachment"}
        condition("input-if", "input-group", 0, shortcut_input)
        action("shared-package", "getvariable", WFVariable=shortcut_input)
        condition("input-else", "input-group", 1)
        action("select-package", "documentpicker.open", WFShowFilePicker=True, WFSelectMultiple=False)
        condition("chosen-package", "input-group", 2)
        filename = output("chosen-package", "If Result")
        filename["Value"]["Aggrandizements"] = [
            {"Type": "WFPropertyVariableAggrandizement", "PropertyName": "Name", "PropertyUserInfo": "WFItemName"},
        ]
        action("full-package-name", "text.match", text=text(filename),
               WFMatchTextPattern=r"^fuyaorime-[0-9]{8}(?: (?:\([0-9]+\)|[0-9]+))?(?:\.zip)?$",
               WFMatchTextCaseSensitive=False)
        condition("full-package-if", "full-package-group", 0, output("full-package-name", "Matches"))
        install(output("chosen-package", "If Result"))
        condition("full-package-else", "full-package-group", 1)
        action("package-error", "alert", WFAlertActionTitle="请选择 FuyaoRime 全量包",
               WFAlertActionMessage="选择下载完成的 fuyaorime-YYYYMMDD.zip。此快捷指令不接受 diff 包，也不会修改当前配置。",
               WFAlertActionCancelButtonShown=False)
        condition("full-package-end", "full-package-group", 2)
    else:
        questions.append({"ParameterKey": "WFTextActionText", "Category": "Parameter", "ActionIndex": len(actions),
                          "Text": "GitHub 下载代理前缀，可留空直连；仅影响配置包下载", "DefaultValue": ""})
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
        action("download-url", "url", WFURLActionURL=text(
            output("download-prefix", "If Result"), REPOSITORY + "/releases/download/v",
            output("version", "Matches"), "/fuyaorime-", output("version", "Matches"), ".zip",
        ), CustomOutputName="配置包下载地址")
        if variant == "download":
            action("browser-download", "openurl", WFInput=output("download-url", "URL"))
        else:
            action("package", "downloadurl", WFURL=text(output("download-url", "URL")), WFHTTPMethod="GET")
            install(output("package", "Contents of URL"))
        condition("version-else", "version-group", 1)
        action("version-error", "alert", WFAlertActionTitle="无法确认 FuyaoRime 最新版本",
               WFAlertActionMessage="请检查 GitHub 连接后重试。本次没有写入配置文件。",
               WFAlertActionCancelButtonShown=False)
        condition("version-end", "version-group", 2)

    return {
        "WFWorkflowName": VARIANTS[variant][1],
        "WFWorkflowClientVersion": "5111.0.1",
        "WFWorkflowMinimumClientVersion": 3010,
        "WFWorkflowMinimumClientVersionString": "3010",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 946986751, "WFWorkflowIconGlyphNumber": 61440},
        "WFWorkflowActions": actions,
        "WFWorkflowInputContentItemClasses": ["WFGenericFileContentItem"] if variant == "deploy" else [],
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowHasShortcutInputVariables": False,
        "WFQuickActionSurfaces": [],
        "WFWorkflowTypes": ["ActionExtension", "WFWorkflowTypeShowInSearch"] if variant == "deploy" else ["WFWorkflowTypeShowInSearch"],
        "WFWorkflowImportQuestions": questions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist" / "ios")
    parser.add_argument("--variant", choices=[*VARIANTS, "all"], default="all")
    parser.add_argument("--unsigned-only", action="store_true", help="Only emit the inspectable source plist")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    variants = VARIANTS if args.variant == "all" else [args.variant]
    for variant in variants:
        basename = VARIANTS[variant][0]
        source = args.output_dir / f"{basename}.source.plist"
        workflow = build_workflow(variant)
        source.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_XML, sort_keys=False))
        print(f"Source: {source}", flush=True)
        if args.unsigned_only:
            continue
        unsigned = args.output_dir / f"{basename}.unsigned.shortcut"
        unsigned.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_BINARY, sort_keys=False))
        destination = args.output_dir / f"{basename}.shortcut"
        # Sign on the system volume before copying to an external checkout.
        with tempfile.TemporaryDirectory(prefix="fuyaorime-shortcut-sign-") as directory:
            input_directory = Path(directory) / "source"
            input_directory.mkdir()
            signing_input = input_directory / destination.name
            signing_output = Path(directory) / destination.name
            signing_input.write_bytes(unsigned.read_bytes())
            subprocess.run(["/usr/bin/shortcuts", "sign", "--mode", "anyone", "--input", str(signing_input),
                            "--output", str(signing_output)], check=True)
            destination.write_bytes(signing_output.read_bytes())
        print(f"Shortcut: {destination}")


if __name__ == "__main__":
    main()
