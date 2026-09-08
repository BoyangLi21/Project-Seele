package com.projectseele.entity;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.InteractionResult;
import net.minecraft.network.chat.Component;

/** Independent experimental airframe; it never occupies a canonical Unit-01 fleet slot. */
public final class EvaPrototypeEntity extends EvaUnit01Entity
{
    public EvaPrototypeEntity(EntityType<? extends EvaUnit01Entity> type,Level level)
    {
        super(type,level);
    }

    @Override
    public boolean isExperimentalUnit()
    {
        return true;
    }

    @Override
    public InteractionResult tryEnterFromPlug(Player player,boolean requireAim)
    {
        if(this.isNervLogisticsLocked())
        {
            player.displayClientMessage(Component.literal("请先在控制室排空 LCL 并开启试验舱门"),true);
            return InteractionResult.CONSUME;
        }
        return super.tryEnterFromPlug(player,requireAim);
    }

    @Override
    public Vec3 getDismountLocationForPassenger(LivingEntity passenger)
    {
        // This surface project has its own gantry and never borrows Unit-01's capsule.
        if(this.position().distanceTo(new Vec3(6442.5,77,-6205.5))<4
                &&this.level().dimension().equals(com.projectseele.world.FacilitySchemaV2.DIMENSION))
            return new Vec3(6442.5,127,-6217.5);
        return super.getDismountLocationForPassenger(passenger);
    }
}
