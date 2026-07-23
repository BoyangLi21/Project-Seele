package com.projectseele.world;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.NervCarrierPlatformEntity;
import com.projectseele.registry.ModEntities;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;

/** Runtime ownership for non-saving mag-lev carrier display entities. */
public final class NervCarrierVisuals
{
    private static final Map<UUID, UUID> PLATFORM_BY_EVA = new HashMap<>();

    private NervCarrierVisuals() {}

    public static void update(ServerLevel level, EvaUnit01Entity unit,
                              double x, double y, double z)
    {
        NervCarrierPlatformEntity platform = resolve(level, unit.getUUID());
        if (platform == null)
        {
            platform = ModEntities.NERV_CARRIER_PLATFORM.get().create(level);
            if (platform == null)
            {
                return;
            }
            platform.assignVariant(unit.getUnitVariant());
            platform.moveControlled(x, y + 0.04D, z);
            if (!level.addFreshEntity(platform))
            {
                return;
            }
            PLATFORM_BY_EVA.put(unit.getUUID(), platform.getUUID());
            ProjectSeele.LOGGER.info(
                    "NERV visual carrier engaged: eva={} platform={}",
                    unit.getStringUUID(), platform.getStringUUID());
        }
        platform.assignVariant(unit.getUnitVariant());
        platform.moveControlled(x, y + 0.04D, z);
    }

    public static void remove(ServerLevel level, EvaUnit01Entity unit)
    {
        UUID platformId = PLATFORM_BY_EVA.remove(unit.getUUID());
        if (platformId == null)
        {
            return;
        }
        Entity entity = level.getEntity(platformId);
        if (entity instanceof NervCarrierPlatformEntity platform)
        {
            platform.discard();
        }
    }

    public static void resetRuntime()
    {
        PLATFORM_BY_EVA.clear();
    }

    private static NervCarrierPlatformEntity resolve(ServerLevel level,
                                                      UUID evaId)
    {
        UUID platformId = PLATFORM_BY_EVA.get(evaId);
        if (platformId == null)
        {
            return null;
        }
        Entity entity = level.getEntity(platformId);
        if (entity instanceof NervCarrierPlatformEntity platform
                && platform.isAlive())
        {
            return platform;
        }
        PLATFORM_BY_EVA.remove(evaId);
        return null;
    }
}
