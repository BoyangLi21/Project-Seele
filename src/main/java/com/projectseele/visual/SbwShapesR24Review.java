package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.SbwStaticShapesR24;
import com.projectseele.entity.SbwRestCollisionR24;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.level.*;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.*;
import net.minecraft.world.phys.shapes.*;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Compare actual parked vehicle queries with the untouched native collision path. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class SbwShapesR24Review
{
    private static final boolean ENABLED="r24-sbw-shapes".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r24_sbw_shape_review",Comparator.comparingLong(ChunkPos::toLong),120);
    private static final JsonArray results=new JsonArray();private static List<JsonObject> cases;
    private static int age,index,timer,fastShapes,fallbacks,pairs;private static boolean done;
    private static long baselineNanos,fastNanos;private static Path world;
    private static final JsonArray wakeChecks=new JsonArray();
    private static boolean wakesDone;
    private static Vec3 collision(Entity entity,Vec3 movement,boolean original,boolean stepping) throws Exception
    {
        var field=entity.getClass().getField("ignoreEntityGroundCheckStepping");boolean prior=field.getBoolean(null);
        try
        {
            field.setBoolean(null,stepping);SbwRestCollisionR24.VANILLA.set(original);
            return (Vec3)entity.getClass().getMethod("vCollide",Vec3.class).invoke(entity,movement);
        }
        finally{field.setBoolean(null,prior);SbwRestCollisionR24.VANILLA.remove();}
    }
    private static void compareWake(Entity vehicle,Vec3 input,String name,boolean stepping,boolean requireReuse) throws Exception
    {
        Vec3 expected=collision(vehicle,input,true,stepping);long before=SbwRestCollisionR24.reused.sum();
        Vec3 actual=collision(vehicle,input,false,stepping);boolean reused=SbwRestCollisionR24.reused.sum()>before;
        if(expected.distanceTo(actual)>1e-9||reused!=requireReuse)throw new IllegalStateException(name+" native="+expected+" cached="+actual+" reused="+reused+" wanted="+requireReuse);
        var row=new JsonObject();row.addProperty("case",name);row.addProperty("error",expected.distanceTo(actual));row.addProperty("reused",reused);wakeChecks.add(row);
    }
    private static boolean warm(Entity vehicle,Vec3 input,boolean stepping) throws Exception
    {
        SbwRestCollisionR24.forget(vehicle);collision(vehicle,input,false,stepping);long n=SbwRestCollisionR24.reused.sum();collision(vehicle,input,false,stepping);
        return SbwRestCollisionR24.reused.sum()>n;
    }
    private static void checkWake(ServerLevel level,Entity vehicle) throws Exception
    {
        Vec3 input=new Vec3(0,-.08,0);if(wakesDone||!warm(vehicle,input,false))return;
        Vec3 position=vehicle.position();float yaw=vehicle.getYRot();boolean ground=vehicle.onGround();
        BlockPos change=vehicle.blockPosition().below();var state=level.getBlockState(change);
        if(level.getBlockEntity(change)!=null||state.getBlock().getClass()!=net.minecraft.world.level.block.Block.class)return;
        var passenger=new net.minecraft.world.entity.decoration.ArmorStand(level,position.x,position.y+2,position.z);
        var beforeNbt=vehicle.saveWithoutId(new net.minecraft.nbt.CompoundTag());
        try
        {
            compareWake(vehicle,input,"unchanged_rest",false,true);
            if(!warm(vehicle,input,true))throw new IllegalStateException("Native ground probe did not cache");
            compareWake(vehicle,input,"unchanged_ground_probe",true,true);
            warm(vehicle,input,false);compareWake(vehicle,input,"one_shot_step_mode",true,false);
            warm(vehicle,input,false);level.setBlock(change,state.is(net.minecraft.world.level.block.Blocks.STONE)?net.minecraft.world.level.block.Blocks.QUARTZ_BLOCK.defaultBlockState():net.minecraft.world.level.block.Blocks.STONE.defaultBlockState(),3);
            compareWake(vehicle,input,"changed_support_chunk",false,false);level.setBlock(change,state,3);
            warm(vehicle,input,false);vehicle.setYRot(yaw+15);compareWake(vehicle,input,"turned_vehicle",false,false);vehicle.setYRot(yaw);
            warm(vehicle,input,false);compareWake(vehicle,new Vec3(.2,-.08,.1),"drive_forward",false,false);
            warm(vehicle,input,false);compareWake(vehicle,new Vec3(-.2,-.08,-.1),"drive_reverse",false,false);
            warm(vehicle,input,false);compareWake(vehicle,new Vec3(0,.5,0),"takeoff",false,false);
            warm(vehicle,input,false);vehicle.setOnGround(false);compareWake(vehicle,input,"airborne",false,false);vehicle.setOnGround(ground);
            warm(vehicle,input,false);vehicle.setPos(position.add(.25,0,0));compareWake(vehicle,input,"translated_vehicle",false,false);vehicle.setPos(position);
            warm(vehicle,input,false);SbwStaticShapesR24.reload(null);compareWake(vehicle,input,"tag_reload",false,false);
            warm(vehicle,input,false);if(!passenger.startRiding(vehicle,true))throw new IllegalStateException("Native passenger test could not board");
            compareWake(vehicle,input,"boarded_vehicle",false,false);passenger.stopRiding();
            warm(vehicle,input,false);passenger.setPos(position.add(0,2,0));if(!level.addFreshEntity(passenger))throw new IllegalStateException("Native near-entity test not attached");
            compareWake(vehicle,input,"nearby_entity",false,false);passenger.discard();
            wakesDone=true;
        }
        finally
        {
            passenger.stopRiding();passenger.discard();vehicle.setPos(position);vehicle.setYRot(yaw);vehicle.setOnGround(ground);level.setBlock(change,state,3);SbwRestCollisionR24.forget(vehicle);
            vehicle.getClass().getMethod("updateOBB").invoke(vehicle);
            if(!beforeNbt.equals(vehicle.saveWithoutId(new net.minecraft.nbt.CompoundTag())))throw new IllegalStateException("Wake test did not restore original vehicle NBT");
        }
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END||++age<100)return;
        var server=event.getServer();var level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
        try
        {
            if(cases==null)
            {
                world=server.getWorldPath(LevelResource.ROOT).normalize();if(!world.getFileName().toString().equals("SEELE_R24_TV_REVIEW"))throw new IllegalStateException("Wrong shape review world");
                var rows=JsonParser.parseString(Files.readString(world.resolve("military_readiness_r23.json"))).getAsJsonObject().getAsJsonArray("vehicles");
                var unique=new LinkedHashMap<String,JsonObject>();for(var item:rows){var row=item.getAsJsonObject();unique.putIfAbsent(row.get("id").getAsString(),row);}cases=List.copyOf(unique.values());
            }
            level.resetEmptyTime();if(age>7000)throw new IllegalStateException("SBW shape review timeout");
            if(index==cases.size()){finish(server,"");return;}
            var row=cases.get(index);var p=row.getAsJsonArray("position");Vec3 point=new Vec3(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble());
            if(timer++%30==0)
            {
                var c=new ChunkPos(BlockPos.containing(point));for(int x=c.x-2;x<=c.x+2;x++)for(int z=c.z-2;z<=c.z+2;z++)
                {var q=new ChunkPos(x,z);level.getChunkSource().addRegionTicket(TICKET,q,2,q);level.getChunk(x,z);}
            }
            if(timer<65)return;
            String type=row.get("id").getAsString();var matching=level.getEntitiesOfClass(Entity.class,new AABB(point,point).inflate(12),e->BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).toString().equals(type)&&e.getTags().contains("seele_r23_readiness"));
            if(matching.isEmpty()){if(timer>250)throw new IllegalStateException("Original vehicle not attached "+type);return;}
            Entity vehicle=matching.stream().min(Comparator.comparingDouble(e->e.position().distanceToSqr(point))).orElseThrow();
            var context=CollisionContext.of(vehicle);var bounds=vehicle.getBoundingBox().inflate(2);int tested=0;
            for(var pos:BlockPos.betweenClosed(BlockPos.containing(bounds.minX,bounds.minY,bounds.minZ),BlockPos.containing(bounds.maxX,bounds.maxY,bounds.maxZ)))
            {
                var state=level.getBlockState(pos);var fast=SbwStaticShapesR24.shape(state,context);
                if(fast==null){fallbacks++;continue;}
                var original=state.getCollisionShape(level,pos,context);
                if(Shapes.joinIsNotEmpty(original,fast,BooleanOp.NOT_SAME))throw new IllegalStateException("Changed vehicle block shape at "+pos+" "+state);
                fastShapes++;tested++;
            }
            var method=vehicle.getClass().getMethod("vCollide",Vec3.class);double maximum=0;
            var position=vehicle.position();var motion=vehicle.getDeltaMovement();
            for(var vector:List.of(new Vec3(0,-.08,0),new Vec3(.2,-.08,.1),new Vec3(-.2,-.08,.1),new Vec3(0,.5,0),new Vec3(1,-.01,0),new Vec3(0,-1,0)))
            {
                Vec3 a=null,b=null;
                for(int n=0;n<4;n++)for(boolean original:n%2==0?new boolean[]{true,false}:new boolean[]{false,true})
                {
                    SbwStaticShapesR24.VANILLA.set(original);long t=System.nanoTime();var value=(Vec3)method.invoke(vehicle,vector);long elapsed=System.nanoTime()-t;
                    if(original){a=value;baselineNanos+=elapsed;}else{b=value;fastNanos+=elapsed;}
                }
                SbwStaticShapesR24.VANILLA.remove();double error=a.distanceTo(b);maximum=Math.max(maximum,error);pairs++;
                if(error>1e-9)throw new IllegalStateException("Changed native collision result "+type+" "+vector+" "+a+" vs "+b);
            }
            if(!position.equals(vehicle.position())||!motion.equals(vehicle.getDeltaMovement()))throw new IllegalStateException("Read-only collision review moved vehicle");
            SbwStaticShapesR24.reload(null);var q=BlockPos.containing(point.add(0,-1,0));var state=level.getBlockState(q);var refreshed=SbwStaticShapesR24.shape(state,context);
            if(refreshed!=null&&Shapes.joinIsNotEmpty(refreshed,state.getCollisionShape(level,q,context),BooleanOp.NOT_SAME))throw new IllegalStateException("Cache invalidation mismatch");
            var result=new JsonObject();result.addProperty("vehicle",type);result.addProperty("uuid",vehicle.getUUID().toString());result.addProperty("shape_comparisons",tested);result.addProperty("maximum_motion_error",maximum);results.add(result);
            checkWake(level,vehicle);
            ProjectSeele.LOGGER.info("R24 SBW native shape/collision compare {} shapes={} error={}",type,tested,maximum);index++;timer=0;
        }
        catch(Exception error){ProjectSeele.LOGGER.error("R24 SBW collision comparison failed",error);finish(server,error.toString());}
    }
    private static void finish(net.minecraft.server.MinecraftServer server,String error)
    {
        if(error.isEmpty()&&!wakesDone)error="No stationary vehicle completed wake/invalidation probes";
        SbwStaticShapesR24.VANILLA.remove();SbwRestCollisionR24.VANILLA.remove();var report=new JsonObject();report.addProperty("passed",error.isEmpty());report.addProperty("error",error);report.add("vehicles",results);report.add("wake_checks",wakeChecks);report.addProperty("wake_restored_original_vehicle_nbt",wakesDone);
        report.addProperty("fast_shapes_equal",fastShapes);report.addProperty("contextual_shape_fallbacks",fallbacks);report.addProperty("native_motion_pairs",pairs);report.addProperty("baseline_ns",baselineNanos);report.addProperty("fast_ns",fastNanos);
        report.addProperty("collision_query_speedup",baselineNanos/(double)Math.max(1,fastNanos));report.addProperty("world_blocks_left_changed",0);report.addProperty("temporary_support_swap_restored_same_tick",wakesDone);
        try{Files.writeString(world.resolve("r24_sbw_shape_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception e){ProjectSeele.LOGGER.error("Could not write shape review",e);}done=true;server.halt(false);
    }
    private SbwShapesR24Review(){}
}
