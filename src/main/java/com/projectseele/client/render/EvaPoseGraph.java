package com.projectseele.client.render;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;

/**
 * Phase-A observer for the eventual single EVA pose authority.
 *
 * <p>This class deliberately writes no bone. It resolves the owner that the
 * contract says should win, records every overlapping candidate and exposes
 * that decision to the final-matrix recorder. Promotion to an enforcing pose
 * graph is a separate, human-approved phase.</p>
 */
public final class EvaPoseGraph
{
    private static final ResourceLocation RIG = new ResourceLocation(
            ProjectSeele.MODID, "eva/eva_rig_schema.json");
    private static final ResourceLocation AUTHORITY = new ResourceLocation(
            ProjectSeele.MODID, "eva/eva_pose_authority_contract.json");
    private static final ResourceLocation ACTIONS = new ResourceLocation(
            ProjectSeele.MODID, "eva/eva_approved_actions.json");
    private static volatile Contract contract = Contract.empty();

    private EvaPoseGraph() {}

    public static void reload(ResourceManager resources)
    {
        try
        {
            String rigText = read(resources, RIG);
            String authorityText = read(resources, AUTHORITY);
            String actionsText = read(resources, ACTIONS);
            JsonObject rig = JsonParser.parseString(rigText).getAsJsonObject();
            JsonObject authority = JsonParser.parseString(
                    authorityText).getAsJsonObject();
            JsonObject actions = JsonParser.parseString(
                    actionsText).getAsJsonObject();
            if (rig.get("schema").getAsInt() != 1
                    || authority.get("schema").getAsInt() != 1
                    || actions.get("schema").getAsInt() != 1)
            {
                throw new IllegalArgumentException(
                        "unsupported EVA Phase-A contract schema");
            }
            String rigVersion = rig.get("rigVersion").getAsString();
            String poseGraphVersion = authority.get(
                    "poseGraphVersion").getAsString();
            if (!rigVersion.equals(authority.get("rigVersion").getAsString())
                    || !rigVersion.equals(actions.get(
                    "rigVersion").getAsString())
                    || !poseGraphVersion.equals(actions.get(
                    "poseGraphVersion").getAsString())
                    || !"OBSERVE_ONLY_NO_BONE_WRITES".equals(
                    authority.get("mode").getAsString()))
            {
                throw new IllegalArgumentException(
                        "EVA Phase-A contract versions disagree");
            }

            List<String> boneOrder = new ArrayList<>();
            Map<String, String> defaultOwners = new LinkedHashMap<>();
            for (JsonElement element : rig.getAsJsonArray("bones"))
            {
                JsonObject bone = element.getAsJsonObject();
                String name = bone.get("name").getAsString();
                if (defaultOwners.put(name,
                        bone.get("defaultOwner").getAsString()) != null)
                {
                    throw new IllegalArgumentException(
                            "duplicate canonical EVA bone " + name);
                }
                boneOrder.add(name);
            }
            if (boneOrder.size() != rig.get("boneCount").getAsInt())
            {
                throw new IllegalArgumentException(
                        "canonical EVA bone count mismatch");
            }

            Map<String, Set<String>> masks = new LinkedHashMap<>();
            for (Map.Entry<String, JsonElement> entry : authority
                    .getAsJsonObject("boneMasks").entrySet())
            {
                masks.put(entry.getKey(), stringSet(
                        entry.getValue().getAsJsonArray()));
            }
            List<String> priority = stringList(authority.getAsJsonArray(
                    "ownerPriority"));
            Map<String, String> actionStatuses = new LinkedHashMap<>();
            for (Map.Entry<String, JsonElement> entry : actions
                    .getAsJsonObject("actions").entrySet())
            {
                actionStatuses.put(entry.getKey(), entry.getValue()
                        .getAsJsonObject().get("status").getAsString());
            }
            contract = new Contract(true, rigVersion, poseGraphVersion,
                    sha256(rigText), sha256(authorityText),
                    sha256(actionsText), List.copyOf(boneOrder),
                    Map.copyOf(defaultOwners), immutableMasks(masks),
                    List.copyOf(priority), Map.copyOf(actionStatuses));
            ProjectSeele.LOGGER.info(
                    "EVA PoseGraph observer loaded: rig={} graph={} bones={} actionLocks={}",
                    rigVersion, poseGraphVersion, boneOrder.size(),
                    actionStatuses.size());
        }
        catch (Exception exception)
        {
            contract = Contract.empty();
            ProjectSeele.LOGGER.error(
                    "EVA PoseGraph observer contracts rejected", exception);
        }
    }

