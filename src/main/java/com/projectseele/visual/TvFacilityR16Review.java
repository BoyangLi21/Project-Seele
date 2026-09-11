package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.world.*;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.*;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** A complete real dummy/plug/catapult/recovery cycle in a copied commissioned world. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class TvFacilityR16Review
{
    public static final boolean ENABLED="r16-facilities".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean finished,clientReady;
    public static volatile String phase="INITIALIZING",capture="";
    public static volatile int heroId=-1,shot;
    public static volatile int tick,phaseTick;
    public static volatile boolean photographing;
    public static volatile String photo="";
    public static volatile String hatchPhoto="";
    public static volatile net.minecraft.world.phys.Vec3 photoEye,photoTarget;
    public static final Set<String> capturedPhotos=java.util.concurrent.ConcurrentHashMap.newKeySet();
    private static JsonArray photoViews;private static int photoIndex;
    private static ServerLevel level;private static ServerPlayer player;private static Path world;
    private static UUID canonical,plugId;
    private static int state,localTick,lastLcl=44;
    private static double maxY=-1000;
    private static final JsonObject checks=new JsonObject();
    private static final JsonArray transitions=new JsonArray();
    private static String lastPhase="";
    public static boolean controlsSurfaceHatches(ServerLevel request)
    {
        // The isolated all-open inspection owns the controls while the fleet
        // remains safely parked. Normal parked-fleet maintenance must not
        // issue a competing close command during this test.
        return ENABLED&&!finished&&state==9&&level==request;
    }
    private static void check(String id,boolean passed)
    {
        checks.addProperty(id,passed);if(!passed)throw new IllegalStateException(id);
    }
    private static void action(String name,EvaLogisticsDirector.ActionResult result)
    {check(name+"/"+result.message(),result.accepted());}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;
        try
        {
            var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty())return;
            if(world==null)
            {
                world=server.getWorldPath(LevelResource.ROOT).normalize();
                if(!world.getFileName().toString().equals("SEELE_TV_FACILITIES_R16"))throw new IllegalStateException("Disposable review world required");
                player=server.getPlayerList().getPlayers().get(0);level=server.getLevel(FacilitySchemaV2.DIMENSION);
                check("commissioned_tv_geometry",TvLaunchFacility.enabled(level));player.setGameMode(GameType.SPECTATOR);
                player.teleportTo(level,35,-387,-112,0,0);
            }
            tick++;localTick++;
            if(Files.exists(world.resolve("regional_stop_requested")))throw new IllegalStateException("Review stopped");
            if(state==8){photographs();return;}
            if(state==9){hatches();return;}
            if(tick%40==1)for(int v=0;v<3;v++)EvaLogisticsDirector.loadControlTarget(level,v);
            var eva=EvaLogisticsDirector.canonicalUnit(level,1);if(eva==null){if(tick>300)throw new IllegalStateException("Canonical EVA did not load");return;}
            heroId=eva.getId();var status=EvaLogisticsDirector.status(level,1);phase=status.phase();phaseTick=status.ticks();
            if(!phase.equals(lastPhase))
            {
                JsonObject row=new JsonObject();row.addProperty("tick",tick);row.addProperty("phase",phase);row.addProperty("y",eva.getY());transitions.add(row);lastPhase=phase;
                ProjectSeele.LOGGER.info("R16 FACILITY phase={} y={} tick={}",phase,eva.getY(),tick);
            }
            if(canonical==null)
            {
                canonical=eva.getUUID();check("original_unit01_uuid",canonical.toString().equals("972271c6-dd86-472d-938e-4dc3a363f343"));check("initial_parked",phase.equals("PARKED"));
            }
            check("same_airframe_identity",canonical.equals(eva.getUUID()));
            var plug=EntryPlugDirector.canonical(level,1);
            if(plug!=null){if(plugId==null)plugId=plug.getUUID();check("same_plug_identity",plugId.equals(plug.getUUID()));}
            switch(state)
            {
                case 0 ->
                {
                    shot=0;
                    if(localTick>200&&clientReady)
                    {
                        checkObservationRings();
                        check("initial_nine_internal_shutters",countSeals()==9*31*31);
                        var result=TrainingPilotDirector.start(level,1);check("native_dummy_dispatch/"+result.message(),result.accepted());state=1;localTick=0;
                    }
                }
                case 1 ->
                {
                    if(plug!=null&&plug.getFirstPassenger()!=null)
                    {
                        check("dummy_walked_and_boarded",plug.getFirstPassenger() instanceof TrainingPilotEntity);
                        shot=1;capture="entry_plug_insertion";
                        if(localTick>40){action("prepare",EvaLogisticsDirector.requestPrepare(level,1));state=2;localTick=0;}
                    }
                    if(localTick>2400)throw new IllegalStateException("Dummy boarding timeout");
                }
                case 2 ->
                {
                    if(phase.equals("PLUG_FAULT"))throw new IllegalStateException("Native plug fault");
                    if(phase.equals("DRAINING"))
                    {
                        check("native_spinal_lock",EntryPlugDirector.hasLaunchLock(level,1,eva));
                        if(++lastLcl>84){shot=2;capture="eva_catapult_launch";state=3;localTick=0;}
                    }
                }
                case 3 ->
                {
                    shot=phase.equals("TO_SILO")?3:phase.equals("SILO_READY")?4:2;
                    if(phase.equals("TO_SILO"))check("dry_transfer",status.lclLayers()==0);
                    if(phase.equals("SILO_READY"))
                    {
                        if(++lastLcl>145){action("launch",EvaLogisticsDirector.requestLaunch(level,1));state=4;localTick=0;}
                    }
                }
                case 4 ->
                {
                    // Hold the exterior camera before the high-speed ascent so
                    // the destination scenery has time to compile and stream.
                    shot=localTick<14?4:7;
                    if(eva.getLaunchPhase()==EvaUnit01Entity.LAUNCH_ASCENT)
                    {
                        check("all_intermediate_seals_open_before_ascent",countVariantSeals(1)==0);shot=7;
                    }
                    maxY=Math.max(maxY,eva.getY());
                    if(phase.equals("DEPLOYED")){shot=6;state=5;localTick=0;check("surface_arrival",eva.getY()>=80);}
                    if(localTick>600)throw new IllegalStateException("Catapult did not reach surface");
                }
                case 5 ->
                {
                    if(localTick>100){capture="";action("recovery",EvaLogisticsDirector.requestRecovery(level,1));state=6;localTick=0;}
                }
                case 6 ->
                {
                    shot=phase.equals("DESCENDING")?5:1;
                    if(phase.equals("PARKED"))
                    {
                        check("wet_cage_recovered",status.lclLayers()==44);check("full_height_travel",maxY>=81);
                        state=7;localTick=0;
                    }
                }
                case 7 ->
                {
                    if(localTick>100)
                    {
                        check("shutters_resealed",countSeals()==9*31*31);
                        checkHatchGeometry();state=9;localTick=0;
                    }
                }
            }
            // Keep the real client near its camera to stream the actual chunks.
            if(tick%20==0&&state>=3&&state<=6)
            {
                if(state==4&&localTick>=14||state==5)
                    player.teleportTo(level,72,121.4,-100,0,0);
                else player.teleportTo(level,eva.getX()+9,Math.min(133,eva.getY()+55),eva.getZ()-12,0,0);
            }
            if(tick>6500)throw new IllegalStateException("Full facility cycle timeout");
        }
        catch(Exception e){ProjectSeele.LOGGER.error("R16 FACILITY REVIEW FAILED",e);finish(e.toString());}
    }
    private static int countVariantSeals(int variant)
    {
        int count=0,cx=new int[]{-12,30,72}[variant];
        for(int y:new int[]{-332,-192,-52})for(int x=cx-15;x<=cx+15;x++)for(int z=-51;z<=-21;z++)
            if(level.getBlockState(new BlockPos(x,y,z)).is(Blocks.BARRIER))count++;
        return count;
    }
    private static int countSeals(){return countVariantSeals(0)+countVariantSeals(1)+countVariantSeals(2);}
    private static void checkHatchGeometry()
    {
        double maxX=0;
        for(int sample=0;sample<=1000;sample++)
        {
            float open=sample/1000F;var boxes=new ArrayList<AABB>();
            for(int side:new int[]{-1,1})for(int index=0;index<SiloHatchMechanism.PANELS;index++)
            {
                var p=SiloHatchMechanism.panel(index,open);
                double x0=side<0?-p.x()-SiloHatchMechanism.WIDTH:p.x();
                var box=new AABB(x0,p.y(),-16.5,x0+SiloHatchMechanism.WIDTH,p.y()+SiloHatchMechanism.PANEL_TOP,16.5);
                for(var other:boxes)if(box.deflate(.00001).intersects(other))throw new IllegalStateException("Rigid hatch panels intersect at "+open);
                boxes.add(box);maxX=Math.max(maxX,Math.max(Math.abs(box.minX),Math.abs(box.maxX)));
                if(sample==1000)check("open_panel_clear_of_31m_core",box.maxX<=-15.5||box.minX>=15.5);
            }
        }
        check("1001_hatch_poses_without_panel_intersection",true);
        check("independent_neighbour_hatches_clear",2*maxX<42&&2*SiloHatchMechanism.CASE_OUTER_X<42);
        check("cassette_outer_clearance_0_6m",42-2*SiloHatchMechanism.CASE_OUTER_X>.599);
    }
    private static void hatches()
    {
        shot=8;phase="HATCH_CLEARANCE";capture="surface_hatch_clearance";
        if(localTick%20==1)player.teleportTo(level,30,153.4,-85,0,0);
        boolean open=localTick>100&&localTick<=220;
        for(int variant=0;variant<3;variant++)NervSiloDoorEntity.reconcile(level,variant,new BlockPos(new int[]{-12,30,72}[variant],79,-36),open?1:0);
        if(localTick==85)hatchPhoto="surface_hatches_closed.png";
        if(localTick==200)
        {
            check("three_surface_hatches_open",countSurfaceSeals()==0);
            hatchPhoto="surface_hatches_open.png";
        }
        if(localTick>300)
        {
            check("three_surface_hatches_resealed",countSurfaceSeals()==3*31*31);
            check("twelve_shutters_resealed",countSeals()==9*31*31);
            check("hatch_closed_and_open_native_photos",capturedPhotos.contains("surface_hatches_closed.png")&&capturedPhotos.contains("surface_hatches_open.png"));
            hatchPhoto="";capture="";
            if(Boolean.getBoolean("projectseele.tvNpcCapture")){try{photoViews=JsonParser.parseString(Files.readString(world.resolve("r16_npc_views.json"))).getAsJsonArray();}catch(Exception e){throw new IllegalStateException(e);}state=8;localTick=0;}
            else finish("");
        }
    }
    private static int countSurfaceSeals()
    {
        int count=0;for(int cx:new int[]{-12,30,72})for(int x=cx-15;x<=cx+15;x++)for(int z=-51;z<=-21;z++)
            if(level.getBlockState(new BlockPos(x,80,z)).is(Blocks.BARRIER))count++;
        return count;
    }
    private static void checkObservationRings()
    {
        for(int cx:new int[]{-12,30,72})
        {
            var probe=net.minecraft.world.entity.EntityType.ZOMBIE.create(level);check("ring_probe_created",probe!=null);probe.setNoAi(true);probe.setNoGravity(true);probe.setPos(cx+.5,-394,-119.5);
            int[][] route={{cx-7,-120},{cx-7,-105},{cx+7,-105},{cx+7,-120},{cx,-120}};
            for(int[] point:route)
            {
                var target=new net.minecraft.world.phys.Vec3(point[0]+.5,-394,point[1]+.5);
                for(int n=0;n<200&&probe.position().distanceToSqr(target)>.000001;n++)
                {
                    var delta=target.subtract(probe.position());probe.move(net.minecraft.world.entity.MoverType.SELF,delta.scale(Math.min(1,.20/delta.length())));
                    check("ring_supported_"+cx,!level.getBlockState(probe.blockPosition().below()).getCollisionShape(level,probe.blockPosition().below()).isEmpty());
                }
                check("ring_native_clear_"+cx+"_"+point[0]+"_"+point[1],probe.position().distanceToSqr(target)<.000001);
            }
            probe.discard();
        }
    }
    private static net.minecraft.world.phys.Vec3 point(JsonArray p){return new net.minecraft.world.phys.Vec3(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble());}
    private static void photographs()
    {
        if(photoIndex>=photoViews.size()){check("npc_scene_photographs",capturedPhotos.size()>=4);finish("");return;}
        var view=photoViews.get(photoIndex).getAsJsonObject();String file=view.get("file").getAsString();
        if(localTick==1)
        {
            check("valid_photo_filename",file.matches("[A-Za-z0-9_]+\\.png"));photo="";photoEye=point(view.getAsJsonArray("eye"));photoTarget=point(view.getAsJsonArray("target"));photographing=true;
            player.teleportTo(level,photoEye.x,photoEye.y-1.62,photoEye.z,0,0);level.setDayTime(6000);
        }
        if(localTick>220)photo=file;
        if(capturedPhotos.contains(file)){photo="";photoIndex++;localTick=0;}
        if(localTick>1400)throw new IllegalStateException("NPC photograph timeout "+file);
    }
    private static void finish(String error)
    {
        finished=true;capture="";var out=new JsonObject();out.addProperty("error",error);out.addProperty("ticks",tick);out.add("checks",checks);out.add("transitions",transitions);
        try{if(world!=null)Files.writeString(world.resolve("r16_facility_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(out));}catch(Exception e){ProjectSeele.LOGGER.error("R16 report write failed",e);}
    }
    private TvFacilityR16Review() {}
}
