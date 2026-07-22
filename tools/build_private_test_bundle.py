#!/usr/bin/env python3
"""Build a local-only Project SEELE multiplayer test bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK_NAME = "Project_SEELE_Private_Test_Pack"
DEFAULT_OUTPUT = ROOT / "external-assets" / "private-test-bundle"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def newest_project_jar() -> Path:
    jars = [
        path
        for path in (ROOT / "build" / "libs").glob("projectseele-*.jar")
        if not path.name.endswith(("-sources.jar", "-javadoc.jar"))
    ]
    if not jars:
        raise FileNotFoundError("Run gradlew.bat build before creating the private bundle")
    return max(jars, key=lambda path: path.stat().st_mtime_ns)


def find_geckolib() -> Path:
    cache = (
        Path.home()
        / ".gradle"
        / "caches"
        / "modules-2"
        / "files-2.1"
        / "software.bernie.geckolib"
        / "geckolib-forge-1.20.1"
    )
    candidates = [
        path
        for path in cache.glob("4.8*/**/*.jar")
        if not path.name.endswith(("-sources.jar", "-javadoc.jar"))
    ]
    if not candidates:
        raise FileNotFoundError(
            "GeckoLib 4.8.x was not found in the Gradle cache; run a Project SEELE build first"
        )
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source: Path, destination: Path, *, world: bool = False) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"Required directory is missing: {source}")
    ignored = None
    if world:
        ignored = shutil.ignore_patterns(
            "session.lock", "*.lock", "*.log", "logs", "screenshots", "crash-reports"
        )
    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignored)


def write_install_note(destination: Path, includes_world: bool) -> None:
    world_line = (
        "此包包含 SEELE_TOKYO3_REBUILT；单人可直接进入，专用服务器请把 level-name 设为 SEELE_TOKYO3_REBUILT。"
        if includes_world
        else "此包不包含世界存档；主机需要另行私传 SEELE_TOKYO3_REBUILT。"
    )
    note = f"""Project SEELE 私有测试包
生成时间：{datetime.now(timezone.utc).isoformat()}
{world_line}

1. 使用 Minecraft 1.20.1、Forge 47.4.10 和 Java 17。
2. 将 minecraft 目录中的内容合并到一个独立游戏实例的根目录。
3. 客户端建议分配 6G 内存；启用 eva_real_model 资源包并将它置于最高优先级。
4. 专用服务器建议分配 8G 内存；资源包只需要安装在客户端。
5. 进入世界后先运行 /seele geofront audit；如提示结构不完整，再运行 /seele geofront setup。
6. 驾驶员可用 /seele pilot sync 查看同步率；管理员可用 /seele pilot sync set <0..100> 调试。
7. 仅限朋友之间本地/私服测试，禁止公开上传或再次分发第三方素材。
8. 专用服务器直接使用包内 server-template；它带 8G 参数、白名单和人工 EULA 门禁。
9. 完整说明见仓库 docs/FRIEND_TEST_PACK.md。
"""
    note += (
        "\nNERV multiplayer commands: /nerv crew status, "
        "/nerv crew claim <station>, /nerv crew ready, "
        "/nerv server status. Operators should run /nerv server audit "
        "before a sortie.\n"
    )
    destination.write_text(note, encoding="utf-8")

def write_server_template(pack_root: Path, includes_world: bool) -> None:
    template = pack_root / "server-template"
    template.mkdir(parents=True, exist_ok=True)

    properties = """# Project SEELE private 1-4 player server
server-port=25565
motd=Project SEELE Private Test
level-name=SEELE_TOKYO3_REBUILT
gamemode=survival
difficulty=normal
hardcore=false
max-players=4
white-list=true
enforce-whitelist=true
online-mode=true
spawn-protection=0
allow-flight=true
view-distance=8
simulation-distance=6
entity-broadcast-range-percentage=150
network-compression-threshold=256
max-tick-time=120000
sync-chunk-writes=false
enable-command-block=false
"""
    (template / "server.properties").write_text(properties, encoding="utf-8")

    jvm_args = """-Xms2G
-Xmx8G
-XX:+UseG1GC
-XX:MaxGCPauseMillis=100
-XX:+ParallelRefProcEnabled
-Dfile.encoding=UTF-8
"""
    (template / "user_jvm_args.txt").write_text(jvm_args, encoding="utf-8")

    world_copy = (
        'if exist "%PACK_ROOT%\\minecraft\\saves\\SEELE_TOKYO3_REBUILT\\level.dat" '
        'xcopy /E /I /Y "%PACK_ROOT%\\minecraft\\saves\\SEELE_TOKYO3_REBUILT" '
        '"SEELE_TOKYO3_REBUILT" >nul\n'
        if includes_world
        else ""
    )
    sync = f"""@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PACK_ROOT=%~dp0.."
