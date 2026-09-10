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
    private static final net.minecraft.network.syncher.EntityDataAccessor<Integer> LASER_AGE=net.minecraft.network.syncher.SynchedEntityData.defineId(EvaPrototypeEntity.class,net.minecraft.network.syncher.EntityDataSerializers.INT);
    private static final net.minecraft.network.syncher.EntityDataAccessor<Integer> LASER_COOLDOWN=net.minecraft.network.syncher.SynchedEntityData.defineId(EvaPrototypeEntity.class,net.minecraft.network.syncher.EntityDataSerializers.INT);
    private static final net.minecraft.network.syncher.EntityDataAccessor<Float> EYE_YAW=net.minecraft.network.syncher.SynchedEntityData.defineId(EvaPrototypeEntity.class,net.minecraft.network.syncher.EntityDataSerializers.FLOAT);
    private static final net.minecraft.network.syncher.EntityDataAccessor<Float> EYE_PITCH=net.minecraft.network.syncher.SynchedEntityData.defineId(EvaPrototypeEntity.class,net.minecraft.network.syncher.EntityDataSerializers.FLOAT);
    private static final net.minecraft.network.syncher.EntityDataAccessor<org.joml.Vector3f> LASER_END=net.minecraft.network.syncher.SynchedEntityData.defineId(EvaPrototypeEntity.class,net.minecraft.network.syncher.EntityDataSerializers.VECTOR3);
    private final EvaPoseSignalClock eyeClock=new EvaPoseSignalClock();
    @Override protected void defineSynchedData(){super.defineSynchedData();entityData.define(LASER_AGE,-1);entityData.define(LASER_COOLDOWN,0);entityData.define(EYE_YAW,0F);entityData.define(EYE_PITCH,0F);entityData.define(LASER_END,new org.joml.Vector3f());}
    public boolean isEyeLaserActive(){return entityData.get(LASER_AGE)>=0;}
    public float eyeLaserAge(float partial){return level().isClientSide?eyeClock.sample(FirstBattleSignals.clientFrameTime()):entityData.get(LASER_AGE);}
    public int eyeLaserCooldown(){return entityData.get(LASER_COOLDOWN);}
    public float eyeAimYaw(){return entityData.get(EYE_YAW);}
    public float eyeAimPitch(){return entityData.get(EYE_PITCH);}
    public Vec3 eyeLaserEnd(){return new Vec3(entityData.get(LASER_END));}
    public void requestEyeLaser(net.minecraft.server.level.ServerPlayer pilot)
    {
        if(getPilotEntity()!=pilot||!isPoweredOn()||isPilotControlLocked()||isFirstBattleActive()||eyeLaserCooldown()>0)return;
        entityData.set(LASER_AGE,0);entityData.set(LASER_COOLDOWN,40);eyeAim(pilot);
        level().playSound(null,getX(),getY()+53,getZ(),com.projectseele.registry.ModSounds.BEAM_CHARGE.get(),net.minecraft.sounds.SoundSource.PLAYERS,.65F,1.45F);
    }
    private void eyeAim(net.minecraft.server.level.ServerPlayer p)
    {entityData.set(EYE_YAW,getYRot()+net.minecraft.util.Mth.clamp(net.minecraft.util.Mth.wrapDegrees(p.getYRot()-getYRot()),-65,65));entityData.set(EYE_PITCH,net.minecraft.util.Mth.clamp(p.getXRot(),-35,35));}
    @Override public void tick()
    {
        super.tick();if(level().isClientSide)return;com.projectseele.world.UNPlugDirector.tick(this);if(eyeLaserCooldown()>0)entityData.set(LASER_COOLDOWN,eyeLaserCooldown()-1);
        if(!isEyeLaserActive())return;
        if(!(getPilotEntity() instanceof net.minecraft.server.level.ServerPlayer pilot)||!isPoweredOn()||isPilotControlLocked()){entityData.set(LASER_AGE,-1);return;}
        int age=entityData.get(LASER_AGE)+1;entityData.set(LASER_AGE,age);if(age<8)eyeAim(pilot);if(age==8)fireEyeLaser(pilot);if(age>=20)entityData.set(LASER_AGE,-1);
    }
    private void fireEyeLaser(net.minecraft.server.level.ServerPlayer pilot)
    {
        var level=(net.minecraft.server.level.ServerLevel)level();Vec3 eye=EvaUNOptics.eye(this,1),direction=Vec3.directionFromRotation(eyeAimPitch(),eyeAimYaw());Vec3 far=eye.add(direction.scale(256));
        var block=level.clip(new net.minecraft.world.level.ClipContext(eye,far,net.minecraft.world.level.ClipContext.Block.COLLIDER,net.minecraft.world.level.ClipContext.Fluid.NONE,this));Vec3 end=block.getLocation();
        var hit=net.minecraft.world.entity.projectile.ProjectileUtil.getEntityHitResult(level,this,eye,end,new net.minecraft.world.phys.AABB(eye,end).inflate(32,80,32),e->e instanceof LivingEntity&&e!=this&&e!=pilot&&!hasPassenger(e)&&e.isAlive()&&!e.isSpectator());
        if(hit!=null)
        {
            LivingEntity target=(LivingEntity)hit.getEntity();
            // This ProjectileUtil overload returns an entity-only hit result;
            // its location is the entity origin, not the ray/surface contact.
            end=target.getBoundingBox().inflate(.3D).clip(eye,end).orElse(hit.getLocation());
            boolean shield=target instanceof Angel a&&a.getAtField()>0;
            com.projectseele.event.EvaHitFeedback.hurt(target,pilot.damageSources().playerAttack(pilot),36,end,direction);
            if(shield)com.projectseele.fx.AtFieldFX.ripple(level,end,direction);
        }
        entityData.set(LASER_END,end.toVector3f());level.playSound(null,eye.x,eye.y,eye.z,com.projectseele.registry.ModSounds.BEAM_FIRE.get(),net.minecraft.sounds.SoundSource.PLAYERS,1,1.65F);
        level.sendParticles(net.minecraft.core.particles.ParticleTypes.ELECTRIC_SPARK,end.x,end.y,end.z,20,.55,.55,.55,.12);
        com.projectseele.ProjectSeele.LOGGER.debug("EVA-UN eye pulse {} -> {}",eye,end);
        if("r11-mechanics".equals(System.getProperty("projectseele.regionalBuild","")))com.projectseele.ProjectSeele.LOGGER.info("R11 EYE PULSE origin={} end={} hit={} direction={}",eye,end,hit==null?"none":hit.getEntity().getType(),direction);
    }
    @Override public void onSyncedDataUpdated(net.minecraft.network.syncher.EntityDataAccessor<?> key){super.onSyncedDataUpdated(key);if(key.equals(LASER_AGE)&&eyeClock!=null&&level().isClientSide)eyeClock.accept(entityData.get(LASER_AGE),false,true);}
    @Override public void addAdditionalSaveData(net.minecraft.nbt.CompoundTag t){super.addAdditionalSaveData(t);t.putInt("UNEyeCooldown",eyeLaserCooldown());}
    @Override public void readAdditionalSaveData(net.minecraft.nbt.CompoundTag t){super.readAdditionalSaveData(t);entityData.set(LASER_COOLDOWN,t.getInt("UNEyeCooldown"));entityData.set(LASER_AGE,-1);}
    public EvaPrototypeEntity(EntityType<? extends EvaUnit01Entity> type,Level level)
    {
        super(type,level);
    }

    @Override
    public boolean isExperimentalUnit()
    {
        return true;
    }

    public boolean isInsideTestHangar()
    {
        return this.level().dimension().equals(com.projectseele.world.FacilitySchemaV2.DIMENSION)
                && this.getX()>=6384 && this.getX()<=6500
                && this.getY()>=76 && this.getY()<=160
                && this.getZ()>=-6288 && this.getZ()<=-6136
                && this.level().getBlockState(new net.minecraft.core.BlockPos(6442,76,-6205))
                    .is(com.projectseele.registry.ModBlocks.NERV_FLOOR_PANEL.get());
    }

    @Override
    public InteractionResult tryEnterFromPlug(Player player,boolean requireAim)
    {
        if(this.isNervLogisticsLocked())
        {
            player.displayClientMessage(Component.literal("请先在控制室排空 LCL 并开启试验舱门"),true);
            return InteractionResult.CONSUME;
        }
        var capsule=com.projectseele.world.UNPlugDirector.capsule(this);
        if(capsule!=null)return capsule.tryBoardFromHatch(player);
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
