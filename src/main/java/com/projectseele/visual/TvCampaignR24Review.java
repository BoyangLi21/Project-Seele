package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.event.*;
import com.projectseele.registry.*;
import com.projectseele.world.*;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.*;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Isolated integration review using the original canonical EVA and capsule. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class TvCampaignR24Review
{
    private static final String MODE=System.getProperty("projectseele.regionalBuild","");
    private static final boolean SAVE_MODE=MODE.equals("r24-campaign-save"),RESUME_MODE=MODE.equals("r24-campaign-resume");
    public static final boolean ENABLED=MODE.equals("r24-campaign")||SAVE_MODE||RESUME_MODE;
    public static volatile boolean ready,finished;
    public static volatile String input="",photo="";
    public static volatile int entityId=-1;
    public static final Set<String> inputs=java.util.concurrent.ConcurrentHashMap.newKeySet(),photos=java.util.concurrent.ConcurrentHashMap.newKeySet();
    public static volatile float maxWhipRigError;
    public static volatile int whipRigSamples;
    public static volatile boolean clientBattleActive,clientEnemyTracked;
    public static volatile String clientView="";
    private static int stage,timer,age,sweepFrames;
    private static Path world;
    private static ServerLevel level;
    private static ServerPlayer player;
    private static EvaUnit01Entity eva;
    private static UUID angel;
    private static UUID evaUuid,plugUuid;
    private static CompoundTag before;
    private static boolean previouslyCompleted;
    private static boolean originalInvulnerable,ending,capturedOriginal;
    private static int priorRecoveryReady=-1;
    private static float originalHealth;
    private static net.minecraft.world.phys.Vec3 surface;
    private static String failure="";
    private static final JsonObject checks=new JsonObject();
    private static JsonObject restart;
    private static final TicketType<net.minecraft.world.level.ChunkPos> REVIEW_ACTOR_TICKET=TicketType.create("r24_review_actor",Comparator.comparingLong(net.minecraft.world.level.ChunkPos::toLong),100);
    private static void check(String name,boolean value){checks.addProperty(name,value);if(!value)throw new IllegalStateException(name);}
    private static void next(int value){stage=value;timer=0;photo="";input="";ProjectSeele.LOGGER.info("R24 CAMPAIGN REVIEW phase={}",value);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||!ready||finished||event.phase!=TickEvent.Phase.END)return;
        try
        {
            var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty())return;
            if(world==null)
            {
                world=server.getWorldPath(LevelResource.ROOT).normalize();check("isolated_world",world.getFileName().toString().equals("SEELE_R24_TV_REVIEW"));
                level=server.getLevel(FacilitySchemaV2.DIMENSION);player=server.getPlayerList().getPlayers().get(0);
                var data=TvCampaignSavedData.get(level);
                if(RESUME_MODE)
                {
                    restart=JsonParser.parseString(Files.readString(world.resolve("r24_campaign_reload_checkpoint.json"))).getAsJsonObject();
                    check("same_saved_pilot",player.getUUID().toString().equals(restart.get("pilot").getAsString()));
                    check("saved_second_chapter_active",data.chapter==1&&data.active.equals("shamshel")&&data.completed.equals(List.of("sachiel")));
                    before=net.minecraft.nbt.TagParser.parseTag(restart.get("original_campaign").getAsString());
                    evaUuid=UUID.fromString(restart.get("eva").getAsString());plugUuid=UUID.fromString(restart.get("plug").getAsString());
                    originalHealth=restart.get("original_health").getAsFloat();originalInvulnerable=restart.get("original_invulnerable").getAsBoolean();
                    previouslyCompleted=restart.get("previously_completed").getAsBoolean();surface=new net.minecraft.world.phys.Vec3(30.5,81,-35.5);stage=-5;
                }
                else
                {
                    before=data.save(new CompoundTag());check("idle_campaign_fixture",data.active.isEmpty());
                    data.chapter=0;data.completed.clear();data.clear("");
                    previouslyCompleted=FirstBattleSavedData.get(level).completedPilots.contains(player.getUUID());
                    player.stopRiding();player.setGameMode(GameType.CREATIVE);player.getInventory().add(new net.minecraft.world.item.ItemStack(ModItems.NERV_EMPLOYEE_CARD.get()));
                    player.teleportTo(level,27.5,-407,282.5,0,0);EvaLogisticsDirector.loadControlTarget(level,1);TrainingPilotDirector.stop(level,1);stage=-4;
                }
            }
            age++;timer++;level.resetEmptyTime();if(stage!=90)check("bounded_review",age<14000);
            var data=TvCampaignSavedData.get(level);
            if(stage==-5)
            {
                if(timer>600)throw new IllegalStateException("Saved campaign actors did not reattach");
                if(data.lastPosition!=null)
                {
                    var chunk=new net.minecraft.world.level.ChunkPos(data.lastPosition);
                    level.getChunkSource().addRegionTicket(REVIEW_ACTOR_TICKET,chunk,2,chunk);level.getChunk(data.lastPosition);
                }
                eva=EvaLogisticsDirector.canonicalUnit(level,1);var plug=EntryPlugDirector.canonical(level,1);
                var enemy=data.angel==null?null:level.getEntity(data.angel);
                if(eva==null||plug==null||enemy==null||timer<100)return;
                angel=data.angel;capturedOriginal=true;
                check("saved_eva_identity",eva.getUUID().equals(evaUuid));check("saved_plug_identity",plug.getUUID().equals(plugUuid));
                check("saved_angel_identity",enemy.getUUID().toString().equals(restart.get("angel").getAsString()));
                check("saved_native_ride_chain",EvaPilotResolver.controlTarget(player)==eva);
                check("saved_angel_type",enemy instanceof ShamshelEntity);
                check("saved_field_value",Math.abs(((ShamshelEntity)enemy).getAtField()-restart.get("field").getAsFloat())<.001F);
                check("saved_health_value",Math.abs(((ShamshelEntity)enemy).getHealth()-restart.get("health").getAsFloat())<.001F);
                var nearby=level.getEntitiesOfClass(ShamshelEntity.class,enemy.getBoundingBox().inflate(180),q->q.getTags().contains("seele_tv_shamshel_r24"));
                checks.addProperty("nearby_campaign_targets",nearby.stream().map(q->q.getUUID().toString()).toList().toString());
                check("no_duplicate_campaign_target",nearby.size()==1);
                capturedOriginal=true;eva.setInvulnerable(true);entityId=enemy.getId();next(5);return;
            }
            if(stage==-4)
            {
                // A failed prior isolated review may have exited while its
                // original unit was deployed. Return that same assembly via
                // the real recovery sequence before beginning another test.
                if(timer%20==0)
                {
                    EvaLogisticsDirector.loadControlTarget(level,1);
                    for(int x=21;x<=23;x++)for(int z=-25;z<=-23;z++)
                    {
                        var chunk=new net.minecraft.world.level.ChunkPos(x,z);
                        level.getChunkSource().addRegionTicket(REVIEW_ACTOR_TICKET,chunk,2,chunk);level.getChunk(x,z);
                    }
                }
                eva=EvaLogisticsDirector.canonicalUnit(level,1);if(eva==null||timer<100)return;
                String phase=EvaLogisticsDirector.status(level,1).phase();
                if(phase.equals("PARKED")){next(-3);return;}
                if(phase.equals("DEPLOYED")&&!eva.isLaunchSequenceActive())
                {
                    if(priorRecoveryReady<0)
                    {
                        surface=new net.minecraft.world.phys.Vec3(30.5,81,-35.5);relocate(surface,EvaUnit01Entity.SILO_BAY_YAW);priorRecoveryReady=timer+30;return;
                    }
                    if(timer>=priorRecoveryReady)
                    {
                        var motion=eva.getDeltaMovement();boolean grounded=eva.onGround();
                        checks.addProperty("grounded_recovery_motion",motion.toString());
                        try
                        {
                            check("grounded_recovery_motion_accepted",EvaLogisticsDirector.recoveryMotionSettled(eva));
                            eva.setDeltaMovement(.1,motion.y,0);check("moving_recovery_rejected",!EvaLogisticsDirector.recoveryMotionSettled(eva));
                            eva.setDeltaMovement(0,.1,0);check("rising_recovery_rejected",!EvaLogisticsDirector.recoveryMotionSettled(eva));
                            eva.setDeltaMovement(0,-1,0);check("falling_recovery_rejected",!EvaLogisticsDirector.recoveryMotionSettled(eva));
                            eva.setOnGround(false);eva.setDeltaMovement(0,-.1764,0);check("unsupported_recovery_rejected",!EvaLogisticsDirector.recoveryMotionSettled(eva));
                        }
                        finally{eva.setOnGround(grounded);eva.setDeltaMovement(motion);}
                        var outcome=EvaLogisticsDirector.requestRecovery(level,1);
                        checks.addProperty("unfinished_review_recovery_message",outcome.message());check("unfinished_review_recovery",outcome.accepted());
                    }
                }
                else if(phase.equals("PLUG_FAULT"))EvaLogisticsDirector.requestCancel(level,1);
                if(timer>5000)throw new IllegalStateException("Prior review recovery stalled at "+phase);
                return;
            }
            if(stage==-3)
            {
                if(timer%20==0)EvaLogisticsDirector.loadControlTarget(level,1);
                eva=EvaLogisticsDirector.canonicalUnit(level,1);var plug=EntryPlugDirector.canonical(level,1);
                if(eva==null||plug==null||timer<100)return;
                check("original_parked_unit",EvaLogisticsDirector.status(level,1).phase().equals("PARKED"));evaUuid=eva.getUUID();plugUuid=plug.getUUID();
                originalHealth=eva.getHealth();originalInvulnerable=eva.isInvulnerable();capturedOriginal=true;eva.setInvulnerable(true);entityId=eva.getId();
                var hatch=plug.transformPlugMarker(EntryPlugKinematics.HATCH_PORTAL_CENTRE_P);var outward=plug.getCanonicalTransform().transformVector(EntryPlugKinematics.PILOT_VIEW_FORWARD_P).normalize();
                var eye=hatch.add(outward.scale(2.4));var look=hatch.subtract(eye);
                player.teleportTo(level,eye.x,eye.y-player.getEyeHeight(),eye.z,(float)Math.toDegrees(Math.atan2(-look.x,look.z)),(float)-Math.toDegrees(Math.atan2(look.y,look.horizontalDistance())));
                plug.tryBoardFromHatch(player);check("original_hatch_boarding",plug.getFirstPassenger()==player);
                var result=EvaLogisticsDirector.requestPrepare(level,1);check("native_prepare",result.accepted());next(-2);return;
            }
            if(stage==-2)
            {
                String phase=EvaLogisticsDirector.status(level,1).phase();check("prepare_no_fault",!phase.equals("PLUG_FAULT"));
                if(phase.equals("SILO_READY")){check("native_launch",EvaLogisticsDirector.requestLaunch(level,1).accepted());next(-1);}return;
            }
            if(stage==-1)
            {
                if(!EvaLogisticsDirector.status(level,1).phase().equals("DEPLOYED")||eva.isLaunchSequenceActive())return;
                surface=eva.position();check("canonical_surface_pilot",EvaPilotResolver.controlTarget(player)==eva);
                var position=eva.position();var motion=eva.getDeltaMovement();boolean ground=eva.onGround();
                try
                {
                    eva.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);check("stationary_surface_supported",EvaLogisticsDirector.recoveryMotionSettled(eva));
                    eva.setPos(position.add(0,4,0));eva.setOnGround(true);check("stale_ground_bit_without_floor_rejected",!EvaLogisticsDirector.recoveryMotionSettled(eva));
                }
                finally{eva.setPos(position);eva.setDeltaMovement(motion);eva.setOnGround(ground);}
                next(0);return;
            }
            if(stage==90){cleanupTick();return;}
            if(stage==0&&timer>70)
            {
                var previous=FirstBattleSavedData.get(level);
                if(previous.missionOwner!=null||previous.active!=null){if(timer>600)throw new IllegalStateException("Previous isolated encounter did not retire");return;}
                check("radio_contact",StaffConversationR24.contact(player,"美里")==1);next(1);input="briefing";return;
            }
            if(stage==1)
            {
                if(!inputs.contains("briefing"))return;photo="tv_first_briefing";
                if(photos.contains(photo)){next(2);input="accept";}return;
            }
            if(stage==2)
            {
                if(!inputs.contains("accept")||data.active.isEmpty())
                {if(timer>120)throw new IllegalStateException("UI dispatch was not accepted");return;}
                if(timer<50)return;check("dispatch_does_not_spawn_at_distance",data.angel==null);
                check("duplicate_dispatch_rejected",TvCampaignDirector.begin(player)==0);
                next(3);input="close";
                relocate(new net.minecraft.world.phys.Vec3(356.5,81,-459.5),0);return;
            }
            if(stage==3)
            {
                if(data.angel==null)return;angel=data.angel;
                if(timer%20==0)ProjectSeele.LOGGER.info("R24 FIRST APPROACH eva={} player={} target={} ticking={}",eva.position(),player.position(),level.getEntity(angel),level.isPositionEntityTicking(new BlockPos(356,81,-426)));
                if(level.getEntity(angel)==null&&timer<90)return;
                check("bound_first_angel",level.getEntity(angel) instanceof SachielEntity);
                var enemy=(SachielEntity)level.getEntity(angel);enemy.setNoAi(true);enemy.setTarget(null);enemy.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
                check("wrong_target_not_credited",!data.finish("sachiel",player.getUUID(),UUID.randomUUID()));
                // The fixture teleports from the silo. Allow real destination
                // meshes to settle before recording, as normal approach does.
                if(timer>300)
                {
                    check("actual_floor_support",FirstBattleDirector.stableSupport(eva));
                    enemy.setFirstBattleField(0);enemy.setHealth(enemy.getMaxHealth()*.25F);
                    if(FirstBattleSavedData.get(level).active!=null||FirstBattleDirector.tryStart(enemy,eva,false)){next(4);return;}
                }
                if(timer>700)throw new IllegalStateException("First battle entry conditions not met: ground="+eva.onGround()+" eva="+eva.position()+" angel="+enemy.position());
                return;
            }
            if(stage==4)
            {
                if(timer>150&&timer<240)photo="first_battle_director";
                if(data.chapter!=1)return;check("native_first_battle_callback",data.completed.equals(List.of("sachiel"))&&data.active.isEmpty());
                next(45);return;
            }
            if(stage==45)
            {
                // The test relocation is not a normal walk. Wait until the
                // pilot received the end-of-film state before correcting the
                // local vehicle, otherwise that old cinematic can overwrite it.
                if(timer>200&&clientBattleActive)throw new IllegalStateException("Client retained completed cinematic state for more than ten seconds");
                if(timer<40||clientBattleActive)return;
                check("client_received_control_return",!clientBattleActive);
                relocate(new net.minecraft.world.phys.Vec3(356.5,81,-459.5),0);
                if(timer<60)return;
                check("second_chapter_dispatch",TvCampaignDirector.begin(player)==1);next(5);return;
            }
            if(stage==5)
            {
                if(data.angel==null)return;angel=data.angel;if(level.getEntity(angel)==null&&timer<90)return;
                check("second_angel_is_shamshel",level.getEntity(angel) instanceof ShamshelEntity);
                var enemy=(ShamshelEntity)level.getEntity(angel);entityId=enemy.getId();
                if(timer%40==0)ProjectSeele.LOGGER.info("R24 SHAMSHEL VIEW server_hero={} server_enemy={} tracked={} client={}",eva.position(),enemy.position(),clientEnemyTracked,clientView);
                if(enemy.isSweeping())sweepFrames++;
                if(timer>50)photo="shamshel_approach";
                if(timer>120&&enemy.isSweeping())photo="shamshel_whip";
                if(timer<260)return;
                check("native_whip_cycle",sweepFrames>20);
                var tag=new CompoundTag();enemy.saveWithoutId(tag);var copy=ModEntities.SHAMSHEL.get().create(level);copy.load(tag);
                var again=new CompoundTag();copy.saveWithoutId(again);
                check("whip_save_fields",tag.getInt("SweepAge")==again.getInt("SweepAge")&&tag.getInt("SweepCooldown")==again.getInt("SweepCooldown")&&tag.get("SweepHits").equals(again.get("SweepHits")));
                check("field_save",copy.getAtField()==enemy.getAtField());
                check("same_second_identity",angel.equals(data.angel));
                if(SAVE_MODE)
                {
                    var saved=data.save(new CompoundTag());
                    check("saved_riding_intent",saved.getBoolean("WasRiding")&&saved.getUUID("PilotEva").equals(evaUuid)&&saved.getUUID("PilotPlug").equals(plugUuid));
                    saved.putBoolean("WasRiding",false);check("voluntary_exit_has_no_auto_resume",!TvCampaignSavedData.load(saved).resumePending);
                    var checkpoint=new JsonObject();checkpoint.addProperty("pilot",player.getUUID().toString());checkpoint.addProperty("eva",evaUuid.toString());checkpoint.addProperty("plug",plugUuid.toString());checkpoint.addProperty("angel",angel.toString());
                    checkpoint.addProperty("field",enemy.getAtField());checkpoint.addProperty("health",enemy.getHealth());checkpoint.addProperty("original_campaign",before.toString());
                    checkpoint.addProperty("original_health",originalHealth);checkpoint.addProperty("original_invulnerable",originalInvulnerable);checkpoint.addProperty("previously_completed",previouslyCompleted);
                    Files.writeString(world.resolve("r24_campaign_reload_checkpoint.json"),new GsonBuilder().setPrettyPrinting().create().toJson(checkpoint));
                    check("checkpoint_written_for_real_jvm_restart",true);writeReport("");return;
                }
                enemy.hurt(level.damageSources().mobAttack(eva),700);check("melee_neutralizes_field",enemy.getAtField()==0);
                enemy.hurt(level.damageSources().mobAttack(eva),4000);next(6);return;
            }
            if(stage==6)
            {
                if(data.chapter!=2)return;
                check("native_second_death_callback",data.completed.equals(List.of("sachiel","shamshel")));
                check("planned_chapter_cannot_start",TvCampaignDirector.begin(player)==0&&data.active.isEmpty());
                checks.addProperty("whip_visible_rig_error_blocks",maxWhipRigError);checks.addProperty("whip_rig_samples",whipRigSamples);check("shared_whip_rig",whipRigSamples>10&&maxWhipRigError<.02);
                check("saved_progress_round_trip",TvCampaignSavedData.load(data.save(new CompoundTag())).completed.equals(data.completed));
                finish("");
            }
        }
        catch(Exception error){ProjectSeele.LOGGER.error("R24 campaign review failed",error);finish(error.toString());}
    }
    private static void finish(String error)
    {
        if(ending){writeReport(failure.isEmpty()?error:failure+"; cleanup: "+error);return;}
        ending=true;failure=error;
        if(level!=null&&player!=null)
        {
            if(!TvCampaignSavedData.get(level).active.isEmpty())TvCampaignDirector.cancel(player);
            FirstBattleMission.cancel(player);
            if(angel!=null&&level.getEntity(angel) instanceof net.minecraft.world.entity.LivingEntity enemy)enemy.discard();
            if(!previouslyCompleted)FirstBattleSavedData.get(level).completedPilots.remove(player.getUUID());
            FirstBattleSavedData.get(level).setDirty();
            if(before!=null)
            {
                var restored=TvCampaignSavedData.load(before);var data=TvCampaignSavedData.get(level);
                data.chapter=restored.chapter;data.owner=restored.owner;data.angel=restored.angel;data.active=restored.active;data.phase=restored.phase;data.notice=restored.notice;data.lastPosition=restored.lastPosition;
                data.pilotEva=restored.pilotEva;data.pilotPlug=restored.pilotPlug;data.wasRiding=restored.wasRiding;data.resumePending=restored.resumePending;data.resumeTicks=0;
                data.completed.clear();data.completed.addAll(restored.completed);data.setDirty();
            }
            if(eva!=null&&capturedOriginal){eva.setInvulnerable(originalInvulnerable);eva.setHealth(originalHealth);}
        }
        next(90);
    }
    private static void relocate(net.minecraft.world.phys.Vec3 pos,float yaw)
    {
        level.getChunk(BlockPos.containing(pos));eva.moveOnNervCarrier(pos.x,pos.y,pos.z,yaw);eva.setNoGravity(false);eva.setOnGround(true);
        level.getChunkSource().broadcastAndSend(eva,new net.minecraft.network.protocol.game.ClientboundTeleportEntityPacket(eva));
        com.projectseele.network.SeeleNetwork.CHANNEL.send(net.minecraftforge.network.PacketDistributor.PLAYER.with(()->player),new com.projectseele.network.ClientboundEvaArrivalSyncPacket(eva.getId(),pos.x,pos.y,pos.z,yaw,0));
    }
    private static void cleanupTick()
    {
        if(level==null||eva==null){writeReport(failure);return;}
        String phase=EvaLogisticsDirector.status(level,1).phase();
        if(phase.equals("PARKED"))
        {
            if(capturedOriginal)check("original_identity_after_return",eva.getUUID().equals(evaUuid)&&EntryPlugDirector.canonical(level,1).getUUID().equals(plugUuid));
            player.stopRiding();player.teleportTo(level,27.5,-407,282.5,0,0);writeReport(failure);return;
        }
        if(phase.equals("DEPLOYED")&&!eva.isLaunchSequenceActive())
        {
            if(surface==null)surface=eva.position();
            if(timer%40==1)relocate(surface,EvaUnit01Entity.SILO_BAY_YAW);
            if(timer%40==30)check("native_recovery",EvaLogisticsDirector.requestRecovery(level,1).accepted());
        }
        else if(phase.equals("SILO_READY"))EvaLogisticsDirector.requestLaunch(level,1);
        else if(phase.equals("PLUG_FAULT"))EvaLogisticsDirector.requestCancel(level,1);
        if(timer>5000)throw new IllegalStateException("Native cleanup stalled at "+phase);
    }
    private static void writeReport(String error)
    {
        var report=new JsonObject();report.addProperty("passed",error.isEmpty());report.addProperty("error",error);report.addProperty("stage",stage);report.addProperty("ticks",age);report.add("checks",checks);
        report.addProperty("fixture",SAVE_MODE?"Real shutdown checkpoint with original ridden EVA and live Shamshel; return and original campaign restoration happen in the separate resume JVM":"original EVA and capsule through native launch/recovery; explicit test relocation and controlled test damage; campaign progress restored");
        try{Files.writeString(world.resolve(RESUME_MODE?"r24_campaign_resume_review.json":SAVE_MODE?"r24_campaign_save_review.json":"r24_campaign_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception ignored){}
        finished=true;
    }
    private TvCampaignR24Review(){}
}
