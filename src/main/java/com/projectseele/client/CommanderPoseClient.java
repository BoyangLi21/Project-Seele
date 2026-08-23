package com.projectseele.client;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.world.entity.LivingEntity;

/** Client mirror of server-authoritative seated commander poses. */
public final class CommanderPoseClient
{
    private static final Map<Integer, Boolean> ACTIVE =
            new ConcurrentHashMap<>();

    private CommanderPoseClient()
    {
    }

    public static void setActive(int entityId, boolean active)
    {
        if (active)
        {
            ACTIVE.put(entityId, true);
        }
        else
        {
            ACTIVE.remove(entityId);
        }
    }

    public static boolean isActive(LivingEntity entity)
    {
        return entity != null && entity.isPassenger()
                && ACTIVE.getOrDefault(entity.getId(), false);
    }
}
