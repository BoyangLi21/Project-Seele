package com.projectseele.entity;

import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;

/** Native block-display geometry with tracking suitable for a port-scale structure. */
public final class IndustrialMemberEntity extends Display.BlockDisplay
{
    public IndustrialMemberEntity(EntityType<?> type, Level level)
    {
        super(type, level);
    }
}
