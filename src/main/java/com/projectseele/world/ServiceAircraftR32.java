package com.projectseele.world;

import com.projectseele.entity.*;
import net.minecraft.world.entity.Entity;
import com.projectseele.mixin.ServiceAircraftSectionsR32Accessor;
import com.projectseele.mixin.ServiceAircraftWorldR32Accessor;
import net.minecraft.server.level.ServerLevel;
import java.lang.ref.WeakReference;
import java.util.*;

/** A fast service aircraft can cross a loaded but not yet visible entity section.
 * ServerLevel.getEntity(UUID) indexes tracked entities only; keep the existing
 * owned object through that transition instead of losing the flight controller. */
public final class ServiceAircraftR32
{
    private static final Map<ServerLevel,Map<UUID,WeakReference<Entity>>> CACHE=new WeakHashMap<>();
    public static UNTransportEntity find(ServerLevel level,UUID id)
    {return resolve(level,id) instanceof UNTransportEntity aircraft?aircraft:null;}
    public static EvaUnit01Entity payload(ServerLevel level,UUID id)
    {return resolve(level,id) instanceof EvaUnit01Entity eva?eva:null;}
    public static EntryPlugCarrierEntity capsule(ServerLevel level,UUID id)
    {return resolve(level,id) instanceof EntryPlugCarrierEntity plug?plug:null;}
    private static Entity resolve(ServerLevel level,UUID id)
    {
        if(id==null)return null;
        var cache=CACHE.computeIfAbsent(level,k->new HashMap<>());
        var ref=cache.get(id);var plane=ref==null?null:ref.get();
        if(plane!=null&&!plane.isRemoved()&&plane.level()==level)return plane;
        var tracked=level.getEntity(id);
        if(tracked!=null)plane=tracked;
        else
        {
            plane=null;
            var manager=((ServiceAircraftWorldR32Accessor)level).seele$entityManagerR32();
            if(manager.isLoaded(id))
            {
                var sections=((ServiceAircraftSectionsR32Accessor)manager).seele$sectionsR32();
                for(long chunk:sections.getAllChunksWithExistingSections())
                {
                    var found=sections.getExistingSectionsInChunk(chunk).flatMap(s->s.getEntities())
                            .filter(e->id.equals(e.getUUID())&&!e.isRemoved()).findFirst().orElse(null);
                    if(found!=null){plane=found;break;}
                }
            }
        }
        if(plane!=null)cache.put(id,new WeakReference<>(plane));else cache.remove(id);
        if(cache.size()>16)cache.entrySet().removeIf(e->{var value=e.getValue().get();return value==null||value.isRemoved();});
        return plane;
    }
    private ServiceAircraftR32(){}
}
