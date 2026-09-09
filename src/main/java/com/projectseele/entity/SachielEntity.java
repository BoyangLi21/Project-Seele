package com.projectseele.entity;

import com.projectseele.fx.AtFieldFX;
import com.projectseele.fx.CrossExplosionFX;
import com.projectseele.network.ClientboundNukeFxPacket;
import com.projectseele.network.SeeleNetwork;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.Level.ExplosionInteraction;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.PacketDistributor;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.util.GeckoLibUtil;

/** Third Angel: a close-range giant that ends the fight with a cross-shaped self-destruction. */
public class SachielEntity extends Monster implements Angel, GeoEntity, SiegeAnchorAware, FirstBattleSignals.Actor
{
    private static final FirstBattleSignals.SignalSet FIRST_BATTLE=new FirstBattleSignals.SignalSet(SachielEntity.class);
    private static final net.minecraft.network.syncher.EntityDataAccessor<Float> FIELD=net.minecraft.network.syncher.SynchedEntityData.defineId(SachielEntity.class,net.minecraft.network.syncher.EntityDataSerializers.FLOAT);
    private boolean firstBattleUsed,firstBattleDeathResolved;
    private float firstBattlePreviousField;
    @Override public FirstBattleSignals.SignalSet firstBattleSignals(){return FIRST_BATTLE;}
    @Override public boolean isFirstBattleEva(){return false;}
    public boolean isFirstBattleActive(){return FIRST_BATTLE.active(this);}
    public boolean hasUsedFirstBattle(){return firstBattleUsed;}
    @Override protected void defineSynchedData(){super.defineSynchedData();FIRST_BATTLE.define(this.entityData);this.entityData.define(FIELD,900F);}
    public void beginFirstBattle(FirstBattleSignals.Spec spec,int partner)
    {
        firstBattlePreviousField=atField;firstBattleUsed=true;selfDestructTicks=-1;this.getNavigation().stop();FIRST_BATTLE.begin(this,spec,partner,-1);setFirstBattleField(900);
    }
    public void endFirstBattle(){if(isFirstBattleActive())FIRST_BATTLE.end(this);}
    public void recoverFirstBattle(){endFirstBattle();setFirstBattleField(firstBattlePreviousField);}
    public void setFirstBattleField(float value){atField=Math.max(0,value);this.entityData.set(FIELD,atField);}
    public void finishFirstBattle(EvaUnit01Entity eva,net.minecraft.server.level.ServerPlayer pilot)
    {
        if(firstBattleDeathResolved||!this.isAlive())return;firstBattleDeathResolved=true;this.setLastHurtByPlayer(pilot);this.setHealth(0);this.die(this.damageSources().mobAttack(eva));
    }
    @Override public void aiStep()
    {
        FIRST_BATTLE.clientPhysics(this);if(isFirstBattleActive()){FirstBattleClip.applyKinematics(this);return;}super.aiStep();
    }
    private static final RawAnimation ANIM_IDLE = RawAnimation.begin().thenLoop("animation.Sachiel.idle");
    private static final RawAnimation ANIM_WALK = RawAnimation.begin().thenLoop("animation.Sachiel.move");
    private final AnimatableInstanceCache geoCache = GeckoLibUtil.createInstanceCache(this);
    private static final float AT_FIELD_MAX = 900.0F;
    private float atField = AT_FIELD_MAX;
    private int spearCooldown = 45;
    private int selfDestructTicks = -1;
    private BlockPos siegeBeacon;

    public SachielEntity(EntityType<? extends SachielEntity> type, Level level)
    {
        super(type, level);
        this.setMaxUpStep(2.0F);
    }

