package com.projectseele.client.render;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

import com.projectseele.ProjectSeele;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;

/** Runtime identity and fail-closed contract for the local high-detail models. */
public final class LocalVisualAssetFingerprint
{
    private static final Map<String, MeshContract> CONTRACTS = Map.of(
            "eva_unit00", new MeshContract(5_510, 43, true),
            "eva_unit01", new MeshContract(6_044, 43, true),
            "eva_unit02", new MeshContract(5_770, 43, true),
            "mass_production_eva", new MeshContract(4_901, 15, false));
    private static final Map<String, Fingerprint> CACHE = new ConcurrentHashMap<>();

    private LocalVisualAssetFingerprint() {}

    public static Fingerprint inspect(String assetName)
    {
        return CACHE.computeIfAbsent(assetName, LocalVisualAssetFingerprint::load);
    }

    public static boolean isStrictMode()
    {
        return Boolean.getBoolean("projectseele.visualCapture")
                || Boolean.getBoolean("projectseele.strictHighDetail");
    }

    public static void clearCache()
    {
        CACHE.clear();
    }

    private static Fingerprint load(String assetName)
    {
        Map<String, ResourceDigest> resources = new LinkedHashMap<>();
        ResourceLocation mesh = resource("mesh/" + assetName + ".mesh.json");
        resources.put("mesh", digest(mesh));
        resources.put("geo", digest(resource("geo/" + assetName + ".geo.json")));
        resources.put("animation", digest(resource(
                "animations/" + assetName + ".animation.json")));
        resources.put("texture", digest(resource(
                "textures/entity/" + assetName + ".png")));

        boolean complete = resources.values().stream().allMatch(ResourceDigest::present);
        String sourcePack = complete ? resources.values().iterator().next().sourcePack() : "missing";
        boolean sameSource = complete && resources.values().stream()
                .allMatch(resource -> sourcePack.equals(resource.sourcePack()));
        String meshTag = LocalTriangleMeshLayer.captureTag(mesh);
        MeshContract contract = CONTRACTS.get(assetName);
        boolean meshMatches = contract != null
                && contract.matches(meshTag, mesh);
        boolean valid = complete && sameSource && meshMatches;
        String reason = !complete ? "missing-resource"
                : !sameSource ? "mixed-resource-packs"
                : contract == null ? "unknown-mesh-contract"
                : !meshMatches ? "wrong-mesh-contract" : "ok";
        Fingerprint fingerprint = new Fingerprint(assetName, Map.copyOf(resources), meshTag,
                sourcePack, valid, reason);
        ProjectSeele.LOGGER.info("Local visual asset fingerprint: {}", fingerprint.description());
        return fingerprint;
    }

    private static ResourceLocation resource(String path)
    {
        return new ResourceLocation(ProjectSeele.MODID, path);
    }

    private static ResourceDigest digest(ResourceLocation location)
    {
        Optional<Resource> resource = Minecraft.getInstance().getResourceManager()
                .getResource(location);
        if (resource.isEmpty())
        {
            return new ResourceDigest(false, "missing", "missing");
        }
        try (var stream = resource.get().open())
        {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return new ResourceDigest(true, resource.get().sourcePackId(),
                    HexFormat.of().formatHex(digest.digest(stream.readAllBytes())));
        }
        catch (Exception exception)
        {
            ProjectSeele.LOGGER.error("Failed to fingerprint local visual resource " + location,
                    exception);
            return new ResourceDigest(false, "unreadable", "unreadable");
        }
    }

    private static String shortHash(String value)
    {
        if (value.length() >= 8 && value.chars().allMatch(character ->
                Character.digit(character, 16) >= 0))
        {
            return value.substring(0, 8);
        }
        try
        {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(
                    value.getBytes(StandardCharsets.UTF_8))).substring(0, 8);
        }
        catch (Exception exception)
        {
            return "00000000";
        }
    }

    private record MeshContract(int triangles, int parts,
                                boolean nativeThumbs)
    {
        private boolean matches(String meshTag, ResourceLocation mesh)
        {
            if (!meshTag.startsWith("triangle-mesh-" + triangles
                    + "-p" + parts + "-"))
            {
                return false;
            }
            if (!nativeThumbs)
            {
                return true;
            }
            for (String side : new String[] {"l", "r"})
            {
                // SmOd already supplies the visible thumb as one authored
                // mesh.  The other four digits use the generated articulated
                // three-segment chains.  Requiring this exact split prevents
                // both the former doubled/overlong thumb and a silently
                // missing finger chain from passing strict mode.
                if (!LocalTriangleMeshLayer.hasPart(
                        mesh, "finger_thumb_" + side)
                        || LocalTriangleMeshLayer.hasPart(
                        mesh, "finger_thumb_distal_" + side)
                        || LocalTriangleMeshLayer.hasPart(
                        mesh, "finger_thumb_tip_" + side))
                {
                    return false;
                }
                for (String digit : new String[] {
                        "index", "middle", "ring", "little"})
                {
                    if (!LocalTriangleMeshLayer.hasPart(
                            mesh, "finger_" + digit + "_" + side)
                            || !LocalTriangleMeshLayer.hasPart(mesh,
                            "finger_" + digit + "_distal_" + side)
                            || !LocalTriangleMeshLayer.hasPart(mesh,
                            "finger_" + digit + "_tip_" + side))
                    {
                        return false;
                    }
                }
            }
            return true;
        }
    }

    public record ResourceDigest(boolean present, String sourcePack, String sha256) {}

    public record Fingerprint(String assetName, Map<String, ResourceDigest> resources,
                              String meshTag, String sourcePack, boolean valid, String reason)
    {
        public String compactTag()
        {
            return assetName + "-" + meshTag
                    + "-g" + shortHash(resources.get("geo").sha256())
                    + "-a" + shortHash(resources.get("animation").sha256())
                    + "-t" + shortHash(resources.get("texture").sha256())
                    + "-s" + shortHash(sourcePack);
        }

        public String description()
        {
            return compactTag() + " valid=" + valid + " reason=" + reason
                    + " source=" + sourcePack
                    + " meshSha256=" + resources.get("mesh").sha256()
                    + " geoSha256=" + resources.get("geo").sha256()
                    + " animationSha256=" + resources.get("animation").sha256()
                    + " textureSha256=" + resources.get("texture").sha256();
        }
    }
}
