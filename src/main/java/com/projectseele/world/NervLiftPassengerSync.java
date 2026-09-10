package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.supermartijn642.movingelevators.blocks.ControllerBlockEntity;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.*;
import net.minecraftforge.fml.common.Mod;
import java.util.*;

/** Corrects stale client passenger positions after a stall on the command rear lift. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class NervLiftPassengerSync
{
    private static final Map<ServerLevel,Map<String,Riders>> LEVELS=new WeakHashMap<>();
    private static final class Riders
    {
        final Map<UUID,Double> offsets=new HashMap<>();boolean moving;
    }
    @SubscribeEvent(priority=EventPriority.HIGH)
    public static void tick(TickEvent.ServerTickEvent event)
    {
        if(event.phase!=TickEvent.Phase.END||!net.minecraftforge.fml.ModList.get().isLoaded("movingelevators"))return;
        var level=event.getServer().getLevel(FacilitySchemaV2.DIMENSION);
        if(level==null||!FacilityWorldPolicy.isS20Rebuild(event.getServer()))return;
        var groups=LEVELS.computeIfAbsent(level,l->new HashMap<>());
        for(var spec:S20PhysicalElevatorDirector.s20Lifts(level))
        {
            if(!spec.id().equals(S20PhysicalElevatorDirector.commandRearLift().id()))continue;
            var base=S20MovingElevatorsAdapter.controllerPosition(spec,spec.lower());
            if(!level.hasChunkAt(base)||!(level.getBlockEntity(base) instanceof ControllerBlockEntity controller))continue;
            var group=controller.getGroup();if(group==null)continue;var riders=groups.computeIfAbsent(spec.id(),s->new Riders());
            double x=spec.lower().cabinCentre().getX()+.5,z=spec.lower().cabinCentre().getZ()+.5,half=Math.min(group.getCageSizeX(),group.getCageSizeZ())*.5;
            var nearby=level.players().stream().filter(p->p.isAlive()&&!p.isSpectator()&&!p.isPassenger()&&!p.getAbilities().flying&&Math.abs(p.getX()-x)<half&&Math.abs(p.getZ()-z)<half).toList();
            riders.offsets.keySet().retainAll(nearby.stream().map(ServerPlayer::getUUID).collect(java.util.stream.Collectors.toSet()));
            if(nearby.isEmpty()){riders.offsets.clear();riders.moving=group.isMoving();continue;}
            if(group.isMoving())
            {
                double floor=group.getCurrentY();
                for(var player:nearby)if(riders.offsets.containsKey(player.getUUID()))correct(player,floor+riders.offsets.get(player.getUUID()),spec.id());
                riders.moving=true;continue;
            }
            if(!riders.moving&&event.getServer().getTickCount()%5!=0)continue;
            var landing=spec.stops().stream().filter(s->level.hasChunkAt(s.cabinCentre())&&S20PhysicalElevatorDirector.hasAuthoredCabinAt(level,s.cabinCentre())).findFirst();
            if(landing.isEmpty()){riders.offsets.clear();riders.moving=false;continue;}
            double floor=landing.get().walkY();
            if(riders.moving)for(var player:nearby)if(riders.offsets.containsKey(player.getUUID()))correct(player,floor,spec.id());
            riders.offsets.clear();riders.moving=false;
            for(var player:nearby)
            {
                double offset=player.getY()-floor;
                if(offset>=-.2&&offset<=1.5)riders.offsets.put(player.getUUID(),Math.max(0,offset));
            }
        }
    }
    private static void correct(ServerPlayer player,double expected,String lift)
    {
        double error=player.getY()-expected;
        // Preserve ordinary walking and jumping. Only a position which has
        // escaped the moving floor/ceiling is reconciled with the server car.
        if(error>=-1.0&&error<=3.4)return;
        player.teleportTo(player.serverLevel(),player.getX(),expected,player.getZ(),player.getYRot(),player.getXRot());
        player.setDeltaMovement(Vec3.ZERO);player.resetFallDistance();player.setOnGround(true);
        ProjectSeele.LOGGER.debug("Lift passenger reconciled lift={} error={}",lift,error);
    }
    private NervLiftPassengerSync(){}
}
