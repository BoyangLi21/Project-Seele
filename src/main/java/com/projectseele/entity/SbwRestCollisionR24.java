package com.projectseele.entity;

import com.projectseele.ProjectSeele;
import com.projectseele.world.CollisionChunkRevisionR24;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.chunk.*;
import net.minecraft.world.phys.*;
import org.joml.Vector3d;
import org.joml.Quaterniond;
import java.lang.ref.WeakReference;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.atomic.LongAdder;

/** Reuses an unchanged, zero-motion native collision result on static UN pads. */
public final class SbwRestCollisionR24
{
    public static final ThreadLocal<Boolean> VANILLA=ThreadLocal.withInitial(()->false);
    public static final LongAdder reused=new LongAdder(),verified=new LongAdder(),misses=new LongAdder();
    public static volatile double maximumError;public static volatile boolean rejected;
    private static final boolean PROFILE=System.getProperty("projectseele.regionalBuild","").startsWith("r24-");
    private static final java.util.concurrent.ConcurrentHashMap<String,LongAdder> REASONS=new java.util.concurrent.ConcurrentHashMap<>();
    private static void count(String reason){if(PROFILE)REASONS.computeIfAbsent(reason,k->new LongAdder()).increment();}
    public static Map<String,Long> diagnostics(){var result=new TreeMap<String,Long>();REASONS.forEach((k,v)->result.put(k,v.sum()));return result;}
    public static void forget(Entity entity){CACHE.get().remove(entity);QUERY.remove();}
    private static final boolean VERIFY="r24-sbw-rest-verify".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final boolean DISABLED=Boolean.getBoolean("projectseele.vanillaVehicleRest");
    private record Api(Method update,Method obb,Field stepping,Field blockCacheTick){}
    private record ObbApi(Method centre,Method extents,Method rotation){}
    private static final ClassValue<Api> API=new ClassValue<>()
    {
        protected Api computeValue(Class<?> type)
        {try{return new Api(type.getMethod("updateOBB"),type.getMethod("getCollisionOBB"),type.getField("ignoreEntityGroundCheckStepping"),type.getField("blockCollisionCacheTick"));}catch(Exception error){throw new IllegalStateException(error);}}
    };
    private static final ClassValue<ObbApi> OBB=new ClassValue<>()
    {
        protected ObbApi computeValue(Class<?> type)
        {try{return new ObbApi(type.getMethod("component1"),type.getMethod("component2"),type.getMethod("component3"));}catch(Exception error){throw new IllegalStateException(error);}}
    };
    private record Stamp(int x,int z,WeakReference<LevelChunk> chunk,long version){}
    private record Entry(Vec3 position,Vec3 input,AABB box,double[] obb,boolean stepping,List<Stamp> chunks,int tagEpoch,long expires,Vec3 result){}
    private static final class Query
    {
        final Entity entity;final Entry key;boolean staticOnly=true;Vec3 expected;
        Query(Entity entity,Entry key){this.entity=entity;this.key=key;}
    }
    private static final ThreadLocal<WeakHashMap<Entity,Entry>> CACHE=ThreadLocal.withInitial(WeakHashMap::new);
    private static final ThreadLocal<Query> QUERY=new ThreadLocal<>();
    public static void shapeFallback(){var q=QUERY.get();if(q!=null)q.staticOnly=false;}
    private static List<Stamp> stamps(Entity e,AABB box)
    {
        List<Stamp> result=new ArrayList<>();int x0=(int)Math.floor(box.minX-3)>>4,x1=(int)Math.floor(box.maxX+3)>>4,z0=(int)Math.floor(box.minZ-3)>>4,z1=(int)Math.floor(box.maxZ+3)>>4;
        if((x1-x0+1)*(z1-z0+1)>64)return null;
        for(int x=x0;x<=x1;x++)for(int z=z0;z<=z1;z++)
        {
            var chunk=e.level().getChunkSource().getChunk(x,z,ChunkStatus.FULL,false);
            if(!(chunk instanceof LevelChunk full))return null;
            result.add(new Stamp(x,z,new WeakReference<>(full),((CollisionChunkRevisionR24)full).seele$collisionRevision()));
        }
        return result;
    }
    private static boolean unchanged(Entity e,List<Stamp> stamps)
    {
        for(var s:stamps)
        {
            var chunk=e.level().getChunkSource().getChunk(s.x,s.z,ChunkStatus.FULL,false);
            if(chunk==null||chunk!=s.chunk.get()||((CollisionChunkRevisionR24)chunk).seele$collisionRevision()!=s.version)return false;
        }
        return true;
    }
    public static Vec3 before(Entity e,Vec3 input)
    {
        QUERY.remove();
        if(DISABLED||rejected||VANILLA.get()||SbwStaticShapesR24.VANILLA.get()||!SbwStaticShapesR24.vehicle(e))return null;
        count("calls");
        if(!e.onGround()||!e.isAlive()){count("not_grounded");return null;}
        if(e.isVehicle()||e.isPassenger()){count("occupied");return null;}
        if(e.isOnFire()||e.isInWaterOrBubble()){count("fluid_or_fire");return null;}
        if(input.x!=0||input.z!=0||input.y>=0||input.y<-.25){count("moving_input");return null;}
        if(!e.level().dimension().location().toString().equals("projectseele:geofront")||e.getX()<6000||e.getX()>7200||e.getZ()<-7400||e.getZ()>-5900
                ||net.minecraftforge.fml.ModList.get().isLoaded("valkyrienskies")){count("outside_scope");return null;}
        try
        {
            Api api=API.get(e.getClass());boolean stepping=api.stepping.getBoolean(null);
            api.update.invoke(e);Object obb=api.obb.invoke(e);if(obb==null)return null;var a=OBB.get(obb.getClass());
            var c=(Vector3d)a.centre.invoke(obb);var h=(Vector3d)a.extents.invoke(obb);var r=(Quaterniond)a.rotation.invoke(obb);
            double[] signature={c.x,c.y,c.z,h.x,h.y,h.z,r.x,r.y,r.z,r.w,e.getYRot(),e.getXRot()};AABB box=e.getBoundingBox();
            // The vanilla entity box can be smaller than the wings. Enclose
            // every rotated OBB corner, the complete downward sweep and the
            // native solver's border before checking changes or neighbours.
            double radius=h.length()*Math.max(1,r.lengthSquared());
            AABB search=new AABB(c.x-radius,c.y-radius,c.z-radius,c.x+radius,c.y+radius,c.z+radius).minmax(box).expandTowards(input).inflate(3);
            var neighbours=e.level().getEntities(e,search);
            if(!neighbours.isEmpty()){count("nearby_entity");if(PROFILE)count("neighbour/"+net.minecraft.core.registries.BuiltInRegistries.ENTITY_TYPE.getKey(neighbours.get(0).getType()));return null;}
            Entry old=CACHE.get().get(e);long now=e.level().getGameTime();
            if(PROFILE&&!e.level().isClientSide)
            {
                if(old==null)count("server_miss/no_entry");
                else if(old.expires<=now)count("server_miss/expired");
                else if(!old.position.equals(e.position()))count("server_miss/position");
                else if(!old.input.equals(input))count("server_miss/input");
                else if(old.stepping!=stepping)count("server_miss/step_mode");
                else if(!old.box.equals(box))count("server_miss/box");
                else if(!Arrays.equals(old.obb,signature))count("server_miss/obb");
                else if(!unchanged(e,old.chunks))count("server_miss/chunks");
            }
            if(old!=null&&old.expires>now&&old.tagEpoch==SbwStaticShapesR24.epoch()&&old.position.equals(e.position())&&old.input.equals(input)&&old.stepping==stepping
                    &&old.box.equals(box)&&Arrays.equals(old.obb,signature)&&unchanged(e,old.chunks))
            {
                reused.increment();
                count(e.level().isClientSide?"client_reuse":"server_reuse");
                if(VERIFY){var query=new Query(e,old);query.expected=old.result;QUERY.set(query);return null;}
                // Native vCollide consumes this one-shot flag and invalidates
                // its internal shape buffer even when motion resolves to zero.
                api.stepping.setBoolean(null,false);api.blockCacheTick.setInt(e,-1);
                return old.result;
            }
            List<Stamp> stamps=stamps(e,search);if(stamps==null)return null;
            misses.increment();QUERY.set(new Query(e,new Entry(e.position(),input,box,signature,stepping,stamps,SbwStaticShapesR24.epoch(),now+10,Vec3.ZERO)));return null;
        }
        catch(Exception error)
        {rejected=true;ProjectSeele.LOGGER.error("UN stationary collision cache disabled after interface mismatch",error);return null;}
    }
    public static void after(Entity e,Vec3 result)
    {
        Query query=QUERY.get();QUERY.remove();if(query==null||query.entity!=e)return;
        if(query.expected!=null)
        {
            double error=result.distanceTo(query.expected);maximumError=Math.max(maximumError,error);verified.increment();
            if(error>1e-9){rejected=true;ProjectSeele.LOGGER.error("UN collision cache rejected native comparison: {} expected={} actual={}",e,query.expected,result);}
            return;
        }
        if(query.staticOnly&&result.lengthSqr()<1e-20&&unchanged(e,query.key.chunks))CACHE.get().put(e,query.key);
        else count(!query.staticOnly?"contextual_shape":result.lengthSqr()>=1e-20?"nonzero_result":"changed_during_query");
    }
    private SbwRestCollisionR24(){}
}
