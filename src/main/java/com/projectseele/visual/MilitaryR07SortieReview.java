package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaPrototypeEntity;
import com.projectseele.world.*;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.*;
import net.minecraft.world.level.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** A real player boards, walks the original airframe through the gate, returns and dismounts. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class MilitaryR07SortieReview
{
    public static final boolean ENABLED="r07-sortie".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile int phase,drive;
    public static volatile boolean finished;
    private static int age,phaseAge;private static ServerPlayer pilot;private static EvaPrototypeEntity unit;
    private static Vec3 oldPos;private static float oldYaw,oldPitch;private static GameType oldMode;private static boolean oldFlying;
    private static ResourceKey<Level> oldDimension;private static CompoundTag original;
    private static final JsonArray checks=new JsonArray();private static final List<UUID> canonical=new ArrayList<>();
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r07_sortie_review",Comparator.comparingLong(ChunkPos::toLong),100);
    private static final List<ChunkPos> chunks=new ArrayList<>();
    private static void check(String name,boolean pass,String detail)
    {
        JsonObject c=new JsonObject();c.addProperty("name",name);c.addProperty("passed",pass);c.addProperty("detail",detail);checks.add(c);
        if(!pass)throw new IllegalStateException(name+": "+detail);
        ProjectSeele.LOGGER.info("R07 SORTIE PASS {} {}",name,detail);
    }
    private static void next(){phase++;phaseAge=0;}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty()||++age<100)return;
        Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("R07 sortie world boundary");
        ServerLevel level=server.getLevel(FacilitySchemaV2.DIMENSION);
        try
        {
            phaseAge++;var data=MilitaryR07Director.state(level);
            if(age%20==0)for(ChunkPos p:chunks)level.getChunkSource().addRegionTicket(TICKET,p,2,p);
            if(phase==0)
            {
                check("commissioned",data.commissioned,"real preview world");
                pilot=server.getPlayerList().getPlayers().get(0);oldPos=pilot.position();oldYaw=pilot.getYRot();oldPitch=pilot.getXRot();oldMode=pilot.gameMode.getGameModeForPlayer();oldDimension=pilot.level().dimension();oldFlying=pilot.getAbilities().flying;
                check("operator_unmounted",!pilot.isPassenger(),"review preserves original operator state");
                for(int i=0;i<3;i++)canonical.add(EvaFleetSavedData.get(server).canonicalId(i).orElseThrow());
                pilot.setGameMode(GameType.SPECTATOR);pilot.teleportTo(level,6442.5,100,-6102.5,180,0);
                for(int x=399;x<=406;x++)for(int z=-391;z<=-381;z++){ChunkPos p=new ChunkPos(x,z);chunks.add(p);level.getChunkSource().addRegionTicket(TICKET,p,2,p);}
                level.getChunk(new BlockPos(6442,77,-6205));next();return;
            }
            if(phase==1)
            {
                if(data.phase==MilitaryR07Director.Phase.WET)MilitaryR07Director.request(level,"drain",null);
                if(data.phase==MilitaryR07Director.Phase.DRY)MilitaryR07Director.request(level,"door",null);
                if(data.phase==MilitaryR07Director.Phase.OPEN)
                {
                    var entity=level.getEntity(data.entities.get("prototype"));if(entity==null&&phaseAge<160)return;
                    check("original_prototype",entity instanceof EvaPrototypeEntity,String.valueOf(entity));unit=(EvaPrototypeEntity)entity;original=unit.saveWithoutId(new CompoundTag());
                    check("prototype_home",unit.position().distanceTo(new Vec3(6442.5,77,-6205.5))<3,unit.position().toString());
                    pilot.setGameMode(GameType.SURVIVAL);pilot.teleportTo(level,6442.5,127,-6217.5,0,0);pilot.getAbilities().flying=false;pilot.onUpdateAbilities();next();return;
                }
            }
            if(phase==2&&phaseAge>=20)
            {
                unit.tryEnterFromPlug(pilot,false);
                check("gantry_boarding",pilot.getVehicle()==unit,"actual plug approach and obstruction validation");next();return;
            }
            if(phase==3&&unit.getActivationTicks()==0)
            {
                check("native_power",unit.isPoweredOn()&&unit.isUmbilicalConnected(),"physical pylon charges inserted pilot circuit");drive=1;next();return;
            }
            if(phase==4&&unit.getZ()>-6115)
            {
                drive=0;check("physical_airframe_gate_exit",unit.getBoundingBox().minZ>-6135&&Math.abs(unit.getY()-77)<.3,unit.position().toString());next();return;
            }
            if(phase==5)
            {
                if(phaseAge==20)unit.setPilotCrouching(pilot,true);
                if(phaseAge==60)check("prototype_crouch",unit.isPilotCrouching(),"native stance control");
                if(phaseAge==70)unit.toggleProne(pilot);
                if(phaseAge==110)check("prototype_prone",unit.isPilotProne(),"native stance control");
                if(phaseAge==120)unit.toggleProne(pilot);
                if(phaseAge==170){check("prototype_stand",!unit.isPilotProne()&&!unit.isPilotCrouching(),"native standing clearance");drive=-1;next();return;}
            }
            if(phase==6&&unit.position().distanceTo(new Vec3(6442.5,77,-6205.5))<1)
            {drive=0;next();return;}
            if(phase==7&&phaseAge>=30)
            {
                check("physical_return",unit.position().distanceTo(new Vec3(6442.5,77,-6205.5))<3,unit.position().toString());
                unit.exitEva(pilot);check("independent_dismount",!pilot.isPassenger()&&pilot.position().distanceTo(new Vec3(6442.5,127,-6217.5))<2,pilot.position().toString());
                MilitaryR07Director.request(level,"door",pilot);next();return;
            }
            if(phase==8)
            {
                if(data.phase==MilitaryR07Director.Phase.OPEN)MilitaryR07Director.request(level,"door",null);
                if(data.phase==MilitaryR07Director.Phase.DRY)MilitaryR07Director.request(level,"fill",null);
                if(data.phase==MilitaryR07Director.Phase.WET)
                {
                    check("stored_again",MilitaryR07Director.fluidCells(level)==130680,"closed and refilled after actual sortie");
                    check("next_sortie_ready",!unit.isUmbilicalSevered()&&!unit.isEntryPlugInserted()&&unit.getPowerTicks()==0,"dock restores the cold pilot circuit and cable connector");
                    for(int i=0;i<3;i++)check("canonical_0"+i,canonical.get(i).equals(EvaFleetSavedData.get(server).canonicalId(i).orElse(null)),canonical.get(i).toString());
                    finish(level,world,null);return;
                }
            }
            if(phaseAge>2200)throw new IllegalStateException("Sortie timed out phase="+phase+" unit="+(unit==null?"null":unit.position())+" facility="+data.phase);
        }
        catch(Exception failure){finish(level,world,failure);}
    }
    private static void finish(ServerLevel level,Path world,Exception failure)
    {
        drive=0;finished=true;
        for(ChunkPos p:chunks)level.getChunkSource().removeRegionTicket(TICKET,p,2,p);
        if(pilot!=null){pilot.stopRiding();pilot.teleportTo(level.getServer().getLevel(oldDimension),oldPos.x,oldPos.y,oldPos.z,oldYaw,oldPitch);pilot.setGameMode(oldMode);pilot.fallDistance=0;pilot.getAbilities().flying=oldFlying;pilot.onUpdateAbilities();}
        if(failure!=null&&unit!=null&&original!=null){unit.load(original);unit.setDeltaMovement(Vec3.ZERO);}
        JsonObject report=new JsonObject();report.addProperty("passed",failure==null);report.add("checks",checks);
        if(failure!=null){report.addProperty("failure",failure.toString());ProjectSeele.LOGGER.error("R07 sortie failed",failure);}
        try{Files.writeString(world.resolve("r07_sortie_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception ignored){}
    }
}
