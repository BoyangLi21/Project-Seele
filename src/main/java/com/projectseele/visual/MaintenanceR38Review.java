package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.world.*;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

@Mod.EventBusSubscriber(modid="projectseele")
public final class MaintenanceR38Review
{
    public static final boolean ENABLED="r38-recovery".equals(System.getProperty("projectseele.regionalBuild"));
    public static volatile boolean done;
    private static int ticks;private static CompoundTag before;private static final Map<Integer,UUID> ids=new HashMap<>();
    private static float cargoHealth;private static List<UUID> cargoPassengers;
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_FIELD_R38_REVIEW"))throw new IllegalStateException("R38 requires its isolated copy");
        var level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null||server.getPlayerList().getPlayers().isEmpty()||++ticks<80)return;
        var report=new JsonObject();
        try
        {
            if(before==null)
            {
                if(Boolean.getBoolean("projectseele.r38LiveCargo"))
                {
                    if(!NervAirLiftR30.stageCarriedReviewR38(level,2,server.getPlayerList().getPlayers().get(0).getUUID())){if(ticks>400)throw new IllegalStateException("Cargo fixture loading failed");return;}
                    var cargo=EvaLogisticsDirector.canonicalUnit(level,2);cargoHealth=cargo.getHealth();cargoPassengers=cargo.getPassengers().stream().map(net.minecraft.world.entity.Entity::getUUID).toList();
                }
                before=NervAirLiftR30.inspectionR38(level);
                for(int i=0;i<3;i++)ids.put(i,EvaFleetSavedData.get(server).entry(i).orElseThrow().canonicalId());
                server.getCommands().performPrefixedCommand(server.createCommandSourceStack(),"nerv transport force_recover");return;
            }
            var after=NervAirLiftR30.inspectionR38(level);
            if(after.getBoolean("ForceRecoveryR38")){if(ticks>700)throw new IllegalStateException("Forced recovery did not complete");return;}
            if(after.contains("Job")||!before.getUUID("Aircraft").equals(after.getUUID("Aircraft")))throw new IllegalStateException("Job remains or aircraft identity changed");
            var plane=ServiceAircraftR32.find(level,after.getUUID("Aircraft"));
            if(plane==null||plane.position().distanceTo(NervAirLiftR30.STAND)>.05)throw new IllegalStateException("Aircraft did not return to its stand");
            for(int i=0;i<3;i++)if(!ids.get(i).equals(EvaFleetSavedData.get(server).entry(i).orElseThrow().canonicalId()))throw new IllegalStateException("Canonical EVA changed");
            if(Boolean.getBoolean("projectseele.r38LiveCargo"))
            {
                var cargo=EvaLogisticsDirector.canonicalUnit(level,2);
                if(cargo==null||cargo.getHealth()!=cargoHealth||!cargo.getPassengers().stream().map(net.minecraft.world.entity.Entity::getUUID).toList().equals(cargoPassengers)||!NervAirLiftR30.waitingAtHead(cargo))throw new IllegalStateException("Cargo health, capsule assembly or handoff changed");
                report.addProperty("cargo_health_and_capsule_retained",true);report.addProperty("cargo_waits_on_own_surface_head",true);
            }
            report.addProperty("passed",true);report.addProperty("command","/nerv transport force_recover");report.addProperty("original_aircraft_retained",true);report.addProperty("original_fleet_retained",true);
            report.addProperty("source_job_phase",before.getCompound("Job").getString("Phase"));report.addProperty("ticks",ticks);
        }
        catch(Exception failure){report.addProperty("passed",false);report.addProperty("error",failure.toString());}
        try{Path output=Path.of("../artifacts/combat_facility_r38/"+(Boolean.getBoolean("projectseele.r38LiveCargo")?"force_recovery_cargo.json":"force_recovery.json"));Files.createDirectories(output.getParent());Files.writeString(output,new GsonBuilder().setPrettyPrinting().create().toJson(report));}
        catch(Exception failure){throw new IllegalStateException(failure);}done=true;
    }
    @Mod.EventBusSubscriber(modid="projectseele",value=net.minecraftforge.api.distmarker.Dist.CLIENT)
    public static final class Client
    {
        private static int ending;
        @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
        {if(ENABLED&&done&&event.phase==TickEvent.Phase.END&&++ending>30)net.minecraft.client.Minecraft.getInstance().stop();}
    }
    private MaintenanceR38Review(){}
}
