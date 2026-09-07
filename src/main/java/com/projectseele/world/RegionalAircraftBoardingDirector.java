package com.projectseele.world;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.visual.RegionalNativeTransitInspection;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.*;

/** Deploys only the surveyed apron stairs while a native aircraft is stopped with doors open. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class RegionalAircraftBoardingDirector
{
    private static final Map<ServerLevel,Runtime> RUNTIMES=new WeakHashMap<>();
    private static final BlockState AIR=Blocks.AIR.defaultBlockState();

    private static final class Gate
    {
        String id;
        double x,y,z;
        final Map<BlockPos,BlockState> stairs=new LinkedHashMap<>();
        Boolean deployed;
        boolean fault;
    }
    private static final class Runtime
    {
        boolean checked,reported;
        final List<Gate> gates=new ArrayList<>();
    }
    @SuppressWarnings({"rawtypes","unchecked"})
    private static BlockState parse(String text)
    {
        int bracket=text.indexOf('[');
        ResourceLocation id=new ResourceLocation(bracket<0?text:text.substring(0,bracket));
        if(!BuiltInRegistries.BLOCK.containsKey(id))throw new IllegalArgumentException("Unknown boarding state "+text);
        BlockState state=BuiltInRegistries.BLOCK.get(id).defaultBlockState();
        if(bracket>=0)for(String assignment:text.substring(bracket+1,text.length()-1).split(","))
        {
            String[] pair=assignment.split("=");Property property=state.getBlock().getStateDefinition().getProperty(pair[0]);
            if(property==null)throw new IllegalArgumentException("Unknown boarding property "+text);
            state=state.setValue(property,(Comparable)property.getValue(pair[1]).orElseThrow());
        }
        return state;
    }
    private static Object call(Object object,String method) throws ReflectiveOperationException
    {
        return object.getClass().getMethod(method).invoke(object);
    }
    private static boolean owned(BlockState actual,BlockState expected)
    {
        return actual.equals(expected)||(actual.is(expected.getBlock())&&BuiltInRegistries.BLOCK.getKey(expected.getBlock()).toString().equals("mtr:platform"));
    }
    private static Runtime state(ServerLevel level) throws Exception
    {
        Runtime runtime=RUNTIMES.computeIfAbsent(level,unused->new Runtime());
        if(runtime.checked)return runtime;
        runtime.checked=true;
        var path=level.getServer().getWorldPath(LevelResource.ROOT).resolve("regional_boarding_gates.json");
        if(!Files.exists(path))return runtime;
        JsonObject plan=JsonParser.parseString(Files.readString(path)).getAsJsonObject();
        if(plan.get("version").getAsInt()!=1)throw new IllegalStateException("Unknown boarding plan version");
        for(JsonElement element:plan.getAsJsonArray("gates"))
        {
            JsonObject item=element.getAsJsonObject();Gate gate=new Gate();gate.id=item.get("id").getAsString();
            JsonArray head=item.getAsJsonArray("head");gate.x=head.get(0).getAsDouble();gate.y=head.get(1).getAsDouble();gate.z=head.get(2).getAsDouble();
            for(JsonElement cell:item.getAsJsonArray("stairs"))
            {
                JsonArray a=cell.getAsJsonArray();BlockPos pos=new BlockPos(a.get(0).getAsInt(),a.get(1).getAsInt(),a.get(2).getAsInt());
                if(Math.abs(pos.getX()-gate.x)>40||Math.abs(pos.getZ()-gate.z)>20||pos.getY()<81||pos.getY()>85)
                    throw new IllegalStateException("Boarding cells exceed surveyed apron "+gate.id);
                gate.stairs.put(pos,parse(a.get(3).getAsString()));
            }
            if(gate.stairs.isEmpty()||gate.stairs.size()>160)throw new IllegalStateException("Unexpected boarding volume "+gate.id);
            runtime.gates.add(gate);
        }
        return runtime;
    }
    @SubscribeEvent
    public static void tick(TickEvent.ServerTickEvent event)
    {
        if(event.phase!=TickEvent.Phase.END)return;
        ServerLevel level=event.getServer().getLevel(FacilitySchemaV2.DIMENSION);
        if(level==null||!RegionalGatewayDirector.active(level))return;
        Runtime runtime=null;
        try
        {
            runtime=state(level);if(runtime.gates.isEmpty())return;
            Set<String> docked=new HashSet<>();Object simulator=RegionalNativeTransitInspection.simulator();
            if(simulator!=null)for(Object siding:(Iterable<?>)simulator.getClass().getField("sidings").get(simulator))
            {
                if(!"AIRPLANE".equals(call(siding,"getTransportMode").toString()))continue;
                Field field=siding.getClass().getDeclaredField("vehicles");field.setAccessible(true);
                for(Object vehicle:(Iterable<?>)field.get(siding))
                {
                    if((Boolean)call(vehicle,"isMoving")||!(Boolean)call(vehicle,"getIsOnRoute"))continue;
                    Object extra=vehicle.getClass().getField("vehicleExtraData").get(vehicle);
                    if(((Number)call(extra,"getDoorMultiplier")).intValue()==0)continue;
                    Object head=call(vehicle,"getHeadPosition");if(head==null)continue;
                    double x=head.getClass().getField("x").getDouble(head),y=head.getClass().getField("y").getDouble(head),z=head.getClass().getField("z").getDouble(head);
                    for(Gate gate:runtime.gates)if(Math.abs(x-gate.x)<1.5&&Math.abs(y-gate.y)<.5&&Math.abs(z-gate.z)<1)docked.add(gate.id);
                }
            }
            for(Gate gate:runtime.gates)
            {
                if(gate.fault||gate.stairs.keySet().stream().anyMatch(p->!level.hasChunkAt(p)))continue;
                boolean deploy=docked.contains(gate.id);
                if(gate.deployed!=null&&gate.deployed==deploy)continue;
                for(var entry:gate.stairs.entrySet())
                {
                    BlockState actual=level.getBlockState(entry.getKey());
                    if(!actual.isAir()&&!owned(actual,entry.getValue()))
                    {gate.fault=true;ProjectSeele.LOGGER.error("AIRCRAFT BOARDING preserved unexpected block at {}",entry.getKey());break;}
                }
                if(gate.fault)continue;
                for(var entry:gate.stairs.entrySet())level.setBlock(entry.getKey(),deploy?entry.getValue():AIR,3);
                gate.deployed=deploy;
                ProjectSeele.LOGGER.info("AIRCRAFT BOARDING {} {}",gate.id,deploy?"deployed at native open-door stop":"retracted; taxi envelope clear");
            }
        }
        catch(Exception exception)
        {
            if(runtime==null||!runtime.reported)ProjectSeele.LOGGER.error("AIRCRAFT BOARDING configuration or native state unavailable",exception);
            if(runtime!=null)
            {
                runtime.reported=true;
                // A lost native signal must leave the taxi corridor clear.
                for(Gate gate:runtime.gates)
                {
                    for(var entry:gate.stairs.entrySet())if(level.hasChunkAt(entry.getKey())&&owned(level.getBlockState(entry.getKey()),entry.getValue()))
                        level.setBlock(entry.getKey(),AIR,3);
                    gate.deployed=false;
                }
            }
        }
    }
}
