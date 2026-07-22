#!/usr/bin/env python3
"""Validate the local-only dedicated server template and generated pack."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "external-assets/private-test-bundle/Project_SEELE_Private_Test_Pack"


def gate(label: str, condition: bool, detail: str) -> bool:
    if condition:
        print(f"[PASS] {label}")
        return True
    print(f"[FAIL] {label}: {detail}")
    return False


def main() -> int:
    builder = (ROOT / "tools/build_private_test_bundle.py").read_text(encoding="utf-8")
    docs = (ROOT / "docs/FRIEND_TEST_PACK.md").read_text(encoding="utf-8")
    results = [
        gate(
            "template.builder",
            "def write_server_template" in builder
            and "write_server_template(pack_root, args.include_world)" in builder,
            "bundle builder does not emit the server template",
        ),
        gate(
            "template.memory",
            "-Xms2G" in builder and "-Xmx8G" in builder
            and "UseG1GC" in builder,
            "2G/8G G1 server JVM policy is missing",
        ),
        gate(
            "template.performance",
            "view-distance=8" in builder
            and "simulation-distance=6" in builder
            and "sync-chunk-writes=false" in builder
            and "max-tick-time=120000" in builder,
            "private server performance profile is incomplete",
        ),
        gate(
            "template.eva_network",
            "allow-flight=true" in builder
            and "entity-broadcast-range-percentage=150" in builder,
            "giant EVA movement or tracking server settings are missing",
        ),
        gate(
            "template.security",
            "online-mode=true" in builder
            and "white-list=true" in builder
            and "enforce-whitelist=true" in builder,
            "private server is not fail-closed behind authentication and whitelist",
        ),
        gate(
            "template.eula_human_gate",
            "https://aka.ms/MinecraftEULA" in builder
            and '(template / "eula.txt").write_text' not in builder
            and "echo eula=true" not in builder,
            "template accepts or writes the Mojang EULA automatically",
        ),
        gate(
            "template.same_world",
            "level-name=SEELE_TOKYO3_REBUILT" in builder
            and "projectseele-local-maps" in builder
            and "sync-from-private-pack.bat" in builder,
            "server does not copy the same connected world/maps/config",
        ),
        gate(
            "template.documentation",
            "server-template/" in docs
            and "whitelist add" in docs
            and "mapVersion=17" in docs
            and "allow-flight=true" in docs,
            "deployment, whitelist, schema or EVA-flight instructions are missing",
        ),
    ]

    if PACK.is_dir():
        template = PACK / "server-template"
        required = (
            "server.properties",
            "user_jvm_args.txt",
            "sync-from-private-pack.bat",
            "start-server.bat",
            "README-服务器部署.txt",
        )
        results.append(gate(
            "generated.files",
            all((template / name).is_file() for name in required),
            "generated private pack is stale or missing server-template files",
        ))
        try:
            manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
            paths = {entry["path"] for entry in manifest["files"]}
            forbidden = [
                path for path in paths
                if path.startswith("external-assets/incoming/")
                or path.startswith("third_party/")
                or path.endswith((".rar", ".blend", ".bbmodel"))
            ]
            manifest_ok = all(f"server-template/{name}" in paths for name in required)
            manifest_ok = manifest_ok and not forbidden
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            manifest_ok = False
        results.append(gate(
            "generated.manifest_private_scope",
            manifest_ok,
            "server template is absent from manifest or forbidden source assets leaked",
        ))

    print(f"\nPrivate server template: {sum(results)}/{len(results)} gates passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())