    public static boolean ready()
    {
        return contract.ready();
    }

    public static Contract contract()
    {
        return contract;
    }

    public static Snapshot observe(EvaUnit01Entity entity, float partialTick)
    {
        Contract current = contract;
        if (!current.ready())
        {
            return Snapshot.empty();
        }
        String actionToken = actionToken(entity, partialTick);
        float phase = phase(entity, partialTick);
        LinkedHashSet<String> activeLayers = new LinkedHashSet<>();
        activeLayers.add("BASE_LOCOMOTION");
        Map<String, LinkedHashSet<String>> candidates = new LinkedHashMap<>();
        for (String bone : current.boneOrder())
        {
            candidates.put(bone, new LinkedHashSet<>(Set.of(
                    current.defaultOwners().get(bone))));
        }

        int preview = entity.getMotionLabPhysicsPreview();
        boolean strike = entity.getCockpitAttackAnim(partialTick) > 0.0F
                || entity.getCockpitSmashAnim(partialTick) > 0.0F;
        boolean fullBody = strike && !entity.isPilotCrouching()
                && !entity.isPilotProne();
        if (preview > 0)
        {
            activeLayers.add("MOTION_ENGINE_PREVIEW");
            addCandidate(candidates, current.masks(), "LOWER_BODY",
                    "MOTION_ENGINE_PREVIEW");
            addCandidate(candidates, current.masks(), "UPPER_BODY",
                    "MOTION_ENGINE_PREVIEW");
            addCandidate(candidates, current.masks(), "GRIP",
                    "MOTION_ENGINE_PREVIEW");
        }
        if (entity.isCrucified() || entity.isBerserk())
        {
            activeLayers.add("FULL_BODY_ACTION");
            addCandidate(candidates, current.masks(), "LOWER_BODY",
                    "FULL_BODY_ACTION");
            addCandidate(candidates, current.masks(), "UPPER_BODY",
                    "FULL_BODY_ACTION");
        }
        else if (strike)
        {
            activeLayers.add("STRIKE_ACTION");
            if (fullBody)
            {
                addCandidate(candidates, current.masks(), "LOWER_BODY",
                        "STRIKE_ACTION");
            }
            addCandidate(candidates, current.masks(), "UPPER_BODY",
                    "STRIKE_ACTION");
            addCandidate(candidates, current.masks(), "GRIP",
                    "STRIKE_ACTION");
        }

        if (entity.getWeapon() != EvaUnit01Entity.WEAPON_FISTS)
        {
            activeLayers.add("WEAPON_ACTION");
            addCandidate(candidates, current.masks(), "UPPER_BODY",
                    "WEAPON_ACTION");
            activeLayers.add("GRIP_PROFILE");
        }
        if (entity.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                || entity.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE)
        {
            activeLayers.add("RENDERER_WEAPON_AIM");
            addCandidate(candidates, current.masks(), "AIM_ADAPTER",
                    "RENDERER_WEAPON_AIM");
        }
        if (entity.getPilotEntity() != null)
        {
            activeLayers.add("RENDERER_PILOT_AIM");
            addOwnerCandidate(candidates, "head",
                    "RENDERER_PILOT_AIM");
        }

        Map<String, String> owners = new LinkedHashMap<>();
        Map<String, List<String>> conflicts = new LinkedHashMap<>();
        for (String bone : current.boneOrder())
        {
            LinkedHashSet<String> boneCandidates = candidates.get(bone);
            owners.put(bone, resolve(boneCandidates, current.priority()));
            if (boneCandidates.size() > 1)
            {
                conflicts.put(bone, List.copyOf(boneCandidates));
            }
        }
        boolean eligible = preview == 0
                && entity.getVisualPose() == EvaUnit01Entity.VISUAL_NORMAL;
        return new Snapshot(actionToken, phase,
                List.copyOf(activeLayers), Map.copyOf(owners),
                Map.copyOf(conflicts), eligible,
                actionStatus(actionToken, current.actionStatuses()));
    }

