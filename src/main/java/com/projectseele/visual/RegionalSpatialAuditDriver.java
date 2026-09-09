package com.projectseele.visual;

import com.google.gson.*;
import com.mojang.authlib.GameProfile;
import com.projectseele.ProjectSeele;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.EmptyBlockGetter;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Measures native voxel shapes and actual player collision movement; no world blocks are authored. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class RegionalSpatialAuditDriver
{
    private static final boolean COMBINED="r10-world".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final boolean ENABLED=COMBINED||"collision-audit".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final TicketType<ChunkPos> TICKET=TicketType.create("projectseele_spatial_audit",Comparator.comparingLong(ChunkPos::toLong),100);
    private static final Gson GSON=new GsonBuilder().setPrettyPrinting().create();
    private static final JsonArray RESULTS=new JsonArray();
    private static JsonArray cases;
    private static FakePlayer player;
    private static int age,index,wait,steps,stalled,settled,stepLimit;
    public static volatile boolean done;
    private static boolean positioned;
    private static Vec3 start,end;
    private static JsonArray route;
    private static int waypoint;
    private static double distance,maxRise,fallSpeed;
    private static final JsonArray TRACE=new JsonArray();
    private static ServerLevel activeLevel;
    private static final Map<BlockPos,BlockState> RESTORE=new LinkedHashMap<>();

    @SuppressWarnings({"rawtypes","unchecked"})
    private static BlockState parse(String text)
    {
        int bracket=text.indexOf('[');String name=bracket<0?text:text.substring(0,bracket);
        ResourceLocation id=new ResourceLocation(name);
        if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalStateException("Unknown block "+text);
        var block=BuiltInRegistries.BLOCK.get(id);BlockState state=block.defaultBlockState();
        if(bracket>=0)for(String property:text.substring(bracket+1,text.length()-1).split(","))
        {
            String[] pair=property.split("=");Property key=block.getStateDefinition().getProperty(pair[0]);
            if(key==null)throw new IllegalStateException("Unknown property "+text);
            state=state.setValue(key,(Comparable)key.getValue(pair[1]).orElseThrow());
        }
        return state;
    }
    private static Vec3 vector(JsonArray a){return new Vec3(a.get(0).getAsDouble(),a.get(1).getAsDouble(),a.get(2).getAsDouble());}
    private static JsonArray position(Vec3 p){JsonArray a=new JsonArray();a.add(p.x);a.add(p.y);a.add(p.z);return a;}

    @SubscribeEvent
    public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("Wrong quality audit world");
        ServerLevel level=server.getLevel(FacilitySchemaV2.DIMENSION);
        try
        {
            if(++age<100)return;
            if(cases==null)
            {
                player=FakePlayerFactory.get(level,new GameProfile(UUID.fromString("9bc3f5d1-2e80-4a10-8986-965c47c87e61"),"[SEELE audit]"));
                player.setGameMode(GameType.SURVIVAL);player.getAbilities().flying=false;player.noPhysics=false;
                player.setMaxUpStep(.6F);
                var stepAttribute=player.getAttribute(net.minecraftforge.common.ForgeMod.STEP_HEIGHT_ADDITION.get());
                if(stepAttribute!=null)stepAttribute.setBaseValue(0);
                JsonObject shapes=new JsonObject();
                for(JsonElement e:JsonParser.parseString(Files.readString(world.resolve("regional_states.json"))).getAsJsonArray())
                {
                    String key=e.getAsString();BlockState state=parse(key);JsonArray boxes=new JsonArray();
                    for(var b:state.getCollisionShape(EmptyBlockGetter.INSTANCE,BlockPos.ZERO,CollisionContext.of(player)).toAabbs())
                    {JsonArray box=new JsonArray();for(double v:new double[]{b.minX,b.minY,b.minZ,b.maxX,b.maxY,b.maxZ})box.add(v);boxes.add(box);}
                    shapes.add(key,boxes);
                }
                Files.writeString(world.resolve("native_collision_shapes.json"),GSON.toJson(shapes));
                Path survey=world.resolve("quality_survey_points.json");
                if(Files.exists(survey))
                {
                    JsonArray heights=new JsonArray();
                    for(JsonElement e:JsonParser.parseString(Files.readString(survey)).getAsJsonArray())
                    {
                        JsonArray point=e.getAsJsonArray();int x=point.get(0).getAsInt(),z=point.get(1).getAsInt();
                        int y=level.getChunkSource().getGenerator().getBaseHeight(x,z,net.minecraft.world.level.levelgen.Heightmap.Types.OCEAN_FLOOR_WG,level,level.getChunkSource().randomState());
                        JsonArray row=new JsonArray();row.add(x);row.add(y);row.add(z);heights.add(row);
                    }
                    Files.writeString(world.resolve("quality_terrain_survey.json"),GSON.toJson(heights));
                }
                cases=JsonParser.parseString(Files.readString(world.resolve("quality_walk_cases.json"))).getAsJsonArray();
                ProjectSeele.LOGGER.info("SPATIAL NATIVE shapes={} cases={} playerStep={}",shapes.size(),cases.size(),player.maxUpStep());
            }
            if(Files.exists(world.resolve("regional_stop_requested")))
            {Files.writeString(world.resolve("quality_native_walk_results.json"),GSON.toJson(RESULTS));Files.delete(world.resolve("regional_stop_requested"));done=true;server.halt(false);return;}
            if(index==cases.size())
            {
                Files.writeString(world.resolve("quality_native_walk_results.json"),GSON.toJson(RESULTS));
                ProjectSeele.LOGGER.info("SPATIAL NATIVE COMPLETE cases={}",RESULTS.size());done=true;if(!COMBINED)server.halt(false);return;
            }
            JsonObject test=cases.get(index).getAsJsonObject();
            if(wait==0)
            {
                route=test.has("path")?test.getAsJsonArray("path"):new JsonArray();
                if(!test.has("path")){route.add(test.getAsJsonArray("start"));route.add(test.getAsJsonArray("end"));}
                if(route.size()<2)throw new IllegalStateException("Route needs two points");
                waypoint=1;start=vector(route.get(0).getAsJsonArray());end=vector(route.get(1).getAsJsonArray());
                for(int segment=1;segment<route.size();segment++)
                {
                    Vec3 a=vector(route.get(segment-1).getAsJsonArray()),b=vector(route.get(segment).getAsJsonArray());
                    for(int cx=(int)Math.floor(Math.min(a.x,b.x)-3)>>4;cx<=(int)Math.floor(Math.max(a.x,b.x)+3)>>4;cx++)
                        for(int cz=(int)Math.floor(Math.min(a.z,b.z)-3)>>4;cz<=(int)Math.floor(Math.max(a.z,b.z)+3)>>4;cz++)
                        {ChunkPos chunk=new ChunkPos(cx,cz);level.getChunkSource().addRegionTicket(TICKET,chunk,2,chunk);level.getChunk(cx,cz);}
                }
                // getChunk above is synchronous: the collision data is already
                // FULL. Extra idle ticks here added half an hour to a whole-world
                // audit without simulating any additional player movement.
                wait=3;positioned=false;
            }
            if(wait++<3)return;
            if(!positioned)
            {
                player.setPos(start);player.setOnGround(true);player.setDeltaMovement(Vec3.ZERO);steps=0;stalled=0;settled=0;maxRise=0;fallSpeed=0;
                double length=0;
                for(int j=1;j<route.size();j++)length+=vector(route.get(j).getAsJsonArray()).distanceTo(vector(route.get(j-1).getAsJsonArray()));
                stepLimit=Math.max(2000,(int)Math.ceil(length/.12)+route.size()*100);
                TRACE.asList().clear();positioned=true;
                activeLevel=level;RESTORE.clear();
                if(test.has("useDoor"))
                {
                    JsonArray d=test.getAsJsonArray("door");BlockPos door=new BlockPos(d.get(0).getAsInt(),d.get(1).getAsInt(),d.get(2).getAsInt());
                    for(BlockPos pos:List.of(door,door.above()))RESTORE.put(pos,level.getBlockState(pos));
                    BlockState state=level.getBlockState(door);
                    if(!(state.getBlock() instanceof net.minecraft.world.level.block.DoorBlock)){finish(test,"missing_entry_door");return;}
                    if(!state.getValue(net.minecraft.world.level.block.DoorBlock.OPEN))state.use(level,player,net.minecraft.world.InteractionHand.MAIN_HAND,new net.minecraft.world.phys.BlockHitResult(Vec3.atCenterOf(door),net.minecraft.core.Direction.SOUTH,door,false));
                    if(!level.getBlockState(door).getValue(net.minecraft.world.level.block.DoorBlock.OPEN)){finish(test,"door_did_not_open");return;}
                }
                if(test.has("button"))
                {
                    JsonArray a=test.getAsJsonArray("button"),d=test.getAsJsonArray("door");
                    BlockPos button=new BlockPos(a.get(0).getAsInt(),a.get(1).getAsInt(),a.get(2).getAsInt());
                    BlockPos door=new BlockPos(d.get(0).getAsInt(),d.get(1).getAsInt(),d.get(2).getAsInt());
                    for(BlockPos pos:List.of(door,door.above(),button))RESTORE.put(pos,level.getBlockState(pos));
                    BlockState state=level.getBlockState(button);
                    if(!(state.getBlock() instanceof net.minecraft.world.level.block.ButtonBlock))throw new IllegalStateException("Expected a native door button at "+button);
                    state.use(level,player,net.minecraft.world.InteractionHand.MAIN_HAND,new net.minecraft.world.phys.BlockHitResult(Vec3.atCenterOf(button),net.minecraft.core.Direction.NORTH,button,false));
                    BlockState opened=level.getBlockState(door);
                    if(!opened.hasProperty(net.minecraft.world.level.block.DoorBlock.OPEN)||!opened.getValue(net.minecraft.world.level.block.DoorBlock.OPEN))
                    {finish(test,"door_did_not_open");return;}
                }
            }
            for(int n=0;n<120;n++)
            {
                Vec3 old=player.position();double dx=end.x-old.x,dz=end.z-old.z;distance=Math.hypot(dx,dz);
                if(distance<.18 && player.onGround() && settled>=2)
                {
                    if(Math.abs(old.y-end.y)>=.16){finish(test,"wrong_arrival_height");break;}
                    if(++waypoint==route.size()){finish(test,"pass");break;}
                    // A route gets one initial placement. Turns continue from the actual
                    // settled player position, so a disconnected seam cannot be skipped.
                    start=end;end=vector(route.get(waypoint).getAsJsonArray());settled=0;stalled=0;continue;
                }
                if(old.y<Math.min(start.y,end.y)-.65){finish(test,"floor_gap");break;}
                double amount=distance<.18?0:Math.min(.12,distance);
                fallSpeed=(fallSpeed-.08)*.98;
                player.move(MoverType.SELF,new Vec3(distance<.001?0:dx/distance*amount,fallSpeed,distance<.001?0:dz/distance*amount));
                if(player.onGround())fallSpeed=0;
                Vec3 now=player.position();maxRise=Math.max(maxRise,now.y-old.y);steps++;
                if(amount==0 && player.onGround() && Math.abs(now.y-old.y)<.0001)settled++;else settled=0;
                if(distance>=.18 && Math.hypot(now.x-old.x,now.z-old.z)<.0001)stalled++;else stalled=0;
                if(steps%4==0||stalled>0)TRACE.add(position(now));
                if(stalled>=8){finish(test,"blocked_by_native_collision");break;}
                if(steps>stepLimit){finish(test,"timeout");break;}
            }
        }
        catch(Exception exception)
        {
            ProjectSeele.LOGGER.error("SPATIAL NATIVE AUDIT FAILED",exception);
            if(activeLevel!=null){RESTORE.forEach((pos,state)->activeLevel.setBlock(pos,state,3));RESTORE.clear();}
            try{Files.writeString(world.resolve("quality_native_failure.txt"),exception.toString());}catch(Exception ignored){}
            done=true;server.halt(false);
        }
    }
    private static void finish(JsonObject test,String status)
    {
        JsonObject result=test.deepCopy();result.addProperty("status",status);result.add("actual",position(player.position()));
        result.addProperty("waypointsReached",waypoint);
        result.addProperty("maxRise",maxRise);result.addProperty("playerStep",player.maxUpStep());result.add("trace",TRACE.deepCopy());RESULTS.add(result);
        ProjectSeele.LOGGER.info("SPATIAL WALK {} {} actual={} target={}",test.get("id").getAsString(),status,player.position(),end);
        RESTORE.forEach((pos,state)->activeLevel.setBlock(pos,state,3));RESTORE.clear();
        index++;wait=0;
    }
}
