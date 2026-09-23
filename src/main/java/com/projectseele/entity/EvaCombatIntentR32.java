package com.projectseele.entity;

import com.projectseele.util.WeakIdentityMap;
import net.minecraft.world.entity.LivingEntity;
import java.util.UUID;

/** One recent intent through a light hit reaction, tied to the current seated pilot. */
public final class EvaCombatIntentR32
{
    private record Intent(UUID pilot,int action,long until){}
    private static final WeakIdentityMap<EvaUnit01Entity,Intent> PENDING=new WeakIdentityMap<>();
    public static void offer(EvaUnit01Entity eva,LivingEntity pilot,int action)
    {
        var beat=CombatFeelR31.beat(eva);
        if(!eva.level().isClientSide&&pilot==eva.getPilotEntity()&&beat!=null&&beat.kind()==CombatFeelR31.STAGGER)
            PENDING.put(eva,new Intent(pilot.getUUID(),action,eva.level().getGameTime()+8));
    }
    public static void tick(EvaUnit01Entity eva)
    {
        if(eva.level().isClientSide)return;var pending=PENDING.get(eva);if(pending==null)return;
        var pilot=eva.getPilotEntity();
        if(eva.level().getGameTime()>pending.until||pilot==null||!pilot.getUUID().equals(pending.pilot)||eva.isPilotControlLocked()||EvaShutdownR30.disabled(eva))
        {PENDING.remove(eva);return;}
        if(CombatFeelR31.restrained(eva))return;
        PENDING.remove(eva);eva.replayCombatIntentR32(pilot,pending.action);
    }
    private EvaCombatIntentR32(){}
}
