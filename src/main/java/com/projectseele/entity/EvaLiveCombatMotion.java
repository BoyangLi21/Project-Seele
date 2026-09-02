package com.projectseele.entity;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;

/** Common-side root curves for project-owner-selected live combat actions. */
public final class EvaLiveCombatMotion
{
    private static final String ORDINARY_RESOURCE =
            "/assets/projectseele/motion/eva_ordinary_attack_group_c_v1.json";
    private static final String KICK_RESOURCE =
            "/assets/projectseele/motion/eva_kick_side_left_v1.json";
    private static final String KNIFE_RESOURCE =
            "/assets/projectseele/motion/eva_knife_attacks_phase_m_v1.json";
    private static final Map<String, RootClip> ORDINARY = load(
            ORDINARY_RESOURCE, "EVA ordinary combat root");
    private static final Map<String, RootClip> KICK = load(
            KICK_RESOURCE, "EVA side-kick root");
    private static final Map<String, RootClip> KNIFE = load(
            KNIFE_RESOURCE, "EVA approved knife root");

    private EvaLiveCombatMotion() {}

    public static void preload()
    {
        // Static initialization performs validation and emits the load audit.
    }

    public static Vec3 ordinary(int visualStage, float progress)
    {
        String clip = switch (visualStage)
        {
            case 0 -> "ordinary_attack_group_c_stage_1";
            case 1 -> "ordinary_attack_group_c_stage_2";
            case 2 -> "ordinary_attack_group_c_stage_3";
            // The loop clip's root-only foot lock contains a large local
            // correction. World authority reuses stage 1's captured path;
            // only the connector rotations come from the loop variant.
            default -> "ordinary_attack_group_c_stage_1";
        };
        return sample(ORDINARY.get(clip), progress);
    }

    public static Vec3 kick(float progress)
    {
        return sample(KICK.get("kick_side_left"), progress);
    }

    public static Vec3 knife(boolean reverse, float progress)
    {
        return sample(KNIFE.get(reverse
                ? "eva_short_knife_stab_twist_reverse"
                : "eva_locked_knife_stab_twist_forward"), progress);
    }

    private static Map<String, RootClip> load(String path, String label)
    {
        try (InputStream stream = EvaLiveCombatMotion.class
                .getResourceAsStream(path))
        {
            if (stream == null)
            {
                throw new IllegalStateException("missing " + path);
            }
            JsonObject root = JsonParser.parseReader(new InputStreamReader(
                    stream, StandardCharsets.UTF_8)).getAsJsonObject();
            if (root.get("schema").getAsInt() != 2)
            {
                throw new IllegalArgumentException(
                        "unsupported live combat motion schema");
            }
            Map<String, RootClip> clips = new HashMap<>();
            for (Map.Entry<String, JsonElement> entry
                    : root.getAsJsonObject("clips").entrySet())
            {
                JsonArray frames = entry.getValue().getAsJsonObject()
                        .getAsJsonArray("frames");
                Vec3[] positions = new Vec3[frames.size()];
                for (int index = 0; index < frames.size(); index++)
                {
                    JsonArray value = frames.get(index).getAsJsonObject()
                            .getAsJsonArray("root_m");
                    positions[index] = new Vec3(
                            value.get(0).getAsDouble(),
                            value.get(1).getAsDouble(),
                            value.get(2).getAsDouble());
                }
                clips.put(entry.getKey(), new RootClip(positions));
            }
            ProjectSeele.LOGGER.info("{} loaded: clips={} frames={}",
                    label, clips.size(), clips.values().stream()
                            .mapToInt(clip -> clip.positions.length).sum());
            return Map.copyOf(clips);
        }
        catch (Exception exception)
        {
            ProjectSeele.LOGGER.error(label + " rejected", exception);
            return Map.of();
        }
    }

    private static Vec3 sample(RootClip clip, float progress)
    {
        if (clip == null || clip.positions.length == 0)
        {
            return Vec3.ZERO;
        }
        double position = Mth.clamp(progress, 0.0F, 1.0F)
                * (clip.positions.length - 1);
        int first = Math.min(clip.positions.length - 1,
                (int)Math.floor(position));
        int second = Math.min(clip.positions.length - 1, first + 1);
        return clip.positions[first].lerp(
                clip.positions[second], position - first);
    }

    private record RootClip(Vec3[] positions) {}
}
