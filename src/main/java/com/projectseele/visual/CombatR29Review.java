package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.entity.*;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.server.level.*;
import net.minecraft.world.level.GameType;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Rendered live attack/recoil fixture. Only temporary actors, never the registered fleet. */
@Mod.EventBusSubscriber(modid="projectseele")
public final class CombatR29Review
{
    public static final boolean R30="r30-combat-feedback".equals(System.getProperty("projectseele.regionalBuild",""));
    public static final boolean ENABLED=R30||"r29-combat".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean ready,done,sceneReady;
    public static volatile int age,evaId;
    public static volatile double maxHandError,maxWhipError;
    public static volatile int handSamples,whipSamples,recoilSamples;
    public static volatile String photo="";
    private static EvaUnit01Entity eva;private static SachielEntity angel;private static ShamshelEntity whip;private static ServerPlayer player;
    private static UNTransportEntity plane;
    private static final Vec3 ORIGIN=new Vec3(32.5,81,195.5);
    private static float initialHealth;private static Vec3 initialPosition;private static double maximumDisplacement;
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e)
    {
        if(!ENABLED||!ready||done||!R30&&!ShamshelContactR24Review.completed||e.phase!=TickEvent.Phase.END)return;
        var server=e.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals(R30?"SEELE_FIELD_R30_REVIEW":"SEELE_FIELD_R29_REVIEW"))throw new IllegalStateException("Combat review world boundary");
        var level=server.getLevel(FacilitySchemaV2.DIMENSION);
        try
        {
            if(eva==null)
            {
                player=server.getPlayerList().getPlayers().get(0);player.stopRiding();player.setGameMode(GameType.SPECTATOR);
                player.teleportTo(level,112.5,135,174.5,0,0);
                for(var stale:level.getEntitiesOfClass(SachielEntity.class,new net.minecraft.world.phys.AABB(ORIGIN,ORIGIN).inflate(1),a->a.isNoAi()))stale.discard();
                // Fleet reconciliation correctly removes unregistered NERV copies.
                // An isolated prototype exercises the shared skeleton and damage code.
                eva=ModEntities.EVA_PROTOTYPE.get().create(level);eva.prepareForMotionLab();eva.setNoAi(!R30);eva.moveTo(32.5,81,217.5,180,0);eva.yBodyRot=180;level.addFreshEntity(eva);evaId=eva.getId();initialHealth=eva.getHealth();initialPosition=eva.position();
                angel=ModEntities.SACHIEL.get().create(level);angel.setNoAi(true);angel.moveTo(ORIGIN.x,ORIGIN.y,ORIGIN.z,0,0);angel.yBodyRot=0;level.addFreshEntity(angel);
            }
            if(!sceneReady)return;
            if(age==0)for(var stale:level.getEntitiesOfClass(SachielEntity.class,new net.minecraft.world.phys.AABB(ORIGIN,ORIGIN).inflate(1),a->a!=angel&&a.isNoAi()))stale.discard();
            age++;
            int sceneAge=R30&&age>=250?(age<330?-1:age-80):age;
            maximumDisplacement=Math.max(maximumDisplacement,eva.position().subtract(initialPosition).horizontalDistance());
            if(R30&&age==260)angel.beginStrike(eva,3);
            if(R30&&age==276)photo="sachiel_left_hook";
            if(sceneAge==100||sceneAge==180)angel.beginStrike(eva,sceneAge==100?1:2);
            if(sceneAge>100&&sceneAge<230&&EvaImpactResponse.sample(eva,1).energy()>.01)recoilSamples++;
            if(sceneAge==113)photo="sachiel_windup";if(sceneAge==120)photo="sachiel_contact";if(sceneAge==132)photo="eva_recovery";
            if(sceneAge==250)
            {
                angel.discard();whip=ModEntities.SHAMSHEL.get().create(level);whip.setNoAi(true);whip.moveTo(ORIGIN.x,ORIGIN.y,ORIGIN.z,0,0);level.addFreshEntity(whip);
            }
            if(sceneAge==290||sceneAge==350)
            {var t=new net.minecraft.nbt.CompoundTag();whip.saveWithoutId(t);t.putInt("SweepAge",0);t.putInt("SweepSide",sceneAge==290?-1:1);t.putFloat("SweepYaw",0);whip.load(t);}
            if(sceneAge==306)photo="shamshel_sweep";
            if(sceneAge==400)
            {
                whip.discard();plane=ModEntities.UN_TRANSPORT.get().create(level);plane.configure(0,false);plane.setPos(eva.position().add(0,84,0));plane.cargo(eva.getId(),true,1);level.addFreshEntity(plane);player.teleportTo(level,132.5,165,97.5,0,0);
            }
            if(sceneAge==445)photo="un_transport_lit_model";
            if(sceneAge==480)
            {
                plane.discard();eva.discard();player.teleportTo(level,32.5,171,-10.5,0,0);
                com.projectseele.network.SeeleNetwork.CHANNEL.send(net.minecraftforge.network.PacketDistributor.PLAYER.with(()->player),new com.projectseele.network.ClientboundBattleFinalePacket(32.5,81,220.5));
            }
            if(sceneAge==505)photo="nuclear_cross_finale";
            if(sceneAge>=740)
            {
                var r=new JsonObject();r.addProperty("hand_samples",handSamples);r.addProperty("max_hand_error_metres",maxHandError);r.addProperty("whip_samples",whipSamples);r.addProperty("max_whip_error_metres",maxWhipError);r.addProperty("recoil_samples",recoilSamples);r.addProperty("actual_hull_damage",initialHealth-eva.getHealth());
                r.addProperty("actual_displacement_metres",maximumDisplacement);
                r.addProperty("passed",(!R30||maximumDisplacement>.3)&&handSamples>20&&maxHandError<.2&&whipSamples>20&&maxWhipError<.05&&recoilSamples>8&&eva.getHealth()<initialHealth);
                Files.writeString(world.resolve(R30?"r30_combat_visual.json":"r29_combat_visual.json"),new GsonBuilder().setPrettyPrinting().create().toJson(r));done=true;
            }
        }
        catch(Exception error)
        {
            if(eva!=null)eva.discard();if(angel!=null)angel.discard();if(whip!=null)whip.discard();if(plane!=null)plane.discard();done=true;
            com.projectseele.ProjectSeele.LOGGER.error("R29 combat visual failed",error);
        }
    }
    private CombatR29Review() {}
}
