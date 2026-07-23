package com.projectseele.world;

import java.util.Locale;

import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.AttachFace;

/** Three independent wet cages and their physical carrier routes. */
public final class EvaHangarBuilder
{
    public static final int HANGAR_CENTRE_Z = -136;
    public static final int HANGAR_BED_ABOVE_ORIGIN = 1;
    public static final int LCL_SHOULDER_LAYERS = 22;
    public static final int GALLERY_Y = 25;
    public static final int GALLERY_Z = -158;
    public static final int OBSERVATION_FLOOR_Y = GALLERY_Y + 7;
    public static final int BRIDGE_SEGMENTS = 8;

    private static final int HALF_WIDTH = 11;
    private static final int HALF_DEPTH = 14;
    private static final int CHAMBER_HEIGHT = 35;
    private static final int GATE_Z = HANGAR_CENTRE_Z + HALF_DEPTH;
    private static final int CORRIDOR_HALF_WIDTH = 7;
    private static final int CARRIER_HALF = 5;
    private static final int CATWALK_FLOOR_ABOVE_BED = 24;
    private static final int REAR_CROSS_Z_FROM_BED = -12;
    private static final int REAR_BOARDING_Z_FROM_BED = -6;
    private static final int BOARDING_CONNECTOR_HALF_WIDTH = 2;
    private static final int OBSERVATION_CEILING_Y = GALLERY_Y + 14;
    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;

    private EvaHangarBuilder() {}

    public static HangarAudit ensure(ServerLevel level, BlockPos origin)
    {
        HangarAudit audit = inspect(level, origin);
        if (audit.valid())
        {
            return audit;
        }
        build(level, origin);
        audit = inspect(level, origin);
        ProjectSeele.LOGGER.info("NERV EVA hangars upgraded: {}", audit.summary());
        if (!audit.valid())
        {
            ProjectSeele.LOGGER.warn("NERV boarding-route diagnostic: {}",
                    boardingRouteDiagnostics(level, origin));
        }
        return audit;
    }

    public static HangarAudit build(ServerLevel level, BlockPos origin)
    {
        for (int variant = 0; variant < 3; variant++)
        {
            buildChamber(level, origin, variant);
            buildTransportTunnel(level, origin, variant);
        }
        buildObservationGallery(level, origin);
        NervOperationsCentreBuilder.linkHangars(level, origin);
        return inspect(level, origin);
    }

    public static HangarAudit inspect(ServerLevel level, BlockPos origin)
    {
        int beds = 0;
        int shells = 0;
        int controls = 0;
        int galleries = 0;
        int observationRooms = 0;
        int plugRigs = 0;
        int walkableRoutes = 0;
        for (int variant = 0; variant < 3; variant++)
        {
            BlockPos bed = hangarBed(origin, variant);
            if (level.getBlockState(bed).is(Blocks.LODESTONE))
            {
                beds++;
            }
            if (level.getBlockState(bed.offset(-HALF_WIDTH, CHAMBER_HEIGHT, 0))
                    .is(Blocks.SEA_LANTERN)
                    && level.getBlockState(bed.offset(HALF_WIDTH, CHAMBER_HEIGHT, 0))
                    .is(Blocks.SEA_LANTERN))
            {
                shells++;
            }
            for (boolean prepare : new boolean[] {true, false})
            {
                if (level.getBlockState(controlPosition(origin, variant, prepare))
                        .is(Blocks.STONE_BUTTON))
                {
                    controls++;
                }
            }
            if (level.getBlockState(origin.offset(
                    IntegratedNervMapBuilder.LIFT_X[variant],
                    OBSERVATION_CEILING_Y, GALLERY_Z)).is(Blocks.BEACON))
            {
                galleries++;
            }
            if (level.getBlockState(origin.offset(
                    IntegratedNervMapBuilder.LIFT_X[variant],
                    OBSERVATION_FLOOR_Y + 3, GALLERY_Z + 8))
                    .is(Blocks.GRAY_STAINED_GLASS))
            {
                observationRooms++;
            }
            if (level.getBlockState(bed.offset(0, CHAMBER_HEIGHT - 1,
                    REAR_BOARDING_Z_FROM_BED)).is(Blocks.BEACON))
            {
                plugRigs++;
            }
            if (isBoardingRouteWalkable(level, origin, variant))
            {
                walkableRoutes++;
            }
        }
        boolean valid = beds == 3 && shells == 3 && controls == 6
                && galleries == 3 && observationRooms == 3
                && plugRigs == 3 && walkableRoutes == 3;
        return new HangarAudit(valid, beds, shells, controls, galleries,
                observationRooms, plugRigs, walkableRoutes);
    }

