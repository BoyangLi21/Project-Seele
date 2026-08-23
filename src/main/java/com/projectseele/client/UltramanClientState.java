package com.projectseele.client;

import com.projectseele.world.UltramanTransformState;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.util.Mth;

/** Client interpolation and Hayata-pose timing for Ultraman transforms. */
public final class UltramanClientState
{
    private static final Map<Integer, Transition> STATES = new HashMap<>();

    private UltramanClientState() {}

    public static void setTarget(int entityId, boolean active,
            float currentScale, boolean hayataPose)
    {
        ClientLevel level = Minecraft.getInstance().level;
        if (level == null)
        {
            return;
        }
        STATES.put(entityId, new Transition(currentScale,
                active ? UltramanTransformState.TARGET_SCALE : 1.0F,
                level.getGameTime(), active && hayataPose));
        if (level.getEntity(entityId) instanceof AbstractClientPlayer player)
        {
            player.refreshDimensions();
        }
    }

    public static float scale(AbstractClientPlayer player, float partialTick)
    {
        Transition transition = STATES.get(player.getId());
        if (transition == null)
        {
            return 1.0F;
        }
        float elapsed = player.level().getGameTime()
                - transition.startedAt + partialTick;
        if (transition.target > 1.0F)
        {
            elapsed -= UltramanTransformState.POSE_TICKS;
        }
        float t = Mth.clamp(elapsed
                / UltramanTransformState.TRANSITION_TICKS, 0.0F, 1.0F);
        float smooth = t * t * (3.0F - 2.0F * t);
        return Mth.lerp(smooth, transition.from, transition.target);
    }

    public static boolean hayataPose(AbstractClientPlayer player)
    {
        Transition transition = STATES.get(player.getId());
        return transition != null && transition.hayata
                && player.level().getGameTime() - transition.startedAt
                < UltramanTransformState.POSE_TICKS;
    }

    public static boolean hidePlayer(AbstractClientPlayer player)
    {
        return scale(player, 0.0F) > 1.01F;
    }

    public static void tick(ClientLevel level)
    {
        Iterator<Map.Entry<Integer, Transition>> iterator =
                STATES.entrySet().iterator();
        while (iterator.hasNext())
        {
            Map.Entry<Integer, Transition> entry = iterator.next();
            if (!(level.getEntity(entry.getKey())
                    instanceof AbstractClientPlayer player))
            {
                iterator.remove();
                continue;
            }
            player.refreshDimensions();
            Transition transition = entry.getValue();
            if (transition.target <= 1.0F
                    && level.getGameTime() - transition.startedAt
                    > UltramanTransformState.TRANSITION_TICKS)
            {
                iterator.remove();
            }
        }
    }

    public static void clear()
    {
        STATES.clear();
    }

    private record Transition(float from, float target, long startedAt,
                              boolean hayata) {}
}
