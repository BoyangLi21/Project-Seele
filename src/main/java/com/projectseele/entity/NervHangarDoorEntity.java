package com.projectseele.entity;

import com.projectseele.registry.ModEntities;
import java.util.Comparator;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.material.PushReaction;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.NetworkHooks;

/** Transient visual leaves for one physical wet-cage pressure gate. */
public final class NervHangarDoorEntity extends Entity
{
    private static final EntityDataAccessor<Integer> DATA_VARIANT =
            SynchedEntityData.defineId(NervHangarDoorEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> DATA_OPEN =
            SynchedEntityData.defineId(NervHangarDoorEntity.class,
                    EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> DATA_TARGET =
            SynchedEntityData.defineId(NervHangarDoorEntity.class,
                    EntityDataSerializers.FLOAT);

    private float clientOpen;
    private float clientOpenO;

    public NervHangarDoorEntity(EntityType<? extends NervHangarDoorEntity> type,
                                Level level)
    {
        super(type, level);
        this.noPhysics = true;
        this.noCulling = true;
        this.setNoGravity(true);
        this.setInvulnerable(true);
    }

    @Override
    protected void defineSynchedData()
    {
        this.entityData.define(DATA_VARIANT, 0);
        this.entityData.define(DATA_OPEN, 0.0F);
        this.entityData.define(DATA_TARGET, 0.0F);
    }

    @Override protected void readAdditionalSaveData(CompoundTag tag) {}
    @Override protected void addAdditionalSaveData(CompoundTag tag) {}

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
        if (this.level().isClientSide)
        {
            this.clientOpenO = this.clientOpen;
            this.clientOpen = this.entityData.get(DATA_OPEN);
            return;
        }
        float current = this.entityData.get(DATA_OPEN);
        float next = Mth.approach(current,
                this.entityData.get(DATA_TARGET), 0.075F);
        if (Math.abs(next - current) > 1.0E-4F)
        {
            this.entityData.set(DATA_OPEN, next);
        }
    }

    public int getVariant()
    {
        return this.entityData.get(DATA_VARIANT);
    }

    public float getOpenProgress(float partialTick)
    {
        return Mth.lerp(partialTick, this.clientOpenO, this.clientOpen);
    }

    public static void reconcile(ServerLevel level, int variant,
            Vec3 centre, boolean open)
    {
        AABB search = new AABB(centre, centre).inflate(3.0D);
        List<NervHangarDoorEntity> matches = level.getEntitiesOfClass(
                NervHangarDoorEntity.class, search,
                entity -> entity.getVariant() == variant);
        matches.sort(Comparator.comparingInt(Entity::getId));
        NervHangarDoorEntity door;
        if (matches.isEmpty())
        {
            door = ModEntities.NERV_HANGAR_DOOR.get().create(level);
            if (door == null)
            {
                return;
            }
            door.entityData.set(DATA_VARIANT, variant);
            door.setPos(centre.x, centre.y, centre.z);
            level.addFreshEntity(door);
        }
        else
        {
            door = matches.get(0);
            if (door.position().distanceToSqr(centre) > 1.0E-8D)
            {
                door.setPos(centre.x, centre.y, centre.z);
            }
            for (int index = 1; index < matches.size(); index++)
            {
                matches.get(index).discard();
            }
        }
        float target = open ? 1.0F : 0.0F;
        if (Math.abs(door.entityData.get(DATA_TARGET) - target) > 1.0E-4F)
        {
            door.entityData.set(DATA_TARGET, target);
        }
    }

    @Override public boolean isPickable() { return false; }
    @Override public boolean isPushable() { return false; }
    @Override public boolean hurt(DamageSource source, float amount) { return false; }
    @Override public PushReaction getPistonPushReaction() { return PushReaction.IGNORE; }
}
