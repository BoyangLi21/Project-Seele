package com.projectseele.mixin;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.OwnableEntity;
import org.jetbrains.annotations.Nullable;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import java.util.UUID;

/** Our installed defenses have persistent local control nodes, rather than an online pilot. */
@Pseudo
@Mixin(targets="com.atsuishio.superbwarfare.entity.vehicle.base.AutoAimableEntity",remap=false)
public abstract class SbwDefenseOwnerMixin implements OwnableEntity
{
    @Override
    @Nullable
    public LivingEntity getOwner()
    {
        Entity self=(Entity)(Object)this;UUID ownerId=this.getOwnerUUID();
        if(ownerId!=null&&self.getTags().contains("seele_r07_defense")&&self.level() instanceof ServerLevel level)
        {
            Entity owner=level.getEntity(ownerId);
            if(owner instanceof LivingEntity living&&owner.getTags().contains("seele_r07_control_node"))return living;
        }
        // Mixin cannot safely remap an invokespecial interface-default call
        // into the Kotlin target class. Match vanilla's player lookup directly.
        return ownerId==null?null:self.level().getPlayerByUUID(ownerId);
    }
}
