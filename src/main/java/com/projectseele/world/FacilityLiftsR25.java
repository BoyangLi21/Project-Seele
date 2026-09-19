package com.projectseele.world;

import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.Files;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

/** Native lift controls are enabled only after the matching civil patch exists. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID)
public final class FacilityLiftsR25
{
    public static final String EAST = "r25-east-command-gallery";
    public static final String OBSERVATION = "r25-west-observation";
    private static final Map<ServerLevel, Boolean> ACTIVE = new WeakHashMap<>();

    public static List<S20PhysicalElevatorDirector.LiftSpec> installed(ServerLevel level)
    {
        if (!level.dimension().equals(FacilitySchemaV2.DIMENSION) || !ACTIVE.computeIfAbsent(level,
                l -> Files.isRegularFile(l.getServer().getWorldPath(LevelResource.ROOT).resolve("facility_lifts_r25.json")))) return List.of();
        var east = new S20PhysicalElevatorDirector.LiftSpec(EAST,
                java.util.stream.IntStream.of(-448,-434,-420,-406,-392).mapToObj(y ->
                        new S20PhysicalElevatorDirector.Landing("东翼 " + y + " · 指挥室联络",
                                new BlockPos(73,y,253),Direction.SOUTH)).toList());
        var west = new S20PhysicalElevatorDirector.LiftSpec(OBSERVATION,
                new S20PhysicalElevatorDirector.Landing("机库登机层",new BlockPos(-29,-394,-278),Direction.NORTH),
                new S20PhysicalElevatorDirector.Landing("三机观察廊",new BlockPos(-29,-367,-278),Direction.NORTH));
        return List.of(east,west);
    }

    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END) return;
        for (var level : event.getServer().getAllLevels()) for (var spec : installed(level))
        {
            if (!level.hasChunkAt(spec.lower().cabinCentre())) continue;
            S20MovingElevatorsAdapter.reconcile(level,spec);
        }
    }
    private FacilityLiftsR25() {}
}