    private static String actionToken(EvaUnit01Entity entity,
                                      float partialTick)
    {
        if (entity.getMotionLabPhysicsPreview() > 0)
        {
            return "motion_engine_preview_"
                    + entity.getMotionLabPhysicsPreview();
        }
        if (entity.isCrucified()) return "crucified";
        if (entity.isBerserk()) return "berserk";
        if (entity.getActivationTicks() > 0) return "activation";
        if (entity.getCockpitSmashAnim(partialTick) > 0.0F)
            return entity.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE
                    ? "progressive_knife" : "unarmed_attack";
        if (entity.getCockpitAttackAnim(partialTick) > 0.0F)
            return entity.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE
                    ? "progressive_knife" : "unarmed_attack";
        if (entity.isPilotProne()) return "prone_crawl";
        if (entity.isPilotCrouching()) return "crouch";
        if (entity.isVisuallyAirborneForRender()) return "jump_landing";
        if (entity.isVisuallyMovingForRender())
            return entity.isPilotSprinting() ? "run" : "walk";
        return "idle";
    }

    private static float phase(EvaUnit01Entity entity, float partialTick)
    {
        return Math.max(entity.getCockpitAttackAnim(partialTick),
                entity.getCockpitSmashAnim(partialTick));
    }

    private static String actionStatus(String action,
                                       Map<String, String> statuses)
    {
        return statuses.getOrDefault(action, "UNLOCKED_RUNTIME_STATE");
    }

    private static void addCandidate(
            Map<String, LinkedHashSet<String>> candidates,
            Map<String, Set<String>> masks, String mask, String owner)
    {
        for (String bone : masks.getOrDefault(mask, Set.of()))
        {
            addOwnerCandidate(candidates, bone, owner);
        }
    }

    private static void addOwnerCandidate(
            Map<String, LinkedHashSet<String>> candidates,
            String bone, String owner)
    {
        LinkedHashSet<String> boneCandidates = candidates.get(bone);
        if (boneCandidates != null)
        {
            boneCandidates.add(owner);
        }
    }

    private static String resolve(Set<String> candidates,
                                  List<String> priority)
    {
        for (String owner : priority)
        {
            if (candidates.contains(owner))
            {
                return owner;
            }
        }
        return candidates.iterator().next();
    }

    private static String read(ResourceManager resources,
                               ResourceLocation location) throws Exception
    {
        try (InputStream stream = resources.getResource(location)
                .orElseThrow(() -> new IllegalStateException(
                        "missing EVA Phase-A contract " + location)).open())
        {
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static String sha256(String text) throws Exception
    {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        return HexFormat.of().formatHex(digest.digest(
                text.getBytes(StandardCharsets.UTF_8)));
    }

    private static List<String> stringList(JsonArray array)
    {
        List<String> result = new ArrayList<>();
        array.forEach(value -> result.add(value.getAsString()));
        return result;
    }

    private static Set<String> stringSet(JsonArray array)
    {
        return Set.copyOf(stringList(array));
    }

    private static Map<String, Set<String>> immutableMasks(
            Map<String, Set<String>> source)
    {
        Map<String, Set<String>> result = new HashMap<>();
        source.forEach((name, mask) -> result.put(name, Set.copyOf(mask)));
        return Collections.unmodifiableMap(result);
    }

    public record Contract(boolean ready, String rigVersion,
                           String poseGraphVersion, String rigSha256,
                           String authoritySha256, String actionsSha256,
                           List<String> boneOrder,
                           Map<String, String> defaultOwners,
                           Map<String, Set<String>> masks,
                           List<String> priority,
                           Map<String, String> actionStatuses)
    {
        private static Contract empty()
        {
            return new Contract(false, "missing", "missing", "missing",
                    "missing", "missing", List.of(), Map.of(), Map.of(),
                    List.of(), Map.of());
        }
    }

    public record Snapshot(String actionToken, float phaseProgress,
                           List<String> activeLayers,
                           Map<String, String> owners,
                           Map<String, List<String>> conflicts,
                           boolean eligibleForHumanReview,
                           String actionLockStatus)
    {
        private static Snapshot empty()
        {
            return new Snapshot("pose_graph_unavailable", 0.0F, List.of(),
                    Map.of(), Map.of(), false, "CONTRACT_REJECTED");
        }
    }
}
