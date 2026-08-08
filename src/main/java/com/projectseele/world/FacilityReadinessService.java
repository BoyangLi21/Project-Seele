package com.projectseele.world;

import java.util.ArrayList;
import java.util.List;

import net.minecraft.server.level.ServerLevel;

/**
 * Read-only authority boundary between gameplay controls and facility
 * generation.
 *
 * <p>The current GeoFront is a retired visual prototype. Until the v2
 * FacilitySchema bootstrap receipt exists, every ordinary mechanism fails
 * closed here before it can inspect chunks, build rooms, repair geometry,
 * spawn logistics entities or mutate fleet SavedData.</p>
 */
public final class FacilityReadinessService
{
    public static final int TARGET_SCHEMA_VERSION =
            FacilitySchemaV2.SCHEMA_VERSION;
    public static final int NO_EPOCH = -1;

    private FacilityReadinessService() {}

    public static FacilityReadiness read(ServerLevel level, Operation operation,
                                         int variant)
    {
        if (FacilityWorldPolicy.isS20Rebuild(level.getServer()))
        {
            return readCompactS20(level, operation, variant);
        }
        if (!FacilityWorldPolicy.isCleanRebuild(level.getServer()))
        {
            return rejected(operation, variant,
                    FaultCode.LEGACY_PROTOTYPE_RETIRED,
                    List.of("facility-v2/bootstrap"),
                    "Legacy GeoFront controls are retired; use the dedicated "
                            + FacilityWorldPolicy.CLEAN_DIRECTORY + " save.");
        }

        FacilityV2SavedData facility = FacilityV2SavedData.get(level);
        if (!facility.commissioned())
        {
            return rejected(operation, variant,
                    FaultCode.FACILITY_RECEIPT_MISSING,
                    List.of("facility-v2/bootstrap"),
                    "FacilitySchema v" + TARGET_SCHEMA_VERSION
                            + " has not been commissioned.");
        }

        ArrayList<String> required = new ArrayList<>(switch (operation)
        {
            case NAVIGATE, ELEVATOR_CALL -> List.of(
                    "NERV_FOYER", "H01_CV_CONNECTOR",
                    "COMMAND_VOLUME", "STAFF_LIFT_SHAFT");
            case PREPARE, LAUNCH, RECOVERY, DUMMY_DISPATCH -> List.of(
                    "COMMAND_VOLUME", "COMMAND_MODULE_CAP",
                    "STAFF_LIFT_SHAFT", "STAFF_SERVICE_CONNECTOR");
            case BATTLE_START, BATTLE_ABORT -> List.of(
                    "TOKYO3_APRON", "SURFACE_TRANSIT",
                    "COMMAND_VOLUME", "COMMAND_MODULE_CAP");
        });
        if (variant >= 0 && variant <= 2
                && switch (operation)
                {
                    case PREPARE, LAUNCH, RECOVERY, DUMMY_DISPATCH -> true;
                    default -> false;
                })
        {
            String unit = String.format("%02d", variant);
            required.add("MECH_ACCESS_SPINE");
            required.add("MECH_AIRLOCK_LINK");
            required.add("MECH_PERSONNEL_TRUNK");
            required.add("MECH_OBS_LINK_" + unit);
            required.add("UNIT" + unit + "_CAGE");
            required.add("UNIT" + unit + "_CARRIER");
            required.add("UNIT" + unit + "_SWITCHYARD");
            required.add("UNIT" + unit + "_SILO");
            required.add("UNIT" + unit + "_SURFACE_HEAD");
        }
        ArrayList<String> missing = new ArrayList<>();
        for (String zone : required)
        {
            FacilityV2SavedData.ZoneRecord record;
            try
            {
                record = facility.requireZone(zone);
            }
            catch (IllegalArgumentException exception)
            {
                missing.add(zone + ":MISSING");
                continue;
            }
            if (record.state() != FacilityV2SavedData.ZoneState.COMPLETE)
            {
                missing.add(zone + ":" + record.state());
            }
        }
        if (!missing.isEmpty())
        {
            return rejected(operation, variant,
                    FaultCode.FACILITY_RECEIPT_INCOMPLETE, missing,
                    "Required facility route is still being constructed.");
        }

        if (variant >= 0 && variant <= 2
                && switch (operation)
                {
                    case PREPARE, LAUNCH, RECOVERY, DUMMY_DISPATCH -> true;
                    default -> false;
                })
        {
            EvaFleetSavedData.FleetEntry entry =
                    EvaFleetSavedData.get(level.getServer())
                            .entry(variant).orElse(null);
            if (entry == null)
            {
                return rejected(operation, variant,
                        FaultCode.FLEET_ENTRY_MISSING,
                        List.of("eva-0" + variant + "/fleet"),
                        "The assigned EVA has no canonical fleet receipt.");
            }
            if (EvaLogisticsDirector.canonicalUnit(level, variant) == null)
            {
                return rejected(operation, variant,
                        FaultCode.CANONICAL_ENTITY_NOT_LOADED,
                        List.of("eva-0" + variant + "/entity"),
                        "The assigned canonical EVA is not loaded.");
            }
        }

        return new FacilityReadiness(true, TARGET_SCHEMA_VERSION,
                FacilitySchemaV2.EPOCH, operation, variant,
                FaultCode.NONE, List.of(),
                "Facility route and command authority ready.");
    }

