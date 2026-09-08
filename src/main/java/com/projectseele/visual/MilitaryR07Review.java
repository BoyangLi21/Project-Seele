package com.projectseele.visual;

import com.google.gson.*;
import com.mojang.authlib.GameProfile;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaPrototypeEntity;
import com.projectseele.registry.ModItems;
import com.projectseele.world.FacilitySchemaV2;
import com.projectseele.world.MilitaryR07Director;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Native physical interlocks and installed-equipment checks on the real R07 world. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class MilitaryR07Review
{
    private static final boolean ENABLED="r07-review".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final TicketType<ChunkPos> TICKET=TicketType.create("seele_r07_review",Comparator.comparingLong(ChunkPos::toLong),200);
    private static int age,phase,phaseAge;private static boolean done;private static FakePlayer operator;
    private static final JsonArray checks=new JsonArray();private static final Set<ChunkPos> tickets=new HashSet<>();
    private static UUID prototypeId;
    private static void check(String name,boolean passed,String detail)
    {
        JsonObject r=new JsonObject();r.addProperty("name",name);r.addProperty("passed",passed);r.addProperty("detail",detail);checks.add(r);
        if(!passed)throw new IllegalStateException(name+": "+detail);
        ProjectSeele.LOGGER.info("R07 NATIVE PASS {} {}",name,detail);
    }
    private static void next(){phase++;phaseAge=0;}
    private static void keep(ServerLevel level,ChunkPos chunk)
    {
        level.getChunkSource().addRegionTicket(TICKET,chunk,2,chunk);tickets.add(chunk);level.getChunk(chunk.x,chunk.z);
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();ServerLevel level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
        Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("R07 review world boundary");
        try
        {
            level.resetEmptyTime();
            if(++age<100)return;phaseAge++;var data=MilitaryR07Director.state(level);
            if(age%20==0)for(ChunkPos p:tickets)level.getChunkSource().addRegionTicket(TICKET,p,2,p);
            if(phase==0)
            {
                JsonObject plan=JsonParser.parseString(Files.readString(world.resolve("r07_installations.json"))).getAsJsonObject();
                for(var v:plan.getAsJsonArray("entities"))
                {
                    var p=v.getAsJsonObject().getAsJsonArray("position");keep(level,new ChunkPos(BlockPos.containing(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble())));
                }
                for(int x=399;x<=406;x++)for(int z=-391;z<=-383;z++)keep(level,new ChunkPos(x,z));
                prototypeId=data.entities.get("prototype");next();return;
            }
            if(phase==1&&phaseAge>=80)
            {
                // A previous interrupted review may leave a dry/open cell.
                // Restore it through the real controls before the next cycle.
                if(data.phase==MilitaryR07Director.Phase.OPEN){MilitaryR07Director.request(level,"door",null);return;}
                if(data.phase==MilitaryR07Director.Phase.DRY){MilitaryR07Director.request(level,"fill",null);return;}
                if(data.phase!=MilitaryR07Director.Phase.WET)return;
                check("commissioned",data.commissioned,"saved installation state");int vehicles=0,defenders=0;
                for(var entry:data.entities.entrySet())
                {
                    if(!entry.getKey().startsWith("vehicle/"))continue;Entity e=level.getEntity(entry.getValue());
                    check(entry.getKey()+"/present",e!=null&&e.isAlive(),String.valueOf(entry.getValue()));vehicles++;
                    Object health=e.getClass().getMethod("getHealth").invoke(e);check(entry.getKey()+"/health",((Number)health).doubleValue()>0,health.toString());
                    e.getCapability(ForgeCapabilities.ENERGY).ifPresent(storage->check(entry.getKey()+"/energy",storage.getEnergyStored()>0,storage.getEnergyStored()+"/"+storage.getMaxEnergyStored()));
                    e.getCapability(ForgeCapabilities.ITEM_HANDLER).ifPresent(items->{
                        boolean supplied=items.getSlots()==0;
                        for(int i=0;i<items.getSlots();i++)if(net.minecraft.core.registries.BuiltInRegistries.ITEM.getKey(items.getStackInSlot(i).getItem()).toString().equals("superbwarfare:creative_ammo_box"))supplied=true;
                        check(entry.getKey()+"/supply",supplied,"native vehicle inventory");
                    });
                    if(e.getTags().contains("seele_r07_defense"))
                    {
                        Object owner=e.getClass().getMethod("getOwner").invoke(e),active=e.getClass().getMethod("getActive").invoke(e);
                        check(entry.getKey()+"/controller",owner instanceof Entity&&Boolean.TRUE.equals(active),"owned active native SBW AI");defenders++;
                    }
                }
                check("fleet_count",vehicles==22&&defenders==8,vehicles+" vehicles, "+defenders+" automatic defenses");
                check("independent_prototype",level.getEntity(prototypeId) instanceof EvaPrototypeEntity,"dedicated entity type and UUID");
                operator=FakePlayerFactory.get(level,new GameProfile(UUID.fromString("a0af3923-7b37-42ee-8b70-8398474360ab"),"[R07 reviewer]"));operator.setGameMode(GameType.SURVIVAL);operator.getInventory().clearContent();operator.setPos(6398.5,77,-6144.5);
                var previous=data.phase;String denied=MilitaryR07Director.request(level,"drain",operator);check("card_denial",data.phase==previous&&denied.contains("身份卡"),denied);
                operator.getInventory().setItem(0,new ItemStack(ModItems.NERV_EMPLOYEE_CARD.get()));
                String gate=MilitaryR07Director.request(level,"door",operator);check("wet_gate_interlock",data.phase==MilitaryR07Director.Phase.WET&&gate.contains("LCL"),gate);
                MilitaryR07Director.request(level,"drain",operator);next();return;
            }
            if(phase==2&&data.phase==MilitaryR07Director.Phase.DRY)
            {
                check("physical_drain",MilitaryR07Director.fluidCells(level)==0,"entire 130680-cell envelope");MilitaryR07Director.request(level,"door",operator);next();return;
            }
            if(phase==3&&data.phase==MilitaryR07Director.Phase.OPEN)
            {
                check("open_gate",level.getBlockState(new BlockPos(6442,80,-6136)).isAir(),"collision plane cleared after animation");
                check("open_cage_unlock",level.getEntity(prototypeId) instanceof EvaPrototypeEntity p&&!p.isNervLogisticsLocked(),"airframe released");
                operator.setPos(6442.5,77,-6140.5);operator.noPhysics=false;operator.setNoGravity(false);operator.getAbilities().flying=false;
                for(int i=0;i<95;i++)operator.move(MoverType.SELF,new Vec3(0,-.08,.12));
                check("physical_gate_walk",operator.getZ()>-6131&&Math.abs(operator.getY()-77)<.1,operator.position().toString());
                var obstruction=EntityType.ARMOR_STAND.create(level);if(obstruction==null)throw new IllegalStateException("Review obstacle");
                obstruction.setPos(6442.5,77,-6135.5);obstruction.setNoGravity(true);level.addFreshEntity(obstruction);
                String occupied=MilitaryR07Director.request(level,"door",operator);check("occupied_gate_interlock",data.phase==MilitaryR07Director.Phase.OPEN,occupied);obstruction.discard();
                operator.setPos(6398.5,77,-6144.5);MilitaryR07Director.request(level,"door",operator);next();return;
            }
            if(phase==4&&data.phase==MilitaryR07Director.Phase.DRY)
            {
                check("closed_gate",level.getBlockState(new BlockPos(6442,80,-6136)).is(Blocks.BARRIER),"collision restored");
                String filling=MilitaryR07Director.request(level,"fill",operator);check("fill_started",data.phase==MilitaryR07Director.Phase.FILLING,filling);next();return;
            }
            if(phase==5&&data.phase==MilitaryR07Director.Phase.WET)
            {
                check("physical_refill",MilitaryR07Director.fluidCells(level)==130680,"full source-fluid envelope restored");
                check("prototype_identity",prototypeId.equals(data.entities.get("prototype")),prototypeId.toString());finish(level,world,null);return;
            }
            if(phaseAge>1400)throw new IllegalStateException("Review timed out phase="+phase+" facility="+data.phase+" cursor="+data.cursor);
        }
        catch(Exception failure){finish(level,world,failure);}
    }
    private static void finish(ServerLevel level,Path world,Exception failure)
    {
        done=true;for(ChunkPos p:tickets)level.getChunkSource().removeRegionTicket(TICKET,p,2,p);
        if(operator!=null){operator.getInventory().clearContent();operator.discard();}
        JsonObject report=new JsonObject();report.add("checks",checks);report.addProperty("passed",failure==null);report.addProperty("phase",phase);
        if(failure!=null){report.addProperty("failure",failure.toString());ProjectSeele.LOGGER.error("R07 native review failed",failure);}
        try {Files.writeString(world.resolve("r07_native_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception ignored){}
        level.getServer().halt(false);
    }
}
