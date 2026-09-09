package com.projectseele.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.GameRules;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** A disposable rendering fixture, never run against the user's TV world. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class AngelModelR10Review
{
    private static boolean prepared;
    private static com.projectseele.entity.EvaUnit01Entity hero;
    private static com.projectseele.entity.SachielEntity angel;
    public static void seek(float seconds)
    {
        if(hero==null||angel==null||seconds<0||seconds>23)throw new IllegalStateException("Invalid choreography review seek");
        int tick=Math.round(seconds*20);hero.firstBattleSignals().advance(hero,tick,angel.getId());angel.firstBattleSignals().advance(angel,tick,hero.getId());
        com.projectseele.entity.FirstBattleClip.applyKinematics(hero);com.projectseele.entity.FirstBattleClip.applyKinematics(angel);
        ProjectSeele.LOGGER.info("R10 CHOREOGRAPHY SEEK seconds={} hero={} angel={}",seconds,hero.position(),angel.position());
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        String mode=System.getProperty("projectseele.regionalBuild","");
        if(!(mode.equals("r10-models")||mode.equals("r10-choreography"))||prepared||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty())return;
        if(!server.getWorldPath(LevelResource.ROOT).normalize().getFileName().toString().equals("SEELE_ANGEL_MODEL_REVIEW_R10"))throw new IllegalStateException("Model review is laboratory-only");
        var level=server.overworld();prepared=true;
        level.getGameRules().getRule(GameRules.RULE_DOMOBSPAWNING).set(false,server);
        level.getGameRules().getRule(GameRules.RULE_MOBGRIEFING).set(false,server);
        level.getGameRules().getRule(GameRules.RULE_DAYLIGHT).set(false,server);level.setDayTime(6000);
        var oldActors=new java.util.ArrayList<Mob>();
        for(var e:level.getAllEntities())if(e instanceof Mob mob)oldActors.add(mob);
        for(var e:oldActors)e.discard();
        for(BlockPos p:BlockPos.betweenClosed(-128,-61,-70,128,-61,100))level.setBlock(p,Blocks.SMOOTH_STONE.defaultBlockState(),2);
        if(mode.equals("r10-choreography"))
        {
            hero=ModEntities.EVA_UNIT01.get().create(level);angel=ModEntities.SACHIEL.get().create(level);
            hero.prepareForMotionLab();hero.moveTo(0,-60,0,0,0);angel.moveTo(0,-60,34,180,0);angel.setNoAi(true);angel.setSilent(true);
            level.addFreshEntity(hero);level.addFreshEntity(angel);
            var spec=new com.projectseele.entity.FirstBattleSignals.Spec(new net.minecraft.world.phys.Vec3(0,-60,0),0,0,180,34,0);
            hero.beginFirstBattle(spec,angel.getId());angel.beginFirstBattle(spec,hero.getId());seek(0);return;
        }
        Mob[] actors={ModEntities.SACHIEL.get().create(level),ModEntities.SHAMSHEL.get().create(level),ModEntities.ZERUEL.get().create(level),ModEntities.ISRAFEL.get().create(level)};
        for(int i=0;i<actors.length;i++)
        {
            Mob actor=actors[i];actor.moveTo(-90+i*60,-60,0,0,0);actor.yBodyRot=actor.yHeadRot=0;actor.setNoAi(true);actor.setNoGravity(true);actor.setSilent(true);actor.setPersistenceRequired();level.addFreshEntity(actor);
            ProjectSeele.LOGGER.info("R10 MODEL FIXTURE {} id={} bounds={}",actor.getType(),actor.getId(),actor.getBoundingBox());
        }
    }
}