    private static FacilityReadiness readCompactS20(
            ServerLevel level, Operation operation, int variant)
    {
        boolean needsEva = variant >= 0 && variant <= 2
                && switch (operation)
                {
                    case PREPARE, LAUNCH, RECOVERY, DUMMY_DISPATCH -> true;
                    default -> false;
                };
        if (needsEva)
        {
            EvaFleetSavedData.FleetEntry entry =
                    EvaFleetSavedData.get(level.getServer())
                            .entry(variant).orElse(null);
            if (entry == null)
            {
                return rejected(operation, variant,
                        FaultCode.FLEET_ENTRY_MISSING,
                        List.of("s20/eva-0" + variant + "/fleet"),
                        "The S20 compact cage has no canonical EVA receipt.");
            }
            if (EvaLogisticsDirector.canonicalUnit(level, variant) == null)
            {
                return rejected(operation, variant,
                        FaultCode.CANONICAL_ENTITY_NOT_LOADED,
                        List.of("s20/eva-0" + variant + "/entity"),
                        "The S20 compact-cage EVA is not loaded.");
            }
        }
        return new FacilityReadiness(true, TARGET_SCHEMA_VERSION,
                NO_EPOCH, operation, variant, FaultCode.NONE, List.of(),
                "S20 authored command and compact EVA plant ready.");
    }

    private static FacilityReadiness rejected(
            Operation operation, int variant, FaultCode fault,
            List<String> missing, String message)
    {
        return new FacilityReadiness(false, TARGET_SCHEMA_VERSION,
                NO_EPOCH, operation, variant, fault, missing, message);
    }

    public enum Operation
    {
        NAVIGATE,
        ELEVATOR_CALL,
        PREPARE,
        LAUNCH,
        RECOVERY,
        DUMMY_DISPATCH,
        BATTLE_START,
        BATTLE_ABORT
    }

    public enum FaultCode
    {
        NONE,
        RESCUE_MODE_INHIBIT,
        LEGACY_PROTOTYPE_RETIRED,
        FACILITY_RECEIPT_MISSING,
        FACILITY_RECEIPT_INCOMPLETE,
        ROUTE_RECEIPT_MISSING,
        FLEET_ENTRY_MISSING,
        CANONICAL_ENTITY_NOT_LOADED,
        DESTINATION_CHUNK_NOT_LOADED
    }

    public record FacilityReadiness(boolean accepted, int schemaVersion,
                                    int epoch, Operation operation, int variant,
                                    FaultCode faultCode,
                                    List<String> missingReceiptIds,
                                    String message)
    {
        public FacilityReadiness
        {
            missingReceiptIds = List.copyOf(missingReceiptIds);
        }
    }
}
