"""Check native text parameter encoding and the generated download data flow."""

import importlib.util
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ios_shortcut", ROOT / "updater/build_ios_shortcut.py")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)
LATEST = BUILDER.REPOSITORY + "/releases/tag/v20261004"
PACKAGE = BUILDER.REPOSITORY + "/releases/download/v20261004/fuyaorime-20261004.zip"


class IosShortcutTests(unittest.TestCase):
    def setUp(self):
        self.workflow = BUILDER.build_workflow()

    def download_address(self, proxy, latest=LATEST):
        values = {}
        branches = []

        def render(value):
            if isinstance(value, str):
                return value
            if value.get("WFSerializationType") == "WFTextTokenAttachment":
                return values[value["Value"]["OutputUUID"]]
            self.assertEqual(value.get("WFSerializationType"), "WFTextTokenString")
            contents = value["Value"]
            encoded = contents["string"].encode("utf-16-le")
            attachments = contents.get("attachmentsByRange", {})
            for position, reference in sorted(attachments.items(), key=lambda x: int(re.search(r"\d+", x[0])[0]), reverse=True):
                offset = int(re.search(r"\d+", position)[0]) * 2
                replacement = values[reference["OutputUUID"]]
                if isinstance(replacement, list):
                    replacement = "\n".join(replacement)
                encoded = encoded[:offset] + replacement.encode("utf-16-le") + encoded[offset + 2:]
            return encoded.decode("utf-16-le")

        for action in self.workflow["WFWorkflowActions"]:
            kind = action["WFWorkflowActionIdentifier"].removeprefix("is.workflow.actions.")
            params = action["WFWorkflowActionParameters"]
            action_id = params["UUID"]
            if kind == "conditional":
                mode = params["WFControlFlowMode"]
                if mode == 0:
                    has_value = bool(render(params["WFInput"]["Variable"]))
                    branches.append(has_value if params["WFCondition"] == 100 else not has_value)
                elif mode == 2:
                    branches.pop()
                else:
                    self.fail("The integrated shortcut should not need Otherwise branches")
                continue
            if branches and not all(branches):
                continue
            if kind in ("comment", "file", "alert"):
                continue
            if kind == "exit":
                return None
            if kind == "gettext":
                values[action_id] = proxy if action_id == BUILDER.identifier("proxy") else render(params["WFTextActionText"])
            elif kind == "text.replace":
                # This slot requires text serialization, not an attachment envelope.
                self.assertEqual(params["WFInput"]["WFSerializationType"], "WFTextTokenString")
                replacement = re.sub(r"\$(\d+)", r"\\g<\1>", render(params["WFReplaceTextReplace"]))
                values[action_id] = re.sub(render(params["WFReplaceTextFind"]), replacement, render(params["WFInput"]))
            elif kind == "url.expand":
                values[action_id] = latest
            elif kind == "text.match":
                values[action_id] = re.findall(params["WFMatchTextPattern"], render(params["text"]))
            elif kind == "url":
                values[action_id] = render(params["WFURLActionURL"])
            elif kind == "downloadurl":
                return render(params["WFURL"])
            else:
                self.fail(f"Unexpected action before download: {kind}")
        self.fail("No download action reached")

    def test_text_replace_uses_native_text_envelope(self):
        for action in self.workflow["WFWorkflowActions"]:
            if action["WFWorkflowActionIdentifier"] == "is.workflow.actions.text.replace":
                self.assertEqual(action["WFWorkflowActionParameters"]["WFInput"]["WFSerializationType"],
                                 "WFTextTokenString")

    def test_proxy_is_used_by_the_download_action(self):
        for prefix in ("https://proxy.example", "https://proxy.example/", "https://proxy.example///", " https://proxy.example/ "):
            with self.subTest(prefix=prefix):
                self.assertEqual(self.download_address(prefix), "https://proxy.example/" + PACKAGE)

    def test_custom_proxy_path_and_direct_mode(self):
        self.assertEqual(self.download_address("https://proxy.example/forward/"), "https://proxy.example/forward/" + PACKAGE)
        self.assertEqual(self.download_address(""), PACKAGE)
        self.assertEqual(self.download_address("  "), PACKAGE)

    def test_invalid_release_stops_before_download(self):
        self.assertIsNone(self.download_address("https://proxy.example", BUILDER.REPOSITORY + "/releases/latest"))
        self.assertIsNone(self.download_address("", "https://github.com/other/repo/releases/tag/v20261004"))

    def test_no_otherwise_or_if_result_wiring(self):
        for action in self.workflow["WFWorkflowActions"]:
            params = action["WFWorkflowActionParameters"]
            self.assertNotEqual(params.get("WFControlFlowMode"), 1)
            self.assertNotIn("If Result", repr(params))

    def test_user_data_protection_remains_before_save(self):
        by_id = {a["WFWorkflowActionParameters"]["UUID"]: a for a in self.workflow["WFWorkflowActions"]}
        pattern = by_id[BUILDER.identifier("protected-item")]["WFWorkflowActionParameters"]["WFMatchTextPattern"]
        guard = by_id[BUILDER.identifier("writable-item")]["WFWorkflowActionParameters"]
        self.assertEqual(guard["WFCondition"], 101)
        self.assertEqual(guard["WFInput"]["Variable"]["Value"]["OutputUUID"], BUILDER.identifier("protected-item"))
        for name in ("installation.yaml", "INSTALLATION.YAML", "rime_ice.userdb", "userdb"):
            self.assertIsNotNone(re.fullmatch(pattern, name, re.I), name)
        for name in ("rime_ice.schema.yaml", "cn_dicts", "lua"):
            self.assertIsNone(re.fullmatch(pattern, name, re.I), name)
        actions = self.workflow["WFWorkflowActions"]
        indexes = {a["WFWorkflowActionParameters"]["UUID"]: i for i, a in enumerate(actions)}
        self.assertLess(indexes[BUILDER.identifier("writable-item")], indexes[BUILDER.identifier("install")])
        self.assertLess(indexes[BUILDER.identifier("install")], indexes[BUILDER.identifier("protected-end")])


if __name__ == "__main__":
    unittest.main()
