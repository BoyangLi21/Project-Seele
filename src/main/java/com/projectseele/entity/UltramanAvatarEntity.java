package com.projectseele.entity;

import com.projectseele.registry.ModEntities;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.material.PushReaction;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.NetworkHooks;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/** Non-colliding high-detail Ultraman shell owned by one transformed player. */
public final class UltramanAvatarEntity extends Entity implements GeoEntity
{
    private static final EntityDataAccessor<Integer> DATA_OWNER_ID =
            SynchedEntityData.defineId(UltramanAvatarEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> DATA_SCALE =
            SynchedEntityData.defineId(UltramanAvatarEntity.class,
                    EntityDataSerializers.FLOAT);
    private static final RawAnimation IDLE = RawAnimation.begin()
            .thenLoop("animation.ultraman.idle");
    private static final RawAnimation WALK = RawAnimation.begin()
            .thenLoop("animation.ultraman.walk");
    private static final RawAnimation RUN = RawAnimation.begin()
            .thenLoop("animation.ultraman.run");
    private final AnimatableInstanceCache cache =
            GeckoLibUtil.createInstanceCache(this);
    private float clientScale = 1.0F;
    private float clientScaleO = 1.0F;

    public UltramanAvatarEntity(
            EntityType<? extends UltramanAvatarEntity> type, Level level)
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
        this.entityData.define(DATA_OWNER_ID, -1);
        this.entityData.define(DATA_SCALE, 1.0F);
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
            this.clientScaleO = this.clientScale;
            this.clientScale = this.entityData.get(DATA_SCALE);
            Entity owner = this.level().getEntity(this.getOwnerId());
            if (owner != null)
            {
                this.setPos(owner.position());
                this.setYRot(owner.getYRot());
            }
            return;
        }
        Entity owner = this.level().getEntity(this.getOwnerId());
        if (!(owner instanceof Player player) || !player.isAlive())
        {
            this.discard();
            return;
        }
        this.setPos(player.position());
        this.setYRot(player.yBodyRot);
    }

    public int getOwnerId()
    {
        return this.entityData.get(DATA_OWNER_ID);
    }

    public float getVisualScale(float partialTick)
    {
        return net.minecraft.util.Mth.lerp(partialTick,
                this.clientScaleO, this.clientScale);
    }

    public void configure(Player owner, float scale)
    {
        this.entityData.set(DATA_OWNER_ID, owner.getId());
        this.entityData.set(DATA_SCALE, scale);
        this.setPos(owner.position());
        this.setYRot(owner.yBodyRot);
    }

    public LivingEntity owner()
    {
        Entity owner = this.level().getEntity(this.getOwnerId());
        return owner instanceof LivingEntity living ? living : null;
    }

    public static UltramanAvatarEntity reconcile(
            ServerLevel level, Player owner, float scale)
    {
        AABB search = owner.getBoundingBox().inflate(96.0D);
        List<UltramanAvatarEntity> matches = level.getEntitiesOfClass(
                UltramanAvatarEntity.class, search,
                avatar -> avatar.getOwnerId() == owner.getId());
        UltramanAvatarEntity avatar;
        if (matches.isEmpty())
        {
            avatar = ModEntities.ULTRAMAN_AVATAR.get().create(level);
            if (avatar == null)
            {
                return null;
            }
            avatar.configure(owner, scale);
            if (!level.addFreshEntity(avatar))
            {
                return null;
            }
        }
        else
        {
            avatar = matches.get(0);
            avatar.configure(owner, scale);
            for (int index = 1; index < matches.size(); index++)
            {
                matches.get(index).discard();
            }
        }
        return avatar;
    }

    public static void remove(ServerLevel level, Player owner)
    {
        AABB search = owner.getBoundingBox().inflate(96.0D);
        level.getEntitiesOfClass(UltramanAvatarEntity.class, search,
                avatar -> avatar.getOwnerId() == owner.getId())
                .forEach(Entity::discard);
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers)
    {
        controllers.add(new AnimationController<>(this, "movement", 4,
                state ->
                {
                    LivingEntity owner = this.owner();
                    if (owner == null
                            || owner.getDeltaMovement().horizontalDistanceSqr()
                            < 0.002D)
                    {
                        state.setAnimation(IDLE);
                    }
                    else if (owner.isSprinting())
                    {
                        state.setAnimation(RUN);
                    }
                    else
                    {
                        state.setAnimation(WALK);
                    }
                    return PlayState.CONTINUE;
                }));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache()
    {
        return this.cache;
    }

    @Override public boolean isPickable() { return false; }
    @Override public boolean isPushable() { return false; }
    @Override public boolean hurt(DamageSource source, float amount) { return false; }
    @Override public PushReaction getPistonPushReaction() { return PushReaction.IGNORE; }
}
