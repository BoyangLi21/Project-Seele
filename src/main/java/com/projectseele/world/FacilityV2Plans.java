package com.projectseele.world;

/** Deterministic resolver for FacilitySchema v2 zone plans. */
public final class FacilityV2Plans
{
    private FacilityV2Plans() {}

    public static FacilityZonePlan resolve(
            FacilitySchemaV2.ResolvedManifest manifest, String zoneId)
    {
        return switch (zoneId)
        {
            case "TOKYO3_APRON" -> new Tokyo3ApronV2Plan(manifest);
            case "COMMAND_VOLUME" -> new CommandVolumeV2Plan(manifest);
            case "COMMAND_MODULE_CAP" ->
                    new CommandModuleCapV2Plan(manifest);
            case "H01_CV_CONNECTOR" ->
                    new H01CommandConnectorV2Plan(manifest);
            case "NERV_FOYER" -> new NervFoyerV2Plan(manifest);
            case "GEOFRONT_TRANSIT" ->
                    new GeoFrontTransitV2Plan(manifest);
            case "PUBLIC_LIFT_SHAFT" ->
                    new PublicLiftShaftV2Plan(manifest);
            case "SURFACE_TRANSIT" ->
                    new SurfaceTransitV2Plan(manifest);
            case "CMD_LIFT_SPINE" -> new CommandLiftSpineV2Plan(manifest);
            case "COMMAND_SUITE" -> new CommandSuiteV2Plan(manifest);
            case "STAFF_LIFT_SHAFT" ->
                    new StaffLiftShaftV2Plan(manifest);
            case "WEST_SERVICE_SPINE", "EAST_SERVICE_SPINE",
                    "STAFF_SERVICE_CONNECTOR" ->
                    new PyramidCirculationV2Plan(manifest, zoneId);
            case "WEST_SUPPORT" -> new WestSupportV2Plan(manifest);
            case "MAGI_CORE" -> new MagiCoreV2Plan(manifest);
            case "MAGI_DOGMA_SPINE" ->
                    new MagiDogmaSpineV2Plan(manifest);
            case "DOGMA_LIFT_SHAFT" ->
                    new DogmaLiftShaftV2Plan(manifest);
            case "DOGMA_SPINE" -> new DogmaSpineV2Plan(manifest);
            case "LILITH_CHAMBER" ->
                    new LilithChamberV2Plan(manifest);
            case "MECH_ACCESS_SPINE", "MECH_AIRLOCK_LINK",
                    "MECH_PERSONNEL_TRUNK", "MECH_OBS_LINK_00",
                    "MECH_OBS_LINK_01", "MECH_OBS_LINK_02" ->
                    new MechanicalAccessV2Plan(manifest, zoneId);
            case "UNIT00_CAGE", "UNIT01_CAGE", "UNIT02_CAGE" ->
                    new EvaCageV2Plan(manifest, zoneId);
            case "UNIT00_CARRIER", "UNIT00_SWITCHYARD",
                    "UNIT00_SILO", "UNIT00_SURFACE_HEAD",
                    "UNIT01_CARRIER", "UNIT01_SWITCHYARD",
                    "UNIT01_SILO", "UNIT01_SURFACE_HEAD",
                    "UNIT02_CARRIER", "UNIT02_SWITCHYARD",
                    "UNIT02_SILO", "UNIT02_SURFACE_HEAD" ->
                    new EvaLogisticsV2Plan(manifest, zoneId);
            default -> throw new IllegalArgumentException(
                    "No FacilitySchema v2 construction plan registered for "
                            + zoneId);
        };
    }
}