    /**
     * Cheap immutable gate for the live logistics tick. Carrier beds and the
     * boarding route are intentionally absent while an EVA is in transit, so
     * the complete static hangar audit must not pause its own state machine.
     */
    public static boolean runtimeInfrastructurePresent(ServerLevel level,
                                                       BlockPos origin)
    {
        for (int variant = 0; variant < 3; variant++)
        {
            BlockPos bed = hangarBed(origin, variant);
            if (!level.getBlockState(bed.offset(-HALF_WIDTH,
                            CHAMBER_HEIGHT, 0)).is(Blocks.SEA_LANTERN)
                    || !level.getBlockState(bed.offset(HALF_WIDTH,
                            CHAMBER_HEIGHT, 0)).is(Blocks.SEA_LANTERN)
                    || !level.getBlockState(controlPosition(
                            origin, variant, true)).is(Blocks.STONE_BUTTON)
                    || !level.getBlockState(controlPosition(
                            origin, variant, false)).is(Blocks.STONE_BUTTON)
                    || !level.getBlockState(origin.offset(
                            IntegratedNervMapBuilder.LIFT_X[variant],
                            OBSERVATION_CEILING_Y, GALLERY_Z)).is(Blocks.BEACON)
                    || !level.getBlockState(bed.offset(0,
                            CHAMBER_HEIGHT - 1,
                            REAR_BOARDING_Z_FROM_BED)).is(Blocks.BEACON))
            {
                return false;
            }
        }
        return true;
    }

    public static BlockPos hangarBed(BlockPos origin, int variant)
    {
        requireVariant(variant);
        return origin.offset(IntegratedNervMapBuilder.LIFT_X[variant],
                HANGAR_BED_ABOVE_ORIGIN, HANGAR_CENTRE_Z);
    }

    public static boolean isHangarBed(BlockPos position)
    {
        for (int variant = 0; variant < 3; variant++)
        {
            if (hangarBed(IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant)
                    .equals(position))
            {
                return true;
            }
        }
        return false;
    }

    public static BlockPos controlPosition(BlockPos origin, int variant,
                                           boolean prepare)
    {
        requireVariant(variant);
        return origin.offset(IntegratedNervMapBuilder.LIFT_X[variant]
                        + (prepare ? -2 : 2),
                OBSERVATION_FLOOR_Y + 1, GALLERY_Z + 2);
    }

    /** Human-scale endpoint of the extended dorsal boarding bridge. */
    public static BlockPos boardingPosition(BlockPos origin, int variant)
    {
        BlockPos bed = hangarBed(origin, variant);
        return new BlockPos(bed.getX(),
                bed.getY() + CATWALK_FLOOR_ABOVE_BED + 1,
                bed.getZ() + REAR_BOARDING_Z_FROM_BED);
    }

    public static int gateZ(BlockPos origin)
    {
        return origin.getZ() + GATE_Z;
    }

    public static int hangarZ(BlockPos origin)
    {
        return origin.getZ() + HANGAR_CENTRE_Z;
    }

    public static void setGate(ServerLevel level, BlockPos origin,
                               int variant, boolean open)
    {
        BlockPos bed = hangarBed(origin, variant);
        BlockState accent = accent(variant);
        for (int x = -6; x <= 6; x++)
        {
            for (int y = 1; y <= 31; y++)
            {
                BlockPos position = new BlockPos(bed.getX() + x,
                        bed.getY() + y, origin.getZ() + GATE_Z);
                if (open)
                {
                    clear(level, position);
                }
                else
                {
                    boolean edge = Math.abs(x) == 6 || y == 1 || y == 31;
                    set(level, position, edge
                            ? Blocks.IRON_BLOCK.defaultBlockState()
                            : (Math.floorMod(x + y, 9) == 0
                            ? accent : Blocks.REINFORCED_DEEPSLATE.defaultBlockState()));
                }
            }
        }
    }

