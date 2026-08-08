package com.projectseele.world;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Comparator;
import java.util.HexFormat;

import net.minecraft.resources.ResourceLocation;

/** Canonical SHA-256 helpers used by FacilitySchema v2 receipts. */
public final class FacilityV2Hashing
{
    private FacilityV2Hashing() {}

    public static String manifestContractHash(
            FacilitySchemaV2.ResolvedManifest manifest,
            ResourceLocation dimension, long worldSeed)
    {
        return hash(output ->
        {
            writeLong(output, FacilitySchemaV2.SCHEMA_VERSION);
            writeLong(output, FacilitySchemaV2.COORDINATE_CONTRACT_VERSION);
            writeString(output, dimension.toString());
            writeString(output, FacilitySchemaV2.REGION_ID);
            writeBox(output, manifest.region());
            writeLong(output, manifest.candidateIndex());
            writeLong(output, manifest.surfaceY());
            writeLong(output, worldSeed);
            writeString(output, FacilitySchemaV2.GENERATOR_VERSION);

            var zones = manifest.zones().stream()
                    .sorted(Comparator.comparing(FacilitySchemaV2.ZoneSpec::id))
                    .toList();
            writeLong(output, zones.size());
            for (FacilitySchemaV2.ZoneSpec zone : zones)
            {
                writeString(output, zone.id());
                writeBox(output, zone.owner());
            }

            var ports = manifest.ports().stream()
                    .sorted(Comparator.comparing(FacilitySchemaV2.PortSpec::key))
                    .toList();
            writeLong(output, ports.size());
            for (FacilitySchemaV2.PortSpec port : ports)
            {
                writeString(output, port.key());
                writeLong(output, port.position().getX());
                writeLong(output, port.position().getY());
                writeLong(output, port.position().getZ());
                writeString(output, port.facing().getName());
                writeString(output, port.type());
                writeString(output, port.clearProfile());
                writeBox(output, port.aperture());
                writeString(output, port.peerKey());
            }
        });
    }

    public static String buildPlanHash(String zoneId, String stage,
                                       String planVersion,
                                       FacilitySchemaV2.IntBox owner)
    {
        return hash(output ->
        {
            writeString(output, zoneId);
            writeString(output, stage);
            writeString(output, planVersion);
            writeString(output, FacilitySchemaV2.GENERATOR_VERSION);
            writeBox(output, owner);
        });
    }

    public static String bootstrapRegionCoreHash(
            String manifestContractHash, int minimumHeight,
            int maximumHeight, int p10, int median, int p90,
            int oceanSamples, int largestLandCluster,
            int criticalMinimumHeight, int criticalMaximumHeight)
    {
        return hash(output ->
        {
            writeString(output, manifestContractHash);
            writeLong(output, minimumHeight);
            writeLong(output, maximumHeight);
            writeLong(output, p10);
            writeLong(output, median);
            writeLong(output, p90);
            writeLong(output, oceanSamples);
            writeLong(output, largestLandCluster);
            writeLong(output, criticalMinimumHeight);
            writeLong(output, criticalMaximumHeight);
            writeString(output, "MOTION_BLOCKING_NO_LEAVES");
            writeString(output, "OCEAN_FLOOR_WG");
            writeString(output, "CLIENT_ONLY");
            writeString(output, "roof-solid-below-y64-no-carvers-no-aquifers");
        });
    }

    public static String fabricFeatureHash(String featureId,
                                           String featureRevision,
                                           int priority,
                                           long authoredWork)
    {
        return hash(output ->
        {
            writeString(output, "GeoFrontFabric");
            writeLong(output, GeoFrontFabricPlan.FORMAT_VERSION);
            writeLong(output, GeoFrontFabricPlan.FABRIC_REVISION);
            writeString(output, featureId);
            writeString(output, featureRevision);
            writeLong(output, priority);
            writeLong(output, authoredWork);
            writeString(output, FacilitySchemaV2.GENERATOR_VERSION);
        });
    }

    public static String fabricPlanHash(String regionCoreHash,
                                        Iterable<GeoFrontFabricPlan.Feature>
                                                features)
    {
        return hash(output ->
        {
            writeString(output, "GeoFrontFabricPlan");
            writeLong(output, GeoFrontFabricPlan.FORMAT_VERSION);
            writeLong(output, GeoFrontFabricPlan.FABRIC_REVISION);
            writeString(output, FacilitySchemaV2.REGION_ID);
            writeLong(output, FacilitySchemaV2.EPOCH);
            writeString(output, regionCoreHash);
            for (GeoFrontFabricPlan.Feature feature : features)
            {
                writeString(output, feature.id());
                writeString(output, feature.contractHash());
            }
        });
    }

    public static String fabricOwnerMaskHash(
            FacilitySchemaV2.ResolvedManifest manifest, int inflation)
    {
        return hash(output ->
        {
            writeString(output, "GeoFrontFabricOwnerMask");
            writeLong(output, inflation);
            var zones = manifest.zones().stream()
                    .sorted(Comparator.comparing(FacilitySchemaV2.ZoneSpec::id))
                    .toList();
            for (FacilitySchemaV2.ZoneSpec zone : zones)
            {
                writeString(output, zone.id());
                FacilitySchemaV2.IntBox owner = zone.owner();
                writeLong(output, owner.minX() - inflation);
                writeLong(output, owner.minY() - inflation);
                writeLong(output, owner.minZ() - inflation);
                writeLong(output, owner.maxX() + inflation);
                writeLong(output, owner.maxY() + inflation);
                writeLong(output, owner.maxZ() + inflation);
            }
        });
    }

    private static String hash(Writer writer)
    {
        try
        {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (DataOutputStream output = new DataOutputStream(bytes))
            {
                writer.write(output);
            }
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(bytes.toByteArray()));
        }
        catch (IOException exception)
        {
            throw new IllegalStateException(
                    "Unable to serialize FacilitySchema v2 hash input",
                    exception);
        }
        catch (NoSuchAlgorithmException exception)
        {
            throw new IllegalStateException("SHA-256 is unavailable",
                    exception);
        }
    }

    private static void writeLong(DataOutputStream output, long value)
            throws IOException
    {
        output.writeLong(value);
    }

    private static void writeString(DataOutputStream output, String value)
            throws IOException
    {
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        output.writeInt(bytes.length);
        output.write(bytes);
    }

    private static void writeBox(DataOutputStream output,
                                 FacilitySchemaV2.IntBox box)
            throws IOException
    {
        writeLong(output, box.minX());
        writeLong(output, box.minY());
        writeLong(output, box.minZ());
        writeLong(output, box.maxX());
        writeLong(output, box.maxY());
        writeLong(output, box.maxZ());
    }

    @FunctionalInterface
    private interface Writer
    {
        void write(DataOutputStream output) throws IOException;
    }
}
