package com.projectseele.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.world.*;
import com.google.gson.*;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.UUID;

/** Real logistics on a cold disposable copy: same fleet UUIDs, complete prepare/cancel/extract cycles. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class EvaCanonicalR11Review
{
    private static final boolean PERFORMANCE="r11-canonical-performance".equals(System.getProperty("projectseele.regionalBuild",""));
    public static final boolean ENABLED=PERFORMANCE||"r11-canonical".equals(System.getProperty("projectseele.regionalBuild",""));
    private static int age,phase,ticks,index;private static final int[] VARIANTS=PERFORMANCE?new int[]{1}:new int[]{1,0,2};private static ServerPlayer pilot;
    private static UUID originalEva,originalPlug;private static boolean sawOpen,sawSealed;private static String oldPhase="";
    private static final JsonArray checks=new JsonArray();private static Path world;
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||EvaMechanicsR11Review.finished||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty()||++age<100)return;
        world=server.getWorldPath(LevelResource.ROOT).normalize();if(!world.getFileName().toString().equals("SEELE_R11_CANONICAL_ACCEPTANCE"))throw new IllegalStateException("Canonical review requires cold copy");
        try
        {
            var level=server.getLevel(FacilitySchemaV2.DIMENSION);int variant=VARIANTS[index];ticks++;
            if(pilot==null){pilot=server.getPlayerList().getPlayers().get(0);pilot.stopRiding();pilot.setGameMode(net.minecraft.world.level.GameType.SURVIVAL);pilot.getCapability(com.projectseele.capability.EvaPilotCapability.DATA).ifPresent(c->c.setSynchronization(100));server.setFlightAllowed(true);}
            if(age%20==0)EvaLogisticsDirector.loadControlTarget(level,variant);
            var eva=EvaLogisticsDirector.canonicalUnit(level,variant);var plug=EntryPlugDirector.canonical(level,variant);if(eva==null||plug==null){if(ticks>500)throw new IllegalStateException("Canonical actor not loaded");return;}
            EvaMechanicsR11Review.actor=eva.getId();EvaMechanicsR11Review.view="dorsal";
            var status=EvaLogisticsDirector.status(level,variant);
            if(!oldPhase.equals(status.phase())){ProjectSeele.LOGGER.info("R11 CANONICAL unit={} phase={} t={}",variant,status.phase(),ticks);oldPhase=status.phase();}
            if(phase==0)
            {
                if(!status.phase().equals("PARKED"))throw new IllegalStateException("Cold baseline unit must be parked: "+status);
                originalEva=eva.getUUID();originalPlug=plug.getUUID();sawOpen=sawSealed=false;pilot.teleportTo(level,plug.getX(),plug.getY()+3,plug.getZ(),0,0);phase=1;ticks=0;return;
            }
            if(phase==1&&ticks>45&&EvaMechanicsR11Review.tracked)
            {
                if(!plug.boardPassenger(pilot))throw new IllegalStateException("Canonical boarding refused");var start=EvaLogisticsDirector.requestPrepare(level,variant);if(!start.accepted())throw new IllegalStateException("Prepare refused: "+start);phase=2;ticks=0;
            }
            if(phase==2)
            {
                if(EvaDorsalMechanism.open(eva)>.98&&EvaDorsalMechanism.bow(eva)>.98)sawOpen=true;
                if(plug.getInsertionProgress()>15&&plug.getInsertionProgress()<40)EvaMechanicsR11Review.shot="unit_"+variant+"_crane_approach";
                if(plug.getInsertionProgress()>77&&plug.getInsertionProgress()<92)EvaMechanicsR11Review.shot="unit_"+variant+"_open_socket";
                if(plug.isLockedToEva()&&EvaDorsalMechanism.eyesEnabled(eva)&&EvaDorsalMechanism.open(eva)<.001)sawSealed=true;
                if(status.phase().equals("PLUG_FAULT")||status.phase().startsWith("PLUG_ABORT"))throw new IllegalStateException("Canonical insertion interlock: "+status);
                if(status.phase().equals("SILO_READY"))
                {
                    check("unit_"+variant+"_prepare",sawOpen&&sawSealed&&eva.getUUID().equals(originalEva)&&plug.getUUID().equals(originalPlug)&&pilot.getVehicle()==plug);
                    var cancel=EvaLogisticsDirector.requestCancel(level,variant);if(!cancel.accepted())throw new IllegalStateException("Cancel refused: "+cancel);phase=3;ticks=0;
                }
                if(ticks>2600)throw new IllegalStateException("Canonical prepare deadline: "+status);
            }
            if(phase==3)
            {
                if(status.phase().equals("PLUG_FAULT"))throw new IllegalStateException("Canonical extraction fault");
                if(status.phase().equals("PARKED")&&plug.getInsertionProgress()==0&&!plug.isLockedToEva()&&ticks>150)
                {
                    check("unit_"+variant+"_returned",eva.getUUID().equals(originalEva)&&plug.getUUID().equals(originalPlug)&&EvaDorsalMechanism.open(eva)<.001);pilot.stopRiding();
                    if(++index==VARIANTS.length){finish("");return;}phase=0;ticks=0;oldPhase="";
                }
                if(ticks>3000)throw new IllegalStateException("Canonical return deadline: "+status);
            }
        }
        catch(Exception e){ProjectSeele.LOGGER.error("R11 CANONICAL FAILED",e);finish(e.toString());}
    }
    private static void check(String name,boolean pass)throws Exception
    {JsonObject c=new JsonObject();c.addProperty("name",name);c.addProperty("passed",pass);checks.add(c);if(!pass)throw new IllegalStateException(name);ProjectSeele.LOGGER.info("R11 CANONICAL PASS {}",name);}
    private static void finish(String error)
    {EvaMechanicsR11Review.finished=true;JsonObject report=new JsonObject();report.add("checks",checks);report.addProperty("error",error);try{Files.writeString(world.resolve("r11_canonical_cycles.json"),report.toString());}catch(Exception ignored){}}
}