if not exist "%PACK_ROOT%\\minecraft\\mods" (
    echo Private pack minecraft folder was not found.
    pause
    exit /b 1
)
if not exist "mods" mkdir "mods"
if not exist "config" mkdir "config"
if not exist "projectseele-local-maps" mkdir "projectseele-local-maps"
copy /Y "%PACK_ROOT%\\minecraft\\mods\\*.jar" "mods\\" >nul
xcopy /E /I /Y "%PACK_ROOT%\\minecraft\\config" "config" >nul
xcopy /E /I /Y "%PACK_ROOT%\\minecraft\\projectseele-local-maps" "projectseele-local-maps" >nul
{world_copy}echo Project SEELE server files synchronized.
echo Install Forge 1.20.1-47.4.10 server files in this folder before start-server.bat.
pause
"""
    (template / "sync-from-private-pack.bat").write_text(sync, encoding="utf-8")

    start = """@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "run.bat" (
    echo Forge server run.bat was not found.
    echo Install Forge 1.20.1-47.4.10 server into this folder first.
    pause
    exit /b 1
)
if not exist "eula.txt" (
    call run.bat --nogui
    echo.
    echo Read https://aka.ms/MinecraftEULA and edit eula.txt yourself.
    pause
    exit /b 1
)
findstr /I /C:"eula=true" "eula.txt" >nul
if errorlevel 1 (
    echo Mojang EULA has not been accepted. Edit eula.txt yourself after reading it.
    pause
    exit /b 1
)
call run.bat --nogui
"""
    (template / "start-server.bat").write_text(start, encoding="utf-8")

    world_note = (
        "模板会从同一私测包复制 SEELE_TOKYO3_REBUILT 世界。"
        if includes_world
        else "此包没有世界存档；请由主机私下复制 SEELE_TOKYO3_REBUILT。"
    )
    note = f"""Project SEELE 私人专用服务器模板
{world_note}

1. 在 server-template 内安装 Forge 1.20.1-47.4.10 服务端，不要安装客户端资源包。
2. 运行 sync-from-private-pack.bat，同步相同版本的模组、配置、本机地图缓存和世界。
3. 首次运行 start-server.bat 只会生成 eula.txt；服务器所有者必须亲自阅读 Mojang EULA 后决定是否改为 eula=true。
4. 在服务器控制台执行 whitelist add <正版玩家名>，再重新启动。模板默认开启正版验证和强制白名单。
5. 首位管理员进入后执行 /seele geofront audit，要求 valid=true、mapVersion=17、三井均为 3/3。
6. 客户端仍需安装私测包 minecraft/ 内容，并启用 eva_real_model 资源包。
7. 默认 JVM 为 2G 起步、8G 上限；如果物理内存不足 12G，请不要同时在主机上启动高精度客户端。
8. server-template 与整个私测包都不得公开上传。
"""
    note += (
        "\nAfter login: claim roles with /nerv crew claim <station>, "
        "then run /nerv server status and the operator-only "
        "/nerv server audit. The audit is bounded and never rebuilds the map.\n"
    )
    (template / "README-服务器部署.txt").write_text(note, encoding="utf-8")

def make_manifest(pack_root: Path, includes_world: bool) -> None:
    files = []
    for path in sorted(pack_root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        files.append(
            {
                "path": path.relative_to(pack_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "schema": 1,
        "privateLocalTestOnly": True,
        "includesWorld": includes_world,
        "minecraft": "1.20.1",
        "forge": "47.4.10",
        "java": 17,
        "files": files,
    }
    (pack_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def create_zip(pack_root: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(pack_root.rglob("*")):
            if path.is_file():
                archive.write(path, (Path(PACK_NAME) / path.relative_to(pack_root)).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-world", action="store_true", help="include SEELE_TOKYO3_REBUILT")
    parser.add_argument("--no-zip", action="store_true", help="leave only the unpacked directory")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output = args.output.resolve()
    pack_root = output / PACK_NAME
    if pack_root.exists():
        shutil.rmtree(pack_root)
    minecraft = pack_root / "minecraft"
    mods = minecraft / "mods"

    project_jar = newest_project_jar()
    geckolib = find_geckolib()
    copy_file(project_jar, mods / project_jar.name)
    copy_file(geckolib, mods / geckolib.name)

    local_mods = ROOT / ".Codex" / "local-mods"
    ars = local_mods / "ars-nouveau-4.12.7.jar"
    curios = local_mods / "curios-forge-1.20.1-5.14.1.jar"
    if ars.is_file():
        if not curios.is_file():
            raise FileNotFoundError("Ars Nouveau is present but its Curios dependency is missing")
        copy_file(ars, mods / ars.name)
        copy_file(curios, mods / curios.name)

    copy_tree(
        ROOT / "run" / "resourcepacks" / "eva_real_model",
        minecraft / "resourcepacks" / "eva_real_model",
    )
    copy_tree(
        ROOT / "run" / "projectseele-local-maps",
        minecraft / "projectseele-local-maps",
    )

    config = ROOT / "run" / "config"
    if config.is_dir():
        for name in ("projectseele-common.toml", "projectseele-client.toml"):
            source = config / name
            if source.is_file():
                copy_file(source, minecraft / "config" / name)

    if args.include_world:
        copy_tree(
            ROOT / "run" / "saves" / "SEELE_TOKYO3_REBUILT",
            minecraft / "saves" / "SEELE_TOKYO3_REBUILT",
            world=True,
        )

    write_install_note(pack_root / "README-安装说明.txt", args.include_world)
    write_server_template(pack_root, args.include_world)
    make_manifest(pack_root, args.include_world)

    zip_path = output / f"{PACK_NAME}.zip"
    if not args.no_zip:
        output.mkdir(parents=True, exist_ok=True)
        create_zip(pack_root, zip_path)

    file_count = sum(1 for path in pack_root.rglob("*") if path.is_file())
    print(f"[PASS] private test bundle: {pack_root}")
    print(f"[PASS] files={file_count} includesWorld={args.include_world}")
    if not args.no_zip:
        print(f"[PASS] zip={zip_path} bytes={zip_path.stat().st_size}")
    print("[INFO] local/private testing only; do not publish this bundle")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        raise SystemExit(1)