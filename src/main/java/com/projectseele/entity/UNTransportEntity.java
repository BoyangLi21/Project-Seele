package com.projectseele.entity;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.network.syncher.*;
import net.minecraft.world.entity.*;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.util.Mth;
import net.minecraftforge.network.NetworkHooks;

/** One persistent service aircraft per active airlift, owned by the server job. */
public final class UNTransportEntity extends Entity
{
    private static final EntityDataAccessor<Integer> SERIAL=SynchedEntityData.defineId(UNTransportEntity.class,EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> CARGO=SynchedEntityData.defineId(UNTransportEntity.class,EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Integer> KIND=SynchedEntityData.defineId(UNTransportEntity.class,EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> CARGO_ID=SynchedEntityData.defineId(UNTransportEntity.class,EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> DEPLOY=SynchedEntityData.defineId(UNTransportEntity.class,EntityDataSerializers.FLOAT);
    private float rig,oldRig,jaw=1,oldJaw=1;
    private double tx,ty,tz;private float targetYaw;private int interpolation;
    public UNTransportEntity(EntityType<? extends UNTransportEntity> type,Level level)
    {super(type,level);noPhysics=true;noCulling=true;setNoGravity(true);setInvulnerable(true);}
    @Override protected void defineSynchedData(){entityData.define(SERIAL,0);entityData.define(CARGO,false);entityData.define(KIND,0);entityData.define(CARGO_ID,-1);entityData.define(DEPLOY,0F);}
    public void configure(int serial,boolean cargo){entityData.set(SERIAL,serial);entityData.set(CARGO,cargo);}
    public int serial(){return entityData.get(SERIAL);}
    public boolean carrying(){return entityData.get(CARGO);}
    public boolean groundCart(){return entityData.get(KIND)==1;}
    public void setGroundCart(){entityData.set(KIND,1);}
    public int cargoEntityId(){return entityData.get(CARGO_ID);}
    public void cargo(int id,boolean attached,float deployment){entityData.set(CARGO_ID,id);entityData.set(CARGO,attached);entityData.set(DEPLOY,Mth.clamp(deployment,0,1));}
    public float rig(float partial){return Mth.lerp(partial,oldRig,rig);}
    public float jaws(float partial){return Mth.lerp(partial,oldJaw,jaw);}
    @Override public AABB getBoundingBoxForCulling(){return groundCart()?new AABB(getX()-15,getY()-3,getZ()-17,getX()+15,getY()+9,getZ()+17):new AABB(getX()-74,getY()-85,getZ()-60,getX()+74,getY()+22,getZ()+60);}
    @Override public boolean shouldRenderAtSqrDistance(double distance){return distance<1600*1600;}
    @Override public void lerpTo(double x,double y,double z,float yaw,float pitch,int steps,boolean teleport)
    {tx=x;ty=y;tz=z;targetYaw=yaw;interpolation=3;}
    @Override public void tick()
    {
        super.tick();
        if(!level().isClientSide&&!groundCart()&&getTags().contains("seele_un_airlift")&&tickCount>200
                &&!com.projectseele.world.UNAirLiftR29.ownsAircraft((net.minecraft.server.level.ServerLevel)level(),getUUID())){discard();return;}
        if(level().isClientSide){oldRig=rig;oldJaw=jaw;rig=Mth.approach(rig,entityData.get(DEPLOY),.035F);jaw=Mth.approach(jaw,carrying()?0:1,.05F);}
        if(level().isClientSide&&interpolation>0)
        {
            setPos(getX()+(tx-getX())/interpolation,getY()+(ty-getY())/interpolation,getZ()+(tz-getZ())/interpolation);
            setYRot(getYRot()+Mth.wrapDegrees(targetYaw-getYRot())/interpolation);interpolation--;
        }
    }
    @Override protected void addAdditionalSaveData(CompoundTag tag){tag.putInt("UNSerial",serial());tag.putBoolean("Cargo",carrying());tag.putInt("Kind",entityData.get(KIND));tag.putFloat("Deploy",entityData.get(DEPLOY));}
    @Override protected void readAdditionalSaveData(CompoundTag tag){configure(tag.getInt("UNSerial"),tag.getBoolean("Cargo"));entityData.set(KIND,tag.getInt("Kind"));entityData.set(DEPLOY,tag.getFloat("Deploy"));}
    @Override public Packet<ClientGamePacketListener> getAddEntityPacket(){return NetworkHooks.getEntitySpawningPacket(this);}
    @Override public boolean isPickable(){return false;}
    @Override public boolean isPushable(){return false;}
}
