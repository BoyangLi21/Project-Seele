package com.projectseele.client;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.entity.Entity;
import net.minecraft.resources.ResourceLocation;
import com.projectseele.entity.SbwStaticShapesR24;
import java.util.*;

/** Avoid reloading identical, unticked remote copies of parked UN vehicles. */
public final class SbwPhantomLoadR24
{
    private static final boolean REVIEW=System.getProperty("projectseele.regionalBuild","").startsWith("r24-");
    private static final boolean VERIFY="r24-sbw-phantom-verify".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final boolean DISABLED=Boolean.getBoolean("projectseele.vanillaPhantomLoads");
    private record Entry(CompoundTag tag,int tick,long expires){}
    private static final WeakHashMap<Entity,Entry> previous=new WeakHashMap<>();
    private static final Set<Entity> pending=Collections.newSetFromMap(new IdentityHashMap<>());
    private static final Map<String,Long> changes=new TreeMap<>();
    private static long calls,identical,nanos,reused,verified;private static boolean replaying,rejected;
    public static void load(Entity entity,CompoundTag tag)
    {
        if(replaying||DISABLED||rejected||!SbwStaticShapesR24.vehicle(entity)||!entity.level().isClientSide||entity.level().getEntity(entity.getId())==entity)
        {entity.load(tag);return;}
        Entry old=previous.get(entity);boolean equal=old!=null&&tag.equals(old.tag);calls++;
        if(equal)identical++;
        else if(REVIEW&&old!=null)
        {
            Set<String> keys=new HashSet<>(old.tag.getAllKeys());keys.addAll(tag.getAllKeys());
            for(String key:keys)if(!Objects.equals(old.tag.get(key),tag.get(key)))changes.merge(key,1L,Long::sum);
        }
        long now=System.nanoTime();
        if(equal&&entity.tickCount==old.tick&&now<old.expires&&entity.isAlive()&&!entity.isVehicle()&&!entity.isPassenger()
                &&entity.level().dimension().location().toString().equals("projectseele:geofront")
                &&entity.getX()>=6000&&entity.getX()<=7200&&entity.getZ()>=-7400&&entity.getZ()<=-5900)
        {reused++;if(VERIFY)pending.add(entity);return;}
        long began=System.nanoTime();entity.load(tag);nanos+=System.nanoTime()-began;
        previous.put(entity,new Entry(tag.copy(),entity.tickCount,now+1_000_000_000L));
    }
    private static CompoundTag state(Entity entity)
    {
        var tag=entity.saveWithoutId(new CompoundTag());
        double[] pose={entity.xOld,entity.yOld,entity.zOld,entity.xo,entity.yo,entity.zo,entity.yRotO,entity.xRotO};
        for(int i=0;i<pose.length;i++)tag.putDouble("R24OldPose"+i,pose[i]);
        return tag;
    }
    public static void afterPacket(ResourceLocation dimension,List<?> packet)
    {
        if(!VERIFY||replaying||pending.isEmpty())return;
        var samples=new IdentityHashMap<Entity,CompoundTag>();for(var entity:pending)samples.put(entity,state(entity));pending.clear();
        try
        {
            // Replay the real complete handler, including ammo, pose, sound
            // and packet metadata, then compare the skipped-load result.
            replaying=true;Class.forName("com.atsuishio.superbwarfare.client.ClientSyncedEntityHandler")
                    .getMethod("syncWorldRender",ResourceLocation.class,List.class).invoke(null,dimension,packet);
            for(var entry:samples.entrySet())
            {
                var actual=state(entry.getKey());if(!actual.equals(entry.getValue()))
                {
                    var keys=new TreeSet<>(actual.getAllKeys());keys.addAll(entry.getValue().getAllKeys());keys.removeIf(k->Objects.equals(actual.get(k),entry.getValue().get(k)));
                    throw new IllegalStateException("Remote vehicle native state differs in "+keys);
                }
                verified++;
            }
        }
        catch(Exception error){rejected=true;com.projectseele.ProjectSeele.LOGGER.error("Remote copy cache rejected native handler comparison",error);}
        finally{replaying=false;}
    }
    public static Map<String,Object> diagnostics(){return Map.of("loads",calls,"identical_payloads",identical,"native_load_ns",nanos,"changed_keys",changes,"reused",reused,"verified",verified,"rejected",rejected);}
    private SbwPhantomLoadR24(){}
}
