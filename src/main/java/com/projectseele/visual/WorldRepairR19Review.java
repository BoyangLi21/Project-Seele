package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.registry.ModItems;
import com.projectseele.world.*;
import com.supermartijn642.movingelevators.blocks.ControllerBlockEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.*;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.*;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Human-pilot arrival support, Dogma egress and native departure boards in a copy. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class WorldRepairR19Review
{
    private static final boolean BOARDS_ONLY=Set.of("r19-boards","r19-boards-tour").contains(System.getProperty("projectseele.regionalBuild",""));
    public static final boolean ENABLED=BOARDS_ONLY||"r19-runtime".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean finished,clientReady;
    public static volatile BlockPos click;
    public static volatile String phase="initializing";
    private static Path world;private static ServerLevel level;private static ServerPlayer player;
    private static int age,state,timer,arrivalTicks;private static boolean moved;
    private static UUID airframe,plugId;private static double minimumArrivalY=Double.MAX_VALUE;
    private static final JsonObject checks=new JsonObject();
    @SubscribeEvent(priority=net.minecraftforge.eventbus.api.EventPriority.LOWEST,receiveCanceled=true)
    public static void realButtonUse(net.minecraftforge.event.entity.player.PlayerInteractEvent.RightClickBlock event)
    {
        if(ENABLED&&event.getEntity() instanceof ServerPlayer&&event.getPos().equals(new BlockPos(9,-565,258)))
        {
            checks.addProperty("actual_dogma_button_packet",true);
            ProjectSeele.LOGGER.info("R19 Dogma call packet received; cancelled={}",event.isCanceled());
        }
    }
    private static void check(String label,boolean ok)
    {
        checks.addProperty(label,ok);if(!ok)throw new IllegalStateException(label);
    }
    private static void next(String name) { phase=name;timer=0;state++;ProjectSeele.LOGGER.info("R19 REVIEW {}",name); }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END||event.getServer().getPlayerList().getPlayers().isEmpty())return;
        try
        {
            var server=event.getServer();
            if(world==null)
            {
                world=server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize();
                check("isolated_world",world.getFileName().toString().equals("SEELE_R19_NATIVE_REVIEW"));
                level=server.getLevel(FacilitySchemaV2.DIMENSION);player=server.getPlayerList().getPlayers().get(0);
                player.stopRiding();player.setGameMode(GameType.CREATIVE);player.getAbilities().flying=false;player.onUpdateAbilities();
                player.setItemInHand(InteractionHand.MAIN_HAND,ItemStack.EMPTY);player.setItemInHand(InteractionHand.OFF_HAND,ItemStack.EMPTY);
                player.teleportTo(level,10.5,-566,260.5,180,10);
                if(BOARDS_ONLY){state=9;phase="native_departure_boards";player.teleportTo(level,512.5,81,469.5,0,0);}
            }
            if(++age>11000)throw new IllegalStateException("R19 total timeout in "+phase);
            if(!clientReady)return;
            timer++;
            var spec=S20PhysicalElevatorDirector.commandRearLift();
            ControllerBlockEntity controller=level.getBlockEntity(new BlockPos(9,-566,253)) instanceof ControllerBlockEntity c?c:null;
            var group=controller!=null&&controller.hasGroup()?controller.getGroup():null;
            switch(state)
            {
                case 0 ->
                {
                    if(timer<100||group==null)return;
                    if(group.isMoving())return;
                    if(!S20PhysicalElevatorDirector.hasAuthoredCabinAt(level,new BlockPos(12,-448,253)))
                    {
                        group.onDisplayPress(-448,0,player);return;
                    }
                    check("dogma_no_card",player.getMainHandItem().isEmpty()&&player.getOffhandItem().isEmpty());
                    click=S20PhysicalElevatorDirector.exteriorCallPosition(spec.stops().get(0));moved=false;arrivalTicks=0;next("dogma_call_without_card");
                }
                case 1 ->
                {
                    moved|=group!=null&&group.isMoving();
                    if(group!=null&&!group.isMoving()&&S20PhysicalElevatorDirector.hasAuthoredCabinAt(level,new BlockPos(12,-566,253))&&timer>80)
                    {
                        // The physical car arrives before its two door systems
                        // finish their normal opening hand-off.
                        if(++arrivalTicks<40)return;
                        check("dogma_egress_call_started_real_trip",moved);
                        for(double z=253.5;z<=259.5;z+=.5)
                            check("dogma_open_threshold_"+z,level.noCollision(player,new AABB(12.2,-565.99,z-.3,12.8,-564.2,z+.3)));
                        player.teleportTo(level,12.5,-566,253.5,90,0);next("dogma_boarding");
                    }
                    if(timer>700)throw new IllegalStateException("Dogma outside call failed");
                }
                case 2 ->
                {
                    if(timer<40)return;
                    S20MovingElevatorsAdapter.prepareDoorsBeforeUse(player,new BlockPos(10,-565,253));
                    group.onDisplayPress(-566,group.getFloorNumber(-448)-group.getFloorNumber(-566),player);
                    check("dogma_leave_without_card",group.isMoving());next("dogma_passenger_ascent");
                }
                case 3 ->
                {
                    if(group!=null&&!group.isMoving()&&timer>230)
                    {
                        check("dogma_passenger_arrived",Math.abs(player.getY()+448)<.8);
                        check("dogma_admission_still_requires_card",!S20MovingElevatorsAdapter.allowDisplayPress(group,-448,group.getFloorNumber(-566)-group.getFloorNumber(-448),player));
                        player.setItemInHand(InteractionHand.MAIN_HAND,ModItems.TERMINAL_DOGMA_ACCESS_CARD.get().getDefaultInstance());
                        check("dogma_admission_accepts_card",S20MovingElevatorsAdapter.allowDisplayPress(group,-448,group.getFloorNumber(-566)-group.getFloorNumber(-448),player));
                        player.setItemInHand(InteractionHand.MAIN_HAND,ItemStack.EMPTY);
                        for(int v=0;v<3;v++)EvaLogisticsDirector.loadControlTarget(level,v);
                        TrainingPilotDirector.stop(level,1);EvaLogisticsDirector.forceReset(level,1);
                        player.teleportTo(level,30.5,-394,-123.5,0,0);next("human_plug_boarding");
                    }
                    if(timer>700)throw new IllegalStateException("Dogma passenger ascent timed out");
                }
                case 4 ->
                {
                    if(timer<160)return;var eva=EvaLogisticsDirector.canonicalUnit(level,1);var plug=EntryPlugDirector.canonical(level,1);
                    if(eva==null||plug==null)return;
                    airframe=eva.getUUID();plugId=plug.getUUID();
                    Vec3 hatch=plug.transformPlugMarker(EntryPlugKinematics.HATCH_PORTAL_CENTRE_P);
                    Vec3 outward=plug.getCanonicalTransform().transformVector(EntryPlugKinematics.PILOT_VIEW_FORWARD_P).normalize();
                    Vec3 eye=hatch.add(outward.scale(2.4));Vec3 look=hatch.subtract(eye);
                    float yaw=(float)Math.toDegrees(Math.atan2(-look.x,look.z));
                    float pitch=(float)-Math.toDegrees(Math.atan2(look.y,look.horizontalDistance()));
                    player.teleportTo(level,eye.x,eye.y-player.getEyeHeight(),eye.z,yaw,pitch);
                    ProjectSeele.LOGGER.info("R19 hatch setup: open={} stage={} occupied={} playerRiding={} eye={} portal={} facing={}",plug.isHatchOpen(),plug.getInsertionStage(),plug.isVehicle(),player.isPassenger(),player.getEyePosition(),hatch,player.getViewVector(1));
                    plug.tryBoardFromHatch(player);check("real_player_in_original_plug",plug.getFirstPassenger()==player);
                    var result=EvaLogisticsDirector.requestPrepare(level,1);check("human_prepare_accepted",result.accepted());next("human_preparation");
                }
                case 5 ->
                {
                    var status=EvaLogisticsDirector.status(level,1);
                    if(status.phase().equals("PLUG_FAULT"))throw new IllegalStateException("Plug fault");
                    if(status.phase().equals("SILO_READY"))
                    {
                        check("human_launch_accepted",EvaLogisticsDirector.requestLaunch(level,1).accepted());next("human_catapult");
                    }
                    if(timer>2600)throw new IllegalStateException("Human preparation timeout");
                }
                case 6 ->
                {
                    var eva=EvaLogisticsDirector.canonicalUnit(level,1);
                    if(EvaLogisticsDirector.status(level,1).phase().equals("DEPLOYED"))
                    {
                        check("human_release_has_physical_support",NervSiloDoorEntity.hasClosedSurfaceSupport(level,new BlockPos(30,79,-36)));
                        check("human_original_identity",eva.getUUID().equals(airframe)&&EntryPlugDirector.canonical(level,1).getUUID().equals(plugId));
                        check("human_not_dummy",eva.getPilotEntity()==player&&!eva.isTrainingPilotActive());next("human_free_gravity_hold");
                    }
                    if(timer>900)throw new IllegalStateException("Human catapult timeout");
                }
                case 7 ->
                {
                    var eva=EvaLogisticsDirector.canonicalUnit(level,1);minimumArrivalY=Math.min(minimumArrivalY,eva.getY());
                    check("human_stays_above_surface",eva.getY()>80.8);
                    check("human_free_control",!eva.isNervLogisticsLocked()&&!eva.isLaunchSequenceActive());
                    if(timer>180){check("human_recovery_accepted",EvaLogisticsDirector.requestRecovery(level,1).accepted());next("human_recovery");}
                }
                case 8 ->
                {
                    if(EvaLogisticsDirector.status(level,1).phase().equals("PARKED"))
                    {
                        player.stopRiding();player.teleportTo(level,512.5,81,469.5,0,0);next("native_departure_boards");
                    }
                    if(timer>2200)throw new IllegalStateException("Human recovery timeout");
                }
                case 9 ->
                {
                    if(timer<140)return;
                    Path boardFile=world.getParent().getParent().getParent().resolve("artifacts/world_repair_r19/stations/display_clearance/places.json");
                    JsonArray boards=JsonParser.parseString(Files.readString(boardFile)).getAsJsonObject().getAsJsonArray("boards");
                    int linked=0;JsonArray rows=new JsonArray();
                    for(var item:boards)
                    {
                        var b=item.getAsJsonObject();var pos=b.getAsJsonArray("pos");BlockPos at=new BlockPos(pos.get(0).getAsInt(),pos.get(1).getAsInt(),pos.get(2).getAsInt());level.getChunkAt(at);
                        check("display_entity_"+b.get("id").getAsString(),level.getBlockEntity(at) instanceof StationDepartureBoardBlockEntity);
                        var p=b.getAsJsonArray("platform");var snapshot=NativeStationDepartures.read(new BlockPos(p.get(0).getAsInt(),p.get(1).getAsInt(),p.get(2).getAsInt()));
                        check("native_platform_"+b.get("id").getAsString(),snapshot.platformId()!=-1&&snapshot.clock()>0);linked++;
                        JsonObject row=new JsonObject();row.addProperty("id",b.get("id").getAsString());row.addProperty("platform",snapshot.platformId());row.addProperty("nativeClock",snapshot.clock());row.addProperty("display",String.join(" | ",snapshot.rows()));rows.add(row);
                    }
                    check("all_50_native_boards",linked==50);JsonObject result=new JsonObject();result.add("checks",checks);result.add("departures",rows);if(!BOARDS_ONLY)result.addProperty("minimumHumanArrivalY",minimumArrivalY);
                    Files.writeString(world.resolve("r19_runtime_pass.json"),result.toString());phase="complete";finished=true;
                }
            }
        }
        catch(Exception failure)
        {
            ProjectSeele.LOGGER.error("R19 RUNTIME REVIEW FAILED in "+phase,failure);
            try{Files.writeString(world.resolve("r19_runtime_failure.txt"),phase+"\n"+failure+"\n"+checks);}catch(Exception ignored){}
            finished=true;
        }
    }
}