    public static AttributeSupplier.Builder createAttributes()
    {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 800.0D)
                .add(Attributes.ARMOR, 10.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.28D)
                .add(Attributes.ATTACK_DAMAGE, 42.0D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0D)
                .add(Attributes.FOLLOW_RANGE, 96.0D);
    }

    @Override
    protected void registerGoals()
    {
        this.goalSelector.addGoal(2, new MeleeAttackGoal(this, 1.0D, true));
        this.goalSelector.addGoal(7, new WaterAvoidingRandomStrollGoal(this, 0.65D));
        this.targetSelector.addGoal(1, new NearestAttackableTargetGoal<>(this, EvaUnit01Entity.class, true));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    @Override
    public void tick()
    {
        super.tick();
        if(isFirstBattleActive())return;
        if(!this.level().isClientSide&&!firstBattleUsed&&this.getHealth()<=this.getMaxHealth()*.32F&&this.tickCount%5==0)
        {
            // Contact root motion can temporarily clear vanilla's onGround bit.
            // Retry once the pair settles; rifle damage is eligible as well.
            for(var eva:this.level().getEntitiesOfClass(EvaUnit01Entity.class,this.getBoundingBox().inflate(48,80,48),e->e.getPilotEntity()!=null))
                if(com.projectseele.event.FirstBattleDirector.tryStart(this,eva,false))return;
        }
        if (this.level().isClientSide)
        {
            return;
        }
        this.entityData.set(FIELD,this.atField);
        if(isFirstBattleActive())return;
        if (this.selfDestructTicks >= 0)
        {
            this.setDeltaMovement(Vec3.ZERO);
            if (--this.selfDestructTicks <= 0)
            {
                selfDestruct();
            }
            return;
        }
        LivingEntity target = this.getTarget();
        if ((target == null || !target.isAlive()) && this.siegeBeacon != null)
        {
            if (this.distanceToSqr(Vec3.atCenterOf(this.siegeBeacon)) > 64.0D)
            {
                this.getNavigation().moveTo(this.siegeBeacon.getX() + 0.5D,
                        this.siegeBeacon.getY(), this.siegeBeacon.getZ() + 0.5D,
                        1.0D);
            }
            else
            {
                this.getNavigation().stop();
            }
        }
        if (target != null && target.isAlive() && --this.spearCooldown <= 0)
        {
            this.spearCooldown = 75;
            if (this.distanceToSqr(target) > 100.0D && this.distanceToSqr(target) < 3600.0D
                    && this.hasLineOfSight(target))
            {
                target.hurt(this.damageSources().mobAttack(this), 55.0F);
                target.push((target.getX() - this.getX()) * 0.12D, 0.55D,
                        (target.getZ() - this.getZ()) * 0.12D);
            }
        }
        if (this.getHealth() <= this.getMaxHealth() * 0.14F)
        {
            this.selfDestructTicks = 60;
        }
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        if(isFirstBattleActive())return source.is(net.minecraft.tags.DamageTypeTags.BYPASSES_INVULNERABILITY)&&super.hurt(source,amount);
        if (this.selfDestructTicks >= 0)
        {
            return false;
        }
        if (this.atField > 0.0F && !com.projectseele.combat.AtFieldRules.bypassesAtField(source))
        {
            if (source.getEntity() instanceof EvaUnit01Entity eva && eva.isMeleeWeapon())
            {
                this.atField = Math.max(0.0F, this.atField - amount);
                this.entityData.set(FIELD,this.atField);
                if (this.level() instanceof ServerLevel server)
                {
                    AtFieldFX.ripple(server, this.getBoundingBox().getCenter(), eva.getForward());
                }
                return true;
            }
            return false;
        }
        if (amount >= this.getHealth())
        {
            this.setHealth(1.0F);
            if(source.getEntity() instanceof EvaUnit01Entity eva&&com.projectseele.event.FirstBattleDirector.tryStart(this,eva,false))return true;
            this.selfDestructTicks = 45;
            return true;
        }
        boolean accepted=super.hurt(source,amount);
        if(accepted&&source.getEntity() instanceof EvaUnit01Entity eva)com.projectseele.event.FirstBattleDirector.tryStart(this,eva,false);
        return accepted;
    }

    private void selfDestruct()
    {
        if (!(this.level() instanceof ServerLevel server))
        {
            return;
        }
        Vec3 center = this.position().add(0.0D, 8.0D, 0.0D);
        CrossExplosionFX.spawn(server, center, 2.2F);
        SeeleNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> this),
                new ClientboundNukeFxPacket(center.x, center.y, center.z, 3.2F, false));
        server.explode(this, this.getX(), this.getY() + 4.0D, this.getZ(), 16.0F, ExplosionInteraction.MOB);
        this.discard();
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
        FIRST_BATTLE.save(this,tag);tag.putFloat("SachielAtField",atField);tag.putInt("SachielSelfDestruct",selfDestructTicks);tag.putBoolean("FirstBattleUsed",firstBattleUsed);tag.putBoolean("FirstBattleDeathResolved",firstBattleDeathResolved);tag.putFloat("FirstBattlePreviousField",firstBattlePreviousField);
        if (this.siegeBeacon != null)
        {
            tag.putLong("SiegeBeacon", this.siegeBeacon.asLong());
        }
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag)
    {
        super.readAdditionalSaveData(tag);
        atField=tag.contains("SachielAtField")?tag.getFloat("SachielAtField"):900;this.entityData.set(FIELD,atField);
        selfDestructTicks=tag.contains("SachielSelfDestruct")?tag.getInt("SachielSelfDestruct"):-1;firstBattleUsed=tag.getBoolean("FirstBattleUsed");firstBattleDeathResolved=tag.getBoolean("FirstBattleDeathResolved");firstBattlePreviousField=tag.getFloat("FirstBattlePreviousField");FIRST_BATTLE.restore(this,tag);
        this.siegeBeacon = tag.contains("SiegeBeacon")
                ? BlockPos.of(tag.getLong("SiegeBeacon")) : null;
    }

    public float getAtField()
    {
        return this.level().isClientSide?this.entityData.get(FIELD):this.atField;
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers)
    {
        controllers.add(new AnimationController<>(this, "base", 6, state ->
                state.setAndContinue(state.isMoving() ? ANIM_WALK : ANIM_IDLE)));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache()
    {
        return this.geoCache;
    }
}
