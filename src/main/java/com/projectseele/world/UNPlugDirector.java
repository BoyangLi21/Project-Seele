package com.projectseele.world;

import com.projectseele.entity.*;
import com.projectseele.registry.ModEntities;
import com.projectseele.ProjectSeele;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.entity.Entity;
import java.util.Map;
import java.util.HashMap;
import java.util.UUID;

/** A fourth persistent capsule, owned by the UN airframe rather than a NERV fleet slot. */
public final class UNPlugDirector
{
    private static final Vec3 HOME=new Vec3(6442.5,77,-6205.5);
    private static final Map<UUID,UUID> CRANES=new HashMap<>();
    public static EntryPlugCarrierEntity capsule(EvaPrototypeEntity eva)
    {
        CompoundTag data=eva.getPersistentData();
        if(!(eva.level() instanceof ServerLevel level)||!data.hasUUID("UNPlug"))return null;
        Entity e=level.getEntity(data.getUUID("UNPlug"));return e instanceof EntryPlugCarrierEntity p?p:null;
    }
    public static boolean atDock(EvaPrototypeEntity eva)
    {
        var d=eva.getPersistentData();return d.contains("UNHomeX")&&eva.position().distanceTo(new Vec3(d.getDouble("UNHomeX"),d.getDouble("UNHomeY"),d.getDouble("UNHomeZ")))<4;
    }
    public static RigidTransform dock(EvaPrototypeEntity eva)
    {
        var d=eva.getPersistentData();double yaw=Math.toRadians(d.getFloat("UNHomeYaw"));Vec3 rear=new Vec3(Math.sin(yaw),0,-Math.cos(yaw));
        Vec3 centre=new Vec3(d.getDouble("UNHomeX"),d.getDouble("UNHomeY"),d.getDouble("UNHomeZ"));
        return EntryPlugKinematics.dockTransform(eva,centre.add(rear.scale(12)).add(0,51.6,0));
    }
    public static void tick(EvaPrototypeEntity eva)
    {
        if(!(eva.level() instanceof ServerLevel level))return;
        CompoundTag d=eva.getPersistentData();EntryPlugCarrierEntity plug=capsule(eva);
        if(!d.hasUUID("UNPlug"))
        {
            boolean lab=System.getProperty("projectseele.regionalBuild","").equals("r11-mechanics")&&d.getBoolean("UNMechanicsLab");
            if(!lab&&(!eva.isInsideTestHangar()||eva.position().distanceTo(HOME)>4))return;
            d.putDouble("UNHomeX",eva.getX());d.putDouble("UNHomeY",eva.getY());d.putDouble("UNHomeZ",eva.getZ());d.putFloat("UNHomeYaw",eva.getYRot());
            plug=ModEntities.ENTRY_PLUG_CARRIER.get().create(level);if(plug==null)return;
            plug.assignIndependentEva(eva);plug.setCanonicalTransform(dock(eva));
            if(!level.addFreshEntity(plug))return;d.putUUID("UNPlug",plug.getUUID());
            ProjectSeele.LOGGER.info("EVA-UN dedicated capsule commissioned: eva={} plug={}",eva.getUUID(),plug.getUUID());
        }
        if(plug==null)return; // An unloaded saved capsule is never replaced.
        plug.assignIndependentEva(eva);
        int stage=plug.getInsertionStage(),tick=d.getInt("UNSequenceTicks");
        if(stage==EntryPlugCarrierEntity.STAGE_SUSPENDED)
        {
            if(atDock(eva)){plug.setCanonicalTransform(dock(eva));hoist(level,eva,plug);}
            d.putInt("UNSequenceTicks",0);return;
        }
        if(stage==EntryPlugCarrierEntity.STAGE_OCCUPIED&&atDock(eva))
        {
            if(eva.isNervLogisticsLocked())return;
            plug.sealCabin();d.putInt("UNSequenceTicks",++tick);plug.setCabinSequenceProgress(Math.min(30,tick));
            if(tick>=36&&plug.isHatchFullySealed())
            {
                RigidTransform previous=dock(eva);boolean clear=true;
                for(int i=1;i<=80;i++){RigidTransform next=EntryPlugKinematics.insertionTransform(eva,dock(eva),i/80D);if(!clear(level,eva,plug,previous,next)){clear=false;break;}previous=next;}
                if(clear){plug.transitionInsertionStage(stage,EntryPlugCarrierEntity.STAGE_INSERTING);d.putInt("UNSequenceTicks",0);plug.clearInsertionAbortRequest();}
                else {d.putInt("UNSequenceTicks",0);plug.getFirstPassenger().stopRiding();ProjectSeele.LOGGER.warn("EVA-UN crane preflight obstructed; capsule held at dock");}
            }
            hoist(level,eva,plug);return;
        }
        if(stage==EntryPlugCarrierEntity.STAGE_INSERTING)
        {
            if(!plug.isVehicle()||plug.isInsertionAbortRequested())
            {plug.transitionInsertionStage(stage,EntryPlugCarrierEntity.STAGE_ABORT_RETURNING);return;}
            EvaDorsalMechanism.prepare(eva,++tick);d.putInt("UNSequenceTicks",tick);
            double p=EvaDorsalMechanism.smooth((tick-36)/154F);RigidTransform next=EntryPlugKinematics.insertionTransform(eva,dock(eva),p);
            if(!clear(level,eva,plug,plug.getCanonicalTransform(),next)){plug.transitionInsertionStage(stage,EntryPlugCarrierEntity.STAGE_ABORT_RETURNING);return;}
            plug.setCanonicalTransform(next);plug.setInsertionProgress((int)Math.round(p*100));plug.setCabinSequenceProgress(30+(int)Math.round(40*p));hoist(level,eva,plug);
            if(tick>=190&&plug.lockToEva(eva)&&eva.bindEntryPlug(plug,70))d.putInt("UNSequenceTicks",0);
            return;
        }
        if(stage==EntryPlugCarrierEntity.STAGE_LOCKED&&atDock(eva))
        {
            if(tick<60){d.putInt("UNSequenceTicks",++tick);EvaDorsalMechanism.seal(eva,tick);}
            hoist(level,eva,plug,Math.min(1,tick/48D));
            return;
        }
        if(stage==EntryPlugCarrierEntity.STAGE_ABORT_RETURNING)
        {
            int p=Math.max(0,plug.getInsertionProgress()-1);RigidTransform next=EntryPlugKinematics.insertionTransform(eva,dock(eva),p/100D);
            if(!clear(level,eva,plug,plug.getCanonicalTransform(),next))return;
            plug.setCanonicalTransform(next);plug.setInsertionProgress(p);float hold=EvaDorsalMechanism.smooth(p/28F);EvaDorsalMechanism.set(eva,Math.min(hold,EvaDorsalMechanism.open(eva)),Math.min(hold,EvaDorsalMechanism.bow(eva)));hoist(level,eva,plug);
            if(p==0){plug.transitionInsertionStage(stage,EntryPlugCarrierEntity.STAGE_ABORT_DOCKED);plug.setCabinRecoveryProgress(0);}
            return;
        }
        if(stage==EntryPlugCarrierEntity.STAGE_ABORT_DOCKED)
        {
            plug.transitionInsertionStage(stage,plug.isVehicle()?EntryPlugCarrierEntity.STAGE_OCCUPIED:EntryPlugCarrierEntity.STAGE_SUSPENDED);
            // A deliberate abort stays at the bridge until the pilot leaves and boards again.
            if(plug.isVehicle())plug.getFirstPassenger().stopRiding();d.putInt("UNSequenceTicks",0);
        }
    }
    public static void extract(EntryPlugCarrierEntity plug,int ticks)
    {
        if(!(plug.getLinkedEva() instanceof EvaPrototypeEntity eva)||!(eva.level() instanceof ServerLevel level))return;
        if(ticks<=36)EvaDorsalMechanism.prepare(eva,ticks);else if(ticks>=137)EvaDorsalMechanism.seal(eva,ticks-137);
        double p=1-Math.max(0,Math.min(1,(ticks-36)/105D));RigidTransform next=EntryPlugKinematics.insertionTransform(eva,dock(eva),p);
        if(!clear(level,eva,plug,plug.getCanonicalTransform(),next))return;
        plug.setCanonicalTransform(next);plug.setInsertionProgress((int)Math.round(p*100));plug.setCabinRecoveryProgress((int)Math.round(p*70));hoist(level,eva,plug,ticks<=36?1-EvaDorsalMechanism.smooth(ticks/36F):0);
        if(ticks>=197)
        {
            plug.transitionInsertionStage(EntryPlugCarrierEntity.STAGE_EJECTING,EntryPlugCarrierEntity.STAGE_SUSPENDED);
            if(plug.isVehicle())plug.getFirstPassenger().stopRiding();plug.openCabin();eva.getPersistentData().putInt("UNSequenceTicks",0);
        }
    }
    private static boolean clear(ServerLevel level,EvaPrototypeEntity eva,EntryPlugCarrierEntity plug,RigidTransform before,RigidTransform after)
    {
        for(int i=1;i<=4;i++)
        {
            AABB bounds=EntryPlugKinematics.worldBounds(before.interpolate(after,i/4D),EntryPlugKinematics.BODY_OBB_CENTRE_P,EntryPlugKinematics.BODY_OBB_HALF_EXTENTS).deflate(.06);
            if(level.getBlockCollisions(plug,bounds).iterator().hasNext())return false;
            if(!level.getEntities(plug,bounds,e->e!=eva&&e.isPickable()&&!plug.hasPassenger(e)).isEmpty())return false;
        }
        return true;
    }
    private static void hoist(ServerLevel level,EvaPrototypeEntity eva,EntryPlugCarrierEntity plug)
    {hoist(level,eva,plug,0);}
    private static void hoist(ServerLevel level,EvaPrototypeEntity eva,EntryPlugCarrierEntity plug,double raised)
    {
        NervCarrierPlatformEntity crane=null;UUID id=CRANES.get(eva.getUUID());if(id!=null&&level.getEntity(id) instanceof NervCarrierPlatformEntity c)crane=c;
        Vec3 eye=plug.getCanonicalTransform().transformPoint(EntryPlugKinematics.CRANE_ATTACHMENT_P);double y=eva.getPersistentData().getDouble("UNHomeY")+73;
        double lower=eye.y+(y-2-eye.y)*Math.max(0,Math.min(1,raised));
        if(crane==null){crane=ModEntities.NERV_CARRIER_PLATFORM.get().create(level);if(crane==null)return;crane.configurePlugCrane(1,lower-y);crane.moveControlled(eye.x,y,eye.z);crane.linkCranePlug(plug);if(!level.addFreshEntity(crane))return;CRANES.put(eva.getUUID(),crane.getUUID());}
        crane.configurePlugCrane(1,lower-y);crane.moveControlled(eye.x,y,eye.z);crane.linkCranePlug(plug);
    }
    private UNPlugDirector() {}
}
