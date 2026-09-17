package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.supermartijn642.movingelevators.blocks.ControllerBlockEntity;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.*;
import net.minecraftforge.fml.common.Mod;
import java.util.*;

/** Keeps identified passengers inside the native travelling cabin after packet stalls. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class NervLiftPassengerSync
{
    public static final String GATEWAY="regional_gateway";
    public static List<S20PhysicalElevatorDirector.LiftSpec> managedLifts(ServerLevel level)
    {
        var list=new ArrayList<>(S20PhysicalElevatorDirector.s20Lifts(level));
        if(RegionalGatewayDirector.active(level))list.add(new S20PhysicalElevatorDirector.LiftSpec(GATEWAY,List.of(
                new S20PhysicalElevatorDirector.Landing("地下入构站",new net.minecraft.core.BlockPos(-360,-466,750),net.minecraft.core.Direction.NORTH),
                new S20PhysicalElevatorDirector.Landing("NERV 地面入口",new net.minecraft.core.BlockPos(-360,81,750),net.minecraft.core.Direction.NORTH))));
        return list;
    }
    public static boolean carPresent(ServerLevel level,S20PhysicalElevatorDirector.LiftSpec spec,S20PhysicalElevatorDirector.Landing stop)
    {return spec.id().equals(GATEWAY)?RegionalGatewayDirector.carAt(level,stop.walkY()):S20PhysicalElevatorDirector.hasAuthoredCabinAt(level,stop.cabinCentre());}
    private static final Map<ServerLevel,Map<String,Riders>> LEVELS=new WeakHashMap<>();
    private static final class Riders
    {
        final Set<UUID> passengers=new HashSet<>();
        double previousFloor=Double.NaN;
        boolean moving;
    }

    @SubscribeEvent(priority=EventPriority.HIGH)
    public static void tick(TickEvent.ServerTickEvent event)
    {
        if(event.phase!=TickEvent.Phase.END||!net.minecraftforge.fml.ModList.get().isLoaded("movingelevators"))return;
        ServerLevel level=event.getServer().getLevel(FacilitySchemaV2.DIMENSION);
        if(level==null||!FacilityWorldPolicy.isS20Rebuild(event.getServer()))return;
        Map<String,Riders> groups=LEVELS.computeIfAbsent(level,l->new HashMap<>());
        for(var spec:managedLifts(level))
        {
            var base=S20MovingElevatorsAdapter.controllerPosition(spec,spec.lower());
            if(!level.hasChunkAt(base)||!(level.getBlockEntity(base) instanceof ControllerBlockEntity controller))continue;
            var group=controller.getGroup();if(group==null)continue;
            Riders riders=groups.computeIfAbsent(spec.id(),s->new Riders());
            double floor;AABB bounds;
            if(group.isMoving())
            {
                var cage=group.getCage();if(cage==null)continue;
                bounds=cage.bounds.move(group.getCageAnchorPos(group.getCurrentY()));
                floor=bounds.minY+1.0D;
            }
            else
            {
                var landing=spec.stops().stream().filter(s->level.hasChunkAt(s.cabinCentre())
                        &&carPresent(level,spec,s)).findFirst();
                if(landing.isEmpty()){riders.passengers.clear();riders.moving=false;continue;}
                floor=landing.get().walkY();
                double x=landing.get().cabinCentre().getX()+.5D,z=landing.get().cabinCentre().getZ()+.5D;
                bounds=new AABB(x-group.getCageSizeX()*.5D,floor-1,z-group.getCageSizeZ()*.5D,
                        x+group.getCageSizeX()*.5D,floor-1+group.getCageSizeY(),z+group.getCageSizeZ()*.5D);
            }
            final double currentFloor=floor;
            final AABB car=bounds;
            List<ServerPlayer> players=level.players().stream().filter(p->p.isAlive()&&!p.isSpectator()&&!p.isPassenger()).toList();
            Set<UUID> available=new HashSet<>();players.forEach(p->available.add(p.getUUID()));riders.passengers.retainAll(available);
            // Sample every tick, including the very first movement tick. A
            // caller can enter and press a floor before a five-tick scan runs.
            for(ServerPlayer player:players)
            {
                double oldFloor=Double.isFinite(riders.previousFloor)?riders.previousFloor:floor;
                boolean inside=player.getX()>=car.minX-.01D&&player.getX()<=car.maxX+.01D
                        &&player.getZ()>=car.minZ-.01D&&player.getZ()<=car.maxZ+.01D;
                boolean onFloor=player.getY()>=Math.min(floor,oldFloor)-.3D
                        &&player.getY()<=Math.max(floor,oldFloor)+1.6D;
                if(inside&&onFloor)riders.passengers.add(player.getUUID());
                if(!riders.passengers.contains(player.getUUID()))continue;
                // A deliberate teleport elsewhere releases the association.
                if(Math.abs(player.getX()-car.getCenter().x)>12||Math.abs(player.getZ()-car.getCenter().z)>12)
                {riders.passengers.remove(player.getUUID());continue;}
                if(group.isMoving())
                {
                    double margin=1.0D+player.getBbWidth()*.5D+.06D;
                    double x=Mth.clamp(player.getX(),car.minX+margin,car.maxX-margin);
                    double z=Mth.clamp(player.getZ(),car.minZ+margin,car.maxZ-margin);
                    double y=player.getY();double top=car.maxY-1.0D-player.getBbHeight();
                    if(y<currentFloor-.10D||y>top+.10D)y=Mth.clamp(y,currentFloor,Math.max(currentFloor,top));
                    if(Math.abs(x-player.getX())>.01D||Math.abs(z-player.getZ())>.01D||Math.abs(y-player.getY())>.01D)
                        reconcile(player,x,y,z,spec.id());
                    player.resetFallDistance();
                }
                else if(riders.moving)
                {
                    double margin=1.0D+player.getBbWidth()*.5D+.06D;
                    double x=Mth.clamp(player.getX(),car.minX+margin,car.maxX-margin);
                    double z=Mth.clamp(player.getZ(),car.minZ+margin,car.maxZ-margin);
                    if(inside&&(Math.abs(player.getY()-floor)>.15D||Math.abs(x-player.getX())>.01D||Math.abs(z-player.getZ())>.01D))reconcile(player,x,floor,z,spec.id());
                }
                else if(!inside)riders.passengers.remove(player.getUUID());
            }
            riders.previousFloor=floor;riders.moving=group.isMoving();
        }
    }

    private static void reconcile(ServerPlayer player,double x,double y,double z,String lift)
    {
        player.teleportTo(player.serverLevel(),x,y,z,player.getYRot(),player.getXRot());
        player.setDeltaMovement(Vec3.ZERO);player.resetFallDistance();player.setOnGround(true);
        ProjectSeele.LOGGER.debug("Lift passenger kept inside native cabin lift={} position={}",lift,player.position());
    }
    private NervLiftPassengerSync(){}
}
