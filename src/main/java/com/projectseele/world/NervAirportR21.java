package com.projectseele.world;

import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.Files;
import java.util.*;

/** Explicit install receipt authorizes initial aircraft creation only once. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class NervAirportR21
{
    public static final class State extends SavedData
    {
        final Map<String,UUID> aircraft=new LinkedHashMap<>();
        static State load(CompoundTag tag){var s=new State();for(String k:tag.getAllKeys())if(tag.hasUUID(k))s.aircraft.put(k,tag.getUUID(k));return s;}
        @Override public CompoundTag save(CompoundTag tag){aircraft.forEach(tag::putUUID);return tag;}
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(event.phase!=TickEvent.Phase.END||event.getServer().getTickCount()%40!=0)return;
        ServerLevel level=event.getServer().getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
        var file=event.getServer().getWorldPath(LevelResource.ROOT).resolve("nerv_airport_r21.json");if(!Files.isRegularFile(file))return;
        State state=level.getDataStorage().computeIfAbsent(State::load,State::new,"projectseele_nerv_airport_r21");
        try
        {
            var plan=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
            for(var element:plan.getAsJsonArray("vehicles"))
            {
                var spec=element.getAsJsonObject();String key=spec.get("key").getAsString();var pos=spec.getAsJsonArray("position");
                BlockPos pad=BlockPos.containing(pos.get(0).getAsDouble(),pos.get(1).getAsDouble(),pos.get(2).getAsDouble());
                if(state.aircraft.containsKey(key))continue;
                level.getChunk(pad);if(level.getBlockState(pad.below()).isAir())throw new IllegalStateException("Missing airport apron "+pad);
                var type=BuiltInRegistries.ENTITY_TYPE.get(new ResourceLocation(spec.get("id").getAsString()));Entity aircraft=type.create(level);
                if(aircraft==null)throw new IllegalStateException("Unavailable installed aircraft "+spec);
                CompoundTag tag=aircraft.saveWithoutId(new CompoundTag());tag.putBoolean("GearUp",false);tag.putFloat("ServerYaw",spec.get("yaw").getAsFloat());
                for(String field:new String[]{"Health","TurretHealth","LeftWheelHealth","RightWheelHealth","MainEngineHealth","SubEngineHealth"})tag.remove(field);
                tag.putInt("Energy",((Number)aircraft.getClass().getMethod("getMaxEnergy").invoke(aircraft)).intValue());
                var items=new ListTag();var ammunition=new ItemStack(BuiltInRegistries.ITEM.get(new ResourceLocation("superbwarfare:creative_ammo_box"))).save(new CompoundTag());ammunition.putByte("Slot",(byte)0);items.add(ammunition);tag.put("Items",items);
                aircraft.load(tag);aircraft.moveTo(pos.get(0).getAsDouble(),pos.get(1).getAsDouble(),pos.get(2).getAsDouble(),spec.get("yaw").getAsFloat(),0);aircraft.addTag("seele_r21_nerv_aircraft");
                if(!level.addFreshEntity(aircraft))throw new IllegalStateException("Aircraft creation rejected "+key);
                state.aircraft.put(key,aircraft.getUUID());state.setDirty();ProjectSeele.LOGGER.info("R21 NERV AIRPORT aircraft {} {} {}",key,aircraft.getUUID(),aircraft.position());
            }
        }
        catch(Exception e){throw new IllegalStateException("R21 aircraft commissioning",e);}
    }
    private NervAirportR21(){}
}