    /** Sets the exact number of full LCL layers, bottom-up. */
    public static void setLclLevel(ServerLevel level, BlockPos origin,
                                   int variant, int layers)
    {
        BlockPos bed = hangarBed(origin, variant);
        int safeLayers = Math.max(0, Math.min(LCL_SHOULDER_LAYERS, layers));
        for (int y = 1; y <= LCL_SHOULDER_LAYERS; y++)
        {
            boolean filled = y <= safeLayers;
            for (int x = -9; x <= 9; x++)
            {
                for (int z = -11; z <= 11; z++)
                {
                    BlockPos position = bed.offset(x, y, z);
                    if (filled)
                    {
                        set(level, position, ModFluids.LCL_SOURCE.get()
                                .defaultFluidState().createLegacyBlock());
                    }
                    else if (level.getFluidState(position).getFluidType()
                            == ModFluids.LCL_TYPE.get())
                    {
                        clear(level, position);
                    }
                }
            }
        }
    }

    public static void setLclLayer(ServerLevel level, BlockPos origin,
                                   int variant, int layer, boolean filled)
    {
        if (layer < 1 || layer > LCL_SHOULDER_LAYERS)
        {
            return;
        }
        BlockPos bed = hangarBed(origin, variant);
        for (int x = -9; x <= 9; x++)
        {
            for (int z = -11; z <= 11; z++)
            {
                BlockPos position = bed.offset(x, layer, z);
                if (filled)
                {
                    set(level, position, ModFluids.LCL_SOURCE.get()
                            .defaultFluidState().createLegacyBlock());
                }
                else if (level.getFluidState(position).getFluidType()
                        == ModFluids.LCL_TYPE.get())
                {
                    clear(level, position);
                }
            }
        }
    }
    public static int lclLevel(ServerLevel level, BlockPos origin, int variant)
    {
        BlockPos bed = hangarBed(origin, variant);
        int layers = 0;
        for (int y = 1; y <= LCL_SHOULDER_LAYERS; y++)
        {
            if (level.getFluidState(bed.offset(8, y, 8)).getFluidType()
                    == ModFluids.LCL_TYPE.get())
            {
                layers = y;
            }
        }
        return layers;
    }

