from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise AssertionError(f"missing required file: {relative}")
    return path.read_text(encoding="utf-8")


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"{label}: missing {needle!r}")


def main() -> int:
    saved = read("src/main/java/com/projectseele/world/NervCrewSavedData.java")
    commands = read("src/main/java/com/projectseele/visual/NervCrewCommands.java")
    telemetry = read("src/main/java/com/projectseele/world/NervCommandTelemetry.java")
    docs = read("docs/MULTIPLAYER_OPERATIONS_TEST.md")

    gates: list[tuple[str, bool]] = []

    def gate(label: str, condition: bool) -> None:
        gates.append((label, condition))
        if not condition:
            raise AssertionError(label)

    require(saved, "extends SavedData", "persistent crew state")
    require(saved, 'DATA_NAME = "projectseele_nerv_crew"', "stable data key")
    require(saved, "DATA_VERSION = 1", "versioned crew schema")
    require(saved, "enum Station", "bounded station set")
    for station in ("COMMANDER", "OPERATIONS", "MAGI", "UNIT_00", "UNIT_01", "UNIT_02"):
        require(saved, station, f"station {station}")
    gate("crew assignments persist UUID, name and readiness",
         all(token in saved for token in ("putUUID", "putString", "putBoolean", "getBoolean")))
    gate("one-player assignment lookup exists",
         "stationFor(UUID playerId)" in saved)
    gate("occupied stations are rejected",
         "ClaimResult.OCCUPIED" in saved)

    require(commands, 'Commands.literal("nerv")', "public NERV command root")
    for command in ("claim", "ready", "standby", "release", "status", "audit"):
        require(commands, f'Commands.literal("{command}")', f"command {command}")
    gate("administrator clear is permission gated",
         'Commands.literal("clear")' in commands
         and ".requires(source -> source.hasPermission(2))" in commands)
    gate("runtime audit uses bounded map gate",
         "IntegratedNervMapBuilder.prepareRuntime(level)" in commands
         and "IntegratedNervMapBuilder.build(level)" not in commands)
    gate("status reports cockpit feed activity",
         "ServerboundEvaVideoFramePacket.isFeedActive" in commands)
    gate("command implementation is server safe",
         "net.minecraft.client" not in commands and "com.projectseele.client" not in commands)

    gate("strategic screen uses authoritative crew SavedData",
         "NervCrewSavedData.CrewOverview" in telemetry
         and ".get(level.getServer()).overview(level.getServer())" in telemetry
         and "CREW %d/6" in telemetry)
    gate("manual multiplayer acceptance procedure is documented",
         "/nerv crew claim unit01" in docs
         and "/nerv server audit" in docs
         and "不会重建" in docs)

    print("NERV multiplayer operations contract")
    for label, _ in gates:
        print(f"  PASS  {label}")
    print(f"PASS: {len(gates)}/{len(gates)} gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
