package com.projectseele.entity;

import com.projectseele.fx.AtFieldFX;
import com.projectseele.fx.CrossExplosionFX;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraft.network.syncher.*;
import java.util.*;

/** Fourth Angel: low-hovering pursuit type with a pair of sweeping energy whips. */
public class ShamshelEntity extends Monster implements Angel, SiegeAnchorAware, software.bernie.geckolib.animatable.GeoEntity
{
    private final software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache geoCache=software.bernie.geckolib.util.GeckoLibUtil.createInstanceCache(this);
    @Override public software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache getAnimatableInstanceCache(){return geoCache;}
    @Override public void registerControllers(software.bernie.geckolib.core.animation.AnimatableManager.ControllerRegistrar controllers)
    {
        controllers.add(new software.bernie.geckolib.core.animation.AnimationController<>(this,"base",6,state->state.setAndContinue(
                software.bernie.geckolib.core.animation.RawAnimation.begin().thenLoop(state.isMoving()?"animation.Shamshel.move":"animation.Shamshel.idle"))));
    }
    private static final EntityDataAccessor<Float> FIELD=SynchedEntityData.defineId(ShamshelEntity.class,EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Integer> SWEEP=SynchedEntityData.defineId(ShamshelEntity.class,EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> SIDE=SynchedEntityData.defineId(ShamshelEntity.class,EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> YAW=SynchedEntityData.defineId(ShamshelEntity.class,EntityDataSerializers.FLOAT);
    private final EvaPoseSignalClock sweepClock=new EvaPoseSignalClock();
    private final Set<UUID> hitVictims=new HashSet<>();
    @Override public float getAtField(){return entityData.get(FIELD);}
    public boolean isSweeping(){return entityData.get(SWEEP)>=0;}
    public int sweepSide(){return entityData.get(SIDE);}
    public float sweepYaw(){return entityData.get(YAW);}
    public float sweepAge(float partial){return level().isClientSide?sweepClock.sample(FirstBattleSignals.clientFrameTime()):entityData.get(SWEEP);}
    @Override protected void defineSynchedData()
    {super.defineSynchedData();entityData.define(FIELD,700F);entityData.define(SWEEP,-1);entityData.define(SIDE,-1);entityData.define(YAW,0F);}
    @Override public void onSyncedDataUpdated(EntityDataAccessor<?> key)
    {super.onSyncedDataUpdated(key);if(key.equals(SWEEP)&&sweepClock!=null&&level().isClientSide)sweepClock.accept(entityData.get(SWEEP),false,true);}
    private int sweepCooldown = 30;
    private BlockPos siegeBeacon;

    public ShamshelEntity(EntityType<? extends ShamshelEntity> type, Level level)
    {
        super(type, level);
        this.setNoGravity(true);
    }

    public static AttributeSupplier.Builder createAttributes()
    {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 620.0D)
                .add(Attributes.ARMOR, 7.0D)
                .add(Attributes.ATTACK_DAMAGE, 30.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.34D)
                .add(Attributes.FLYING_SPEED, 0.38D)
                .add(Attributes.FOLLOW_RANGE, 96.0D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0D);
    }

    @Override
    protected void registerGoals()
    {
        this.targetSelector.addGoal(1, new NearestAttackableTargetGoal<>(this, EvaUnit01Entity.class, true));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    @Override
    public void tick()
    {
        super.tick();
        this.setNoGravity(true);
        if(level().isClientSide)return;
        if(isSweeping()){tickSweep();return;}
        if(sweepCooldown>0)sweepCooldown--;
        LivingEntity target = this.getTarget();
        if (target == null || !target.isAlive())
        {
            if (this.siegeBeacon != null)
            {
                Vec3 anchor = Vec3.atCenterOf(this.siegeBeacon).add(0.0D, 10.0D, 0.0D);
                Vec3 approach = anchor.subtract(this.position().add(0.0D, 6.0D, 0.0D));
                if (approach.lengthSqr() > 64.0D)
                {
                    this.setDeltaMovement(this.getDeltaMovement().scale(0.72D)
                            .add(approach.normalize().scale(0.11D)));
                }
                else
                {
                    this.setDeltaMovement(this.getDeltaMovement().scale(0.82D));
                }
            }
            else
            {
                this.setDeltaMovement(this.getDeltaMovement().scale(0.85D).add(0.0D,
                        Math.sin(this.tickCount * 0.08D) * 0.006D, 0.0D));
            }
            return;
        }
        Vec3 aim = target.getBoundingBox().getCenter().subtract(this.position().add(0.0D, 30.0D, 0.0D));
        double distance = aim.length();
        float yaw=(float)Math.toDegrees(Math.atan2(-aim.x,aim.z));
        setYRot(net.minecraft.util.Mth.approachDegrees(getYRot(),yaw,3));yBodyRot=getYRot();yHeadRot=getYRot();
        if (distance > 28.0D)
        {
            this.setDeltaMovement(this.getDeltaMovement().scale(0.70D).add(aim.normalize().scale(0.10D)));
        }
        else this.setDeltaMovement(this.getDeltaMovement().scale(.78));
        if (distance < 44.0D && this.sweepCooldown <= 0
                &&Math.abs(net.minecraft.util.Mth.wrapDegrees(yaw-getYRot()))<15)
        {
            entityData.set(SWEEP,0);entityData.set(SIDE,-sweepSide());entityData.set(YAW,getYRot());hitVictims.clear();
            playSound(com.projectseele.registry.ModSounds.SHAMSHEL_WHIP_CHARGE.get(),1.3F,1);
        }
    }

    private void tickSweep()
    {
        int age=entityData.get(SWEEP)+1;entityData.set(SWEEP,age);setDeltaMovement(getDeltaMovement().scale(.6));
        setYRot(sweepYaw());yBodyRot=yHeadRot=getYRot();
        if(age==ShamshelWhipMotion.CONTACT_START)playSound(com.projectseele.registry.ModSounds.SHAMSHEL_WHIP_CRACK.get(),1.6F,1);
        if(age>=ShamshelWhipMotion.CONTACT_START&&age<=ShamshelWhipMotion.CONTACT_END)
        {
            // Sample the same rendered chain through time. The old invisible
            // thirteen-block damage box also hit behind walls and through EVA.
            for(int sample=0;sample<=4;sample++)
            {
                var points=ShamshelWhipMotion.points(this,age-1+sample/4F,1);
                for(int i=1;i<points.size();i++)
                {
                    Vec3 from=points.get(i-1),to=points.get(i);
                    var wall=level().clip(new net.minecraft.world.level.ClipContext(from,to,net.minecraft.world.level.ClipContext.Block.COLLIDER,net.minecraft.world.level.ClipContext.Fluid.NONE,this));
                    Vec3 end=wall.getLocation();
                    for(var victim:level().getEntitiesOfClass(LivingEntity.class,new AABB(from,end).inflate(1.2),
                            e->!hitVictims.contains(e.getUUID())&&(e instanceof EvaUnit01Entity||e instanceof Player&&!e.isPassenger())&&e.isAlive()))
                    {
                        var contact=victim.getBoundingBox().inflate(.7).clip(from,end);
                        if(contact.isEmpty()&&!victim.getBoundingBox().inflate(.7).contains(from))continue;
                        hitVictims.add(victim.getUUID());Vec3 direction=end.subtract(from).normalize();
                        if(com.projectseele.event.EvaHitFeedback.hurt(victim,damageSources().mobAttack(this),30F,contact.orElse(from),direction))
                            victim.push(direction.x*.8,.22,direction.z*.8);
                    }
                    if(wall.getType()!=net.minecraft.world.phys.HitResult.Type.MISS)break;
                }
            }
        }
        if(age>=ShamshelWhipMotion.CYCLE){entityData.set(SWEEP,-1);sweepCooldown=0;}
    }

    @Override
    public void setSiegeBeacon(BlockPos beacon)
    {
        this.siegeBeacon = beacon == null ? null : beacon.immutable();
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag)
    {
        super.addAdditionalSaveData(tag);
        tag.putFloat("AtField",getAtField());tag.putInt("SweepCooldown",sweepCooldown);tag.putInt("SweepAge",entityData.get(SWEEP));
        tag.putInt("SweepSide",sweepSide());tag.putFloat("SweepYaw",sweepYaw());
        var hits=new net.minecraft.nbt.ListTag();hitVictims.forEach(id->hits.add(net.minecraft.nbt.StringTag.valueOf(id.toString())));tag.put("SweepHits",hits);
        if (this.siegeBeacon != null)
        {
            tag.putLong("SiegeBeacon", this.siegeBeacon.asLong());
        }
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag)
    {
        super.readAdditionalSaveData(tag);
        if(tag.contains("AtField"))entityData.set(FIELD,Math.max(0,Math.min(700,tag.getFloat("AtField"))));
        if(tag.contains("SweepCooldown"))sweepCooldown=Math.max(0,Math.min(34,tag.getInt("SweepCooldown")));
        if(tag.contains("SweepAge"))entityData.set(SWEEP,Math.max(-1,Math.min(ShamshelWhipMotion.CYCLE-1,tag.getInt("SweepAge"))));
        entityData.set(SIDE,tag.getInt("SweepSide")<0?-1:1);entityData.set(YAW,tag.getFloat("SweepYaw"));
        hitVictims.clear();for(var hit:tag.getList("SweepHits",8))try{hitVictims.add(UUID.fromString(hit.getAsString()));}catch(IllegalArgumentException ignored){}
        this.siegeBeacon = tag.contains("SiegeBeacon")
                ? BlockPos.of(tag.getLong("SiegeBeacon")) : null;
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        if (this.getAtField() > 0.0F && !com.projectseele.combat.AtFieldRules.bypassesAtField(source))
        {
            if (source.getEntity() instanceof EvaUnit01Entity eva && eva.isMeleeWeapon())
            {
                this.entityData.set(FIELD,Math.max(0.0F,this.getAtField()-amount));
                if (this.level() instanceof ServerLevel server)
                {
                    AtFieldFX.ripple(server, this.getBoundingBox().getCenter(), eva.getForward());
                }
                return true;
            }
            return false;
        }
        return super.hurt(source, amount);
    }

    @Override
    public void die(DamageSource source)
    {
        if (this.level() instanceof ServerLevel server)
        {
            CrossExplosionFX.spawn(server, this.position(), 1.25F);
        }
        super.die(source);
    }
}