    /** Moves/restores the visible 11x11 maintenance carrier one block at a time. */
    public static void setCarrier(ServerLevel level, BlockPos origin,
                                  int variant, int centreZ, boolean present)
    {
        BlockPos hangar = hangarBed(origin, variant);
        int y = hangar.getY();
        int centreX = hangar.getX();
        for (int x = -CARRIER_HALF; x <= CARRIER_HALF; x++)
        {
            for (int z = -CARRIER_HALF; z <= CARRIER_HALF; z++)
            {
                BlockPos position = new BlockPos(centreX + x, y, centreZ + z);
                if (present)
                {
                    boolean rim = Math.abs(x) == CARRIER_HALF
                            || Math.abs(z) == CARRIER_HALF;
                    set(level, position, rim
                            ? Blocks.IRON_BLOCK.defaultBlockState()
                            : Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
                }
                else
                {
                    set(level, position, transportFloor(position, origin, variant));
                }
            }
        }
        if (present)
        {
            set(level, new BlockPos(centreX, y, centreZ),
                    Blocks.LODESTONE.defaultBlockState());
        }
    }

    /**
     * Slides a carrier without destroying and repainting its overlapping
     * 11x11 footprint. Only cells whose final state changes are sent to
     * clients, which keeps three simultaneous EVA transfers within the tick
     * budget.
     */
    public static void moveCarrier(ServerLevel level, BlockPos origin,
                                   int variant, int oldCentreZ, int newCentreZ)
    {
        if (oldCentreZ == newCentreZ)
        {
            return;
        }
        BlockPos hangar = hangarBed(origin, variant);
        int y = hangar.getY();
        int centreX = hangar.getX();
        int minZ = Math.min(oldCentreZ, newCentreZ) - CARRIER_HALF;
        int maxZ = Math.max(oldCentreZ, newCentreZ) + CARRIER_HALF;
        for (int worldZ = minZ; worldZ <= maxZ; worldZ++)
        {
            int relativeNewZ = worldZ - newCentreZ;
            boolean insideNew = Math.abs(relativeNewZ) <= CARRIER_HALF;
            for (int x = -CARRIER_HALF; x <= CARRIER_HALF; x++)
            {
                BlockPos position = new BlockPos(centreX + x, y, worldZ);
                if (insideNew)
                {
                    boolean rim = Math.abs(x) == CARRIER_HALF
                            || Math.abs(relativeNewZ) == CARRIER_HALF;
                    set(level, position, rim
                            ? Blocks.IRON_BLOCK.defaultBlockState()
                            : Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
                }
                else
                {
                    set(level, position, transportFloor(position, origin, variant));
                }
            }
        }
        set(level, new BlockPos(centreX, y, newCentreZ),
                Blocks.LODESTONE.defaultBlockState());
    }

    public static void restoreStaticCarrier(ServerLevel level, BlockPos origin,
                                            int variant, BlockPos station)
    {
        setCarrier(level, origin, variant, station.getZ(), true);
    }

    private static void buildChamber(ServerLevel level, BlockPos origin,
                                     int variant)
    {
        BlockPos bed = hangarBed(origin, variant);
        BlockState accent = accent(variant);
        for (int x = -HALF_WIDTH; x <= HALF_WIDTH; x++)
        {
            for (int z = -HALF_DEPTH; z <= HALF_DEPTH; z++)
            {
                set(level, bed.offset(x, 0, z), Math.abs(x) == 5
                        ? Blocks.POLISHED_BASALT.defaultBlockState()
                        : Blocks.POLISHED_DEEPSLATE.defaultBlockState());
                for (int y = 1; y <= CHAMBER_HEIGHT; y++)
                {
                    boolean wall = Math.abs(x) == HALF_WIDTH
                            || Math.abs(z) == HALF_DEPTH
                            || y == CHAMBER_HEIGHT;
                    BlockPos position = bed.offset(x, y, z);
                    if (!wall)
                    {
                        clear(level, position);
                        continue;
                    }
                    boolean observationWindow = z == -HALF_DEPTH
                            && Math.abs(x) <= 9 && y >= 20 && y <= 31;
                    boolean lampBand = (Math.abs(x) == HALF_WIDTH
                            && Math.floorMod(z, 6) == 0 && y == 24)
                            || (y == CHAMBER_HEIGHT && Math.floorMod(x + z, 8) == 0);
                    set(level, position, observationWindow
                            ? Blocks.TINTED_GLASS.defaultBlockState()
                            : lampBand ? Blocks.SEA_LANTERN.defaultBlockState()
                            : (y % 9 == 0 ? accent
                            : Blocks.REINFORCED_DEEPSLATE.defaultBlockState()));
                }
            }
        }
        // Dedicated shell receipts: these exact corner lamps are audited and
        // must not depend on the decorative ceiling-band modulo pattern.
        set(level, bed.offset(-HALF_WIDTH, CHAMBER_HEIGHT, 0),
                Blocks.SEA_LANTERN.defaultBlockState());
        set(level, bed.offset(HALF_WIDTH, CHAMBER_HEIGHT, 0),
                Blocks.SEA_LANTERN.defaultBlockState());
        set(level, bed, Blocks.LODESTONE.defaultBlockState());
        buildShoulderCatwalk(level, bed, accent);
        buildPlugCraneRig(level, bed, accent);
        setGate(level, origin, variant, false);
        setLclLevel(level, origin, variant, LCL_SHOULDER_LAYERS);
    }

    private static void buildShoulderCatwalk(ServerLevel level, BlockPos bed,
                                               BlockState accent)
    {
        // The EVA is parked at yaw 180; its service/entry-plug side is -Z.
        // Keeping this floor at bed + 24 also makes it level with the shared
        // observation gallery and safely above the entry interaction minimum.
        int y = CATWALK_FLOOR_ABOVE_BED;
        for (int z = -12; z <= 12; z++)
        {
            for (int x : new int[] {-10, -9, 9, 10})
            {
                set(level, bed.offset(x, y, z), Math.abs(x) == 10
                        ? Blocks.IRON_BLOCK.defaultBlockState() : accent);
            }
            set(level, bed.offset(-8, y + 1, z), Blocks.IRON_BARS.defaultBlockState());
            set(level, bed.offset(8, y + 1, z), Blocks.IRON_BARS.defaultBlockState());
        }
        for (int x = -10; x <= 10; x++)
        {
            set(level, bed.offset(x, y, REAR_CROSS_Z_FROM_BED),
                    Math.floorMod(x, 5) == 0
                    ? Blocks.SEA_LANTERN.defaultBlockState()
                    : Blocks.IRON_BLOCK.defaultBlockState());
            set(level, bed.offset(x, y + 1, REAR_CROSS_Z_FROM_BED + 1),
                    Blocks.IRON_BARS.defaultBlockState());
        }
    }

    private static void buildTransportTunnel(ServerLevel level, BlockPos origin,
                                             int variant)
    {
        BlockPos bed = hangarBed(origin, variant);
        int destinationZ = IntegratedNervMapBuilder.lowerLiftBed(variant).getZ();
        int shaftPortalZ = destinationZ
                - IntegratedNervMapBuilder.SHAFT_OUTER_RADIUS;
        for (int z = bed.getZ() + HALF_DEPTH + 1; z <= destinationZ; z++)
        {
            for (int x = -CORRIDOR_HALF_WIDTH; x <= CORRIDOR_HALF_WIDTH; x++)
            {
                BlockPos floor = new BlockPos(bed.getX() + x, bed.getY(), z);
                set(level, floor, transportFloor(floor, origin, variant));
                // Inside the audited launch column, extend only the carrier
                // rail. A tunnel roof here used to cap all three shafts.
                if (z > shaftPortalZ)
                {
                    continue;
                }
                for (int y = 1; y <= 33; y++)
                {
                    BlockPos position = floor.above(y);
                    boolean wall = Math.abs(x) == CORRIDOR_HALF_WIDTH
                            || y == 33;
                    if (wall)
                    {
                        set(level, position, y == 33 && Math.floorMod(z, 8) == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
                    }
                    else
                    {
                        clear(level, position);
                    }
                }
            }
        }
    }

    private static void buildObservationGallery(ServerLevel level, BlockPos origin)
    {
        int minX = IntegratedNervMapBuilder.LIFT_X[0] - 13;
        int maxX = IntegratedNervMapBuilder.LIFT_X[2] + 13;
        int minZ = GALLERY_Z - 7;
        int maxZ = GALLERY_Z + 8;
        for (int x = minX; x <= maxX; x++)
        {
            for (int z = minZ; z <= maxZ; z++)
            {
                set(level, origin.offset(x, GALLERY_Y, z),
                        Math.floorMod(x + z, 9) == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.POLISHED_DEEPSLATE.defaultBlockState());
                set(level, origin.offset(x, OBSERVATION_CEILING_Y, z),
                        Math.floorMod(x - z, 11) == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
                for (int y = GALLERY_Y + 1;
                     y < OBSERVATION_CEILING_Y; y++)
                {
                    boolean boundary = x == minX || x == maxX
                            || z == minZ || z == maxZ;
                    BlockPos position = origin.offset(x, y, z);
                    if (!boundary)
                    {
                        clear(level, position);
                    }
                    else if (z == maxZ && y <= GALLERY_Y + 6)
                    {
                        set(level, position,
                                Blocks.GRAY_STAINED_GLASS.defaultBlockState());
                    }
                    else
                    {
                        set(level, position,
                                Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
                    }
                }
            }
        }

        BlockState button = Blocks.STONE_BUTTON.defaultBlockState()
                .setValue(ButtonBlock.FACE, AttachFace.FLOOR)
                .setValue(ButtonBlock.FACING, Direction.NORTH);
        for (int variant = 0; variant < 3; variant++)
        {
            BlockState accent = accent(variant);
            buildObservationControlRoom(level, origin, variant, accent);
            for (boolean prepare : new boolean[] {true, false})
            {
                BlockPos control = controlPosition(origin, variant, prepare);
                set(level, control.below(), prepare ? accent
                        : Blocks.CYAN_CONCRETE.defaultBlockState());
                set(level, control, button);
            }
            set(level, origin.offset(IntegratedNervMapBuilder.LIFT_X[variant],
                            OBSERVATION_CEILING_Y, GALLERY_Z),
                    Blocks.BEACON.defaultBlockState());
            buildBoardingConnector(level, origin, variant, accent);
        }

        // Two dry ladder towers keep the lower gallery independently usable.
        for (int x : new int[] {minX + 2, maxX - 2})
        {
            for (int y = HANGAR_BED_ABOVE_ORIGIN + 1;
                 y <= GALLERY_Y; y++)
            {
                set(level, origin.offset(x, y, GALLERY_Z - 6),
                        Blocks.LADDER.defaultBlockState()
                                .setValue(LadderBlock.FACING, Direction.SOUTH));
                set(level, origin.offset(x, y, GALLERY_Z - 7),
                        Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
            }
        }
    }

    private static void buildObservationControlRoom(ServerLevel level,
                                                     BlockPos origin,
                                                     int variant,
                                                     BlockState accent)
    {
        int centreX = IntegratedNervMapBuilder.LIFT_X[variant];
        int minX = centreX - 9;
        int maxX = centreX + 9;
        int minZ = GALLERY_Z - 6;
        int maxZ = GALLERY_Z + 8;
        for (int x = minX; x <= maxX; x++)
        {
            for (int z = minZ; z <= maxZ; z++)
            {
                set(level, origin.offset(x, OBSERVATION_FLOOR_Y, z),
                        Math.floorMod(x + z, 7) == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.POLISHED_DEEPSLATE.defaultBlockState());
                for (int y = OBSERVATION_FLOOR_Y + 1;
                     y < OBSERVATION_CEILING_Y; y++)
                {
                    boolean side = x == minX || x == maxX || z == minZ;
                    BlockPos position = origin.offset(x, y, z);
                    if (z == maxZ)
                    {
                        set(level, position,
                                Blocks.GRAY_STAINED_GLASS.defaultBlockState());
                    }
                    else if (side)
                    {
                        set(level, position,
                                Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
                    }
                    else
                    {
                        clear(level, position);
                    }
                }
            }
        }

        // A protected internal ladder rises from the bridge gallery into the
        // glass control booth directly above it.
        int ladderX = centreX + 7;
        for (int y = GALLERY_Y + 1; y <= OBSERVATION_FLOOR_Y; y++)
        {
            set(level, origin.offset(ladderX, y, GALLERY_Z - 5),
                    Blocks.LADDER.defaultBlockState()
                            .setValue(LadderBlock.FACING, Direction.SOUTH));
            set(level, origin.offset(ladderX, y, GALLERY_Z - 6),
                    Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
        }
        for (int x = centreX - 5; x <= centreX + 5; x++)
        {
            set(level, origin.offset(x, OBSERVATION_FLOOR_Y + 1,
                            GALLERY_Z + 6),
                    Math.floorMod(x, 4) == 0
                            ? Blocks.SEA_LANTERN.defaultBlockState() : accent);
        }
    }

    private static void buildPlugCraneRig(ServerLevel level, BlockPos bed,
                                          BlockState accent)
    {
        int railY = CHAMBER_HEIGHT - 1;
        for (int z = REAR_BOARDING_Z_FROM_BED - 4; z <= 4; z++)
        {
            set(level, bed.offset(-2, railY, z),
                    Blocks.IRON_BLOCK.defaultBlockState());
            set(level, bed.offset(2, railY, z),
                    Blocks.IRON_BLOCK.defaultBlockState());
            if (Math.floorMod(z, 4) == 0)
            {
                set(level, bed.offset(0, railY, z), accent);
            }
        }
        for (int x = -3; x <= 3; x++)
        {
            set(level, bed.offset(x, railY,
                            REAR_BOARDING_Z_FROM_BED),
                    x == 0 ? Blocks.BEACON.defaultBlockState()
                            : Blocks.IRON_BLOCK.defaultBlockState());
        }
    }

    /**
     * Cuts a real doorway through the gallery glass and continues the deck to
     * a rear boarding spur. Dynamic panels retract sideways before insertion.
     */    private static void buildBoardingConnector(ServerLevel level, BlockPos origin,
                                               int variant, BlockState accent)
    {
        BlockPos bed = hangarBed(origin, variant);
        int floorY = bed.getY() + CATWALK_FLOOR_ABOVE_BED;
        int galleryStartZ = origin.getZ() + GALLERY_Z + 4;
        int doorwayZ = origin.getZ() + GALLERY_Z + 8;

        // Only the pressure threshold is permanent. The exposed eight panels
        // beyond it are controlled by setBoardingBridgeExtension.
        for (int z = galleryStartZ; z <= doorwayZ; z++)
        {
            for (int x = -BOARDING_CONNECTOR_HALF_WIDTH;
                 x <= BOARDING_CONNECTOR_HALF_WIDTH; x++)
            {
                BlockPos floor = new BlockPos(bed.getX() + x, floorY, z);
                set(level, floor, Math.floorMod(x + z, 5) == 0
                        ? accent : Blocks.IRON_BLOCK.defaultBlockState());
                for (int y = 1; y <= 5; y++)
                {
                    clear(level, floor.above(y));
                }
            }
        }
        for (int y = 1; y <= 5; y++)
        {
            set(level, new BlockPos(bed.getX()
                            - BOARDING_CONNECTOR_HALF_WIDTH - 1,
                            floorY + y, doorwayZ),
                    Blocks.IRON_BLOCK.defaultBlockState());
            set(level, new BlockPos(bed.getX()
                            + BOARDING_CONNECTOR_HALF_WIDTH + 1,
                            floorY + y, doorwayZ),
                    Blocks.IRON_BLOCK.defaultBlockState());
        }
        for (int x = -BOARDING_CONNECTOR_HALF_WIDTH - 1;
             x <= BOARDING_CONNECTOR_HALF_WIDTH + 1; x++)
        {
            set(level, new BlockPos(bed.getX() + x, floorY + 6, doorwayZ),
                    x == 0 ? Blocks.SEA_LANTERN.defaultBlockState() : accent);
        }
        setBoardingBridgeExtension(level, origin, variant, BRIDGE_SEGMENTS);
    }

    /**
     * Discrete split-panel bridge: zero leaves the centre lane empty and
     * parks both halves in side pockets; eight reaches the EVA dorsal socket.
     */
    public static void setBoardingBridgeExtension(ServerLevel level,
                                                   BlockPos origin,
                                                   int variant,
                                                   int extension)
    {
        requireVariant(variant);
        int safeExtension = Math.max(0, Math.min(BRIDGE_SEGMENTS, extension));
        BlockPos bed = hangarBed(origin, variant);
        BlockState accent = accent(variant);
        int floorY = bed.getY() + CATWALK_FLOOR_ABOVE_BED;
        int firstZ = origin.getZ() + GALLERY_Z + 9;
        int lastZ = bed.getZ() + REAR_BOARDING_Z_FROM_BED;
        for (int z = firstZ; z <= lastZ; z++)
        {
            int segment = z - firstZ + 1;
            boolean extended = segment <= safeExtension;
            for (int x = -5; x <= 5; x++)
            {
                BlockPos floor = new BlockPos(bed.getX() + x, floorY, z);
                boolean centrePanel = Math.abs(x) <= 2;
                boolean sidePocket = Math.abs(x) >= 3;
                if (extended && centrePanel)
                {
                    set(level, floor, Math.floorMod(x + z, 5) == 0
                            ? accent : Blocks.IRON_BLOCK.defaultBlockState());
                }
                else if (!extended && sidePocket)
                {
                    set(level, floor, Math.abs(x) == 5
                            ? accent : Blocks.IRON_BLOCK.defaultBlockState());
                }
                else
                {
                    clear(level, floor);
                }
                for (int y = 1; y <= 5; y++)
                {
                    clear(level, floor.above(y));
                }
            }
            for (int x : new int[] {-3, 3})
            {
                BlockPos rail = new BlockPos(bed.getX() + x,
                        floorY + 1, z);
                if (extended)
                {
                    set(level, rail, Blocks.IRON_BARS.defaultBlockState());
                }
                else
                {
                    clear(level, rail);
                }
            }
        }
    }
    private static boolean isBoardingRouteWalkable(ServerLevel level,
                                                    BlockPos origin,
                                                    int variant)
    {
        return boardingRouteFailure(level, origin, variant) == null;
    }

    private static String boardingRouteFailure(ServerLevel level,
                                                BlockPos origin,
                                                int variant)
    {
        BlockPos bed = hangarBed(origin, variant);
        int floorY = bed.getY() + CATWALK_FLOOR_ABOVE_BED;
        if (floorY != origin.getY() + GALLERY_Y)
        {
            return "floor-level expected=" + (origin.getY() + GALLERY_Y)
                    + " actual=" + floorY;
        }
        int galleryStartZ = origin.getZ() + GALLERY_Z + 4;
        int doorwayZ = origin.getZ() + GALLERY_Z + 8;
        int boardingEndZ = bed.getZ() + REAR_BOARDING_Z_FROM_BED;
        if (boardingEndZ >= bed.getZ())
        {
            return "boarding-end-not-rear z=" + boardingEndZ;
        }
        for (int z = galleryStartZ; z <= boardingEndZ; z++)
        {
            BlockPos floor = new BlockPos(bed.getX(), floorY, z);
            BlockState floorState = level.getBlockState(floor);
            if (!floorState.isFaceSturdy(level, floor, Direction.UP))
            {
                return "floor " + floor.toShortString() + "="
                        + floorState.getBlock().getDescriptionId();
            }
            for (int y = 1; y <= 4; y++)
            {
                BlockPos clearance = floor.above(y);
                BlockState state = level.getBlockState(clearance);
                if (!state.getCollisionShape(level, clearance).isEmpty())
                {
                    return "clearance " + clearance.toShortString() + "="
                            + state.getBlock().getDescriptionId();
                }
            }
        }
        for (int x = -BOARDING_CONNECTOR_HALF_WIDTH;
             x <= BOARDING_CONNECTOR_HALF_WIDTH; x++)
        {
            for (int y = 1; y <= 4; y++)
            {
                BlockPos doorway = new BlockPos(bed.getX() + x,
                        floorY + y, doorwayZ);
                BlockState state = level.getBlockState(doorway);
                if (!state.getCollisionShape(level, doorway).isEmpty())
                {
                    return "doorway " + doorway.toShortString() + "="
                            + state.getBlock().getDescriptionId();
                }
            }
        }
        for (int z = doorwayZ + 1; z <= boardingEndZ; z++)
        {
            for (int x : new int[] {
                    -BOARDING_CONNECTOR_HALF_WIDTH - 1,
                    BOARDING_CONNECTOR_HALF_WIDTH + 1})
            {
                BlockPos rail = new BlockPos(bed.getX() + x,
                        floorY + 1, z);
                BlockState state = level.getBlockState(rail);
                if (!state.is(Blocks.IRON_BARS))
                {
                    return "rail " + rail.toShortString() + "="
                            + state.getBlock().getDescriptionId();
                }
            }
        }
        return null;
    }

    private static String boardingRouteDiagnostics(ServerLevel level,
                                                    BlockPos origin)
    {
        StringBuilder result = new StringBuilder();
        for (int variant = 0; variant < 3; variant++)
        {
            String failure = boardingRouteFailure(level, origin, variant);
            if (failure != null)
            {
                if (!result.isEmpty())
                {
                    result.append("; ");
                }
                result.append("EVA-").append(String.format(Locale.ROOT,
                        "%02d", variant)).append(' ').append(failure);
            }
        }
        return result.isEmpty() ? "ok" : result.toString();
    }

    private static BlockState transportFloor(BlockPos position, BlockPos origin,
                                             int variant)
    {
        BlockPos hangar = hangarBed(origin, variant);
        BlockPos silo = IntegratedNervMapBuilder.lowerLiftBed(variant);
        if (position.equals(hangar) || position.equals(silo))
        {
            return Blocks.LODESTONE.defaultBlockState();
        }
        int relativeX = position.getX() - hangar.getX();
        return Math.abs(relativeX) == 5
                ? Blocks.POLISHED_BASALT.defaultBlockState()
                : Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    }

    private static BlockState accent(int variant)
    {
        return switch (variant)
        {
            case 0 -> Blocks.ORANGE_CONCRETE.defaultBlockState();
            case 2 -> Blocks.RED_CONCRETE.defaultBlockState();
            default -> Blocks.PURPLE_CONCRETE.defaultBlockState();
        };
    }

    private static void requireVariant(int variant)
    {
        if (variant < 0 || variant > 2)
        {
            throw new IllegalArgumentException(String.format(Locale.ROOT,
                    "EVA hangar variant must be 0, 1 or 2, got %d", variant));
        }
    }

    private static void clear(ServerLevel level, BlockPos position)
    {
        if (!level.getBlockState(position).isAir())
        {
            set(level, position, Blocks.AIR.defaultBlockState());
        }
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state)
    {
        if (!level.getBlockState(position).equals(state))
        {
            level.setBlock(position, state, UPDATE_CLIENTS);
        }
    }

    public record HangarAudit(boolean valid, int beds, int shells,
                              int controls, int galleries,
                              int observationRooms, int plugRigs,
                              int walkableRoutes)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s beds=%d/3 shells=%d/3 controls=%d/6 "
                            + "galleries=%d/3 observationRooms=%d/3 "
                            + "plugRigs=%d/3 walkableRoutes=%d/3",
                    this.valid, this.beds, this.shells, this.controls,
                    this.galleries, this.observationRooms, this.plugRigs,
                    this.walkableRoutes);
        }
    }
}
