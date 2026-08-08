package com.projectseele.entity;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.material.PushReaction;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.NetworkHooks;

/**
 * Invisible fixed riding anchor for a physical NERV command chair.
 *
 * <p>The visible chair remains ordinary authored blocks.  Keeping the mount
 * separate means art revisions can change the chair silhouette without
 * turning the command room into a collection of movable vehicles.</p>
 */
public final class NervCommandSeatEntity extends Entity
{
    public NervCommandSeatEntity(
            EntityType<? extends NervCommandSeatEntity> type, Level level)
    {
        super(type, level);
        this.noPhysics = true;
        this.setNoGravity(true);
        this.setInvulnerable(true);
    }

    @Override
    protected void defineSynchedData()
    {
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag)
    {
    }

    @Override
    protected void addAdditionalSaveData(CompoundTag tag)
    {
    }

    @Override
    public Packet<ClientGamePacketListener> getAddEntityPacket()
    {
        return NetworkHooks.getEntitySpawningPacket(this);
    }

    @Override
    public void tick()
    {
        super.tick();
        this.setDeltaMovement(Vec3.ZERO);
    }

    @Override
    protected boolean canAddPassenger(Entity passenger)
    {
        return passenger instanceof Player && this.getPassengers().isEmpty();
    }

    @Override
    protected void positionRider(Entity passenger, MoveFunction move)
    {
        if (!this.hasPassenger(passenger))
        {
            return;
        }
        move.accept(passenger, this.getX(), this.getY(), this.getZ());
    }

    @Override
    public Vec3 getDismountLocationForPassenger(LivingEntity passenger)
    {
        // Every authored chair faces north. Two blocks south clears its
        // physical backrest before placing the player on the supported aisle.
        return this.position().add(0.0D, 0.08D, 2.25D);
    }

    @Override
    public boolean isPickable()
    {
        return false;
    }

    @Override
    public boolean isPushable()
    {
        return false;
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        return false;
    }

    @Override
    public PushReaction getPistonPushReaction()
    {
        return PushReaction.IGNORE;
    }
}
