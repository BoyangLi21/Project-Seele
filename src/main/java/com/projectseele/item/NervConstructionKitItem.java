package com.projectseele.item;

import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.registry.ModEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

/** Builds an original three-bay NERV underground sortie complex. */
public class NervConstructionKitItem extends Item
{
    public NervConstructionKitItem(Properties properties)
    {
        super(properties);
    }

    @Override
    public InteractionResult useOn(UseOnContext context)
    {
        if (!(context.getLevel() instanceof ServerLevel level))
        {
            return InteractionResult.SUCCESS;
        }
        BlockPos origin = context.getClickedPos().above();
        if (origin.getY() - 31 < level.getMinBuildHeight()
                || origin.getY() + 33 >= level.getMaxBuildHeight())
        {
            if (context.getPlayer() != null)
            {
                context.getPlayer().displayClientMessage(Component.literal(
                        "Not enough vertical space for the NERV launch complex."), true);
            }
            return InteractionResult.FAIL;
        }
        AABB buildArea = new AABB(origin).inflate(52.0D, 40.0D, 52.0D);
        boolean existingComplex = !level.getEntitiesOfClass(EvaUnit01Entity.class, buildArea,
                unit -> unit.isAlive() && unit.findLaunchBed() != null).isEmpty();
        if (existingComplex)
        {
            if (context.getPlayer() != null)
            {
                context.getPlayer().displayClientMessage(Component.literal(
                        "A NERV launch complex already occupies this area."), true);
            }
            return InteractionResult.FAIL;
        }
        buildComplex(level, origin);
        if (context.getPlayer() != null)
        {
            context.getPlayer().displayClientMessage(Component.translatable("message.projectseele.nerv_built"), false);
        }
        return InteractionResult.CONSUME;
    }

    /** Shared builder used by the creative item and the deterministic silo command. */
    public static void buildComplex(ServerLevel level, BlockPos origin)
    {
        BlockState floor = Blocks.SMOOTH_STONE.defaultBlockState();
        BlockState armor = Blocks.GRAY_CONCRETE.defaultBlockState();
        BlockState nerv = Blocks.BLACK_CONCRETE.defaultBlockState();
        BlockState glass = Blocks.TINTED_GLASS.defaultBlockState();

        // Armoured surface apron. The shafts are cut through it afterwards.
        for (int x = -44; x <= 44; x++)
        {
            for (int z = -30; z <= 38; z++)
            {
                BlockState surface = (Math.abs(x) % 12 == 0 || Math.abs(z) % 12 == 0)
                        ? armor : floor;
                level.setBlock(origin.offset(x, 0, z), surface, 3);
            }
        }
        BlockPos unit00Bay = origin.offset(-22, 0, 0);
        BlockPos unit01Bay = origin;
        BlockPos unit02Bay = origin.offset(22, 0, 0);
        buildLaunchShaft(level, unit00Bay, Blocks.ORANGE_CONCRETE.defaultBlockState());
        buildLaunchShaft(level, unit01Bay, Blocks.PURPLE_CONCRETE.defaultBlockState());
        buildLaunchShaft(level, unit02Bay, Blocks.RED_CONCRETE.defaultBlockState());

        // Underground transverse access gallery joining all three cages.
        for (int x = -36; x <= 36; x++)
        {
            for (int y = -27; y <= -21; y++)
            {
                for (int z = 10; z <= 16; z++)
                {
                    boolean shell = y == -27 || y == -21 || z == 10 || z == 16;
                    level.setBlock(origin.offset(x, y, z), shell ? armor : Blocks.AIR.defaultBlockState(), 3);
                    if (shell && y == -21 && x % 6 == 0)
                    {
                        level.setBlock(origin.offset(x, y, z), Blocks.SEA_LANTERN.defaultBlockState(), 3);
                    }
                }
            }
        }
        // Build the lift columns after the transverse gallery so its shell
        // cannot overwrite the ladder openings.
        buildEntryGantry(level, unit00Bay, Blocks.ORANGE_CONCRETE.defaultBlockState());
        buildEntryGantry(level, unit01Bay, Blocks.PURPLE_CONCRETE.defaultBlockState());
        buildEntryGantry(level, unit02Bay, Blocks.RED_CONCRETE.defaultBlockState());

        buildCommandBunker(level, origin.offset(0, 1, 27), armor, nerv, glass);
        for (int[] tower : new int[][] {{-38,-24},{-38,28},{38,-24},{38,28}})
        {
            buildRetractableTower(level, origin.offset(tower[0], 1, tower[1]), armor, glass);
        }
        deployUnit(level, unit00Bay, ModEntities.EVA_UNIT00.get().create(level));
        deployUnit(level, unit01Bay, ModEntities.EVA_UNIT01.get().create(level));
        deployUnit(level, unit02Bay, ModEntities.EVA_UNIT02.get().create(level));
    }

    private static void buildLaunchShaft(ServerLevel level, BlockPos centre, BlockState accent)
    {
        BlockState wall = Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
        BlockState frame = Blocks.IRON_BLOCK.defaultBlockState();
        BlockState dark = Blocks.BLACK_CONCRETE.defaultBlockState();
        BlockState light = Blocks.SEA_LANTERN.defaultBlockState();
        for (int y = -31; y <= 7; y++)
        {
            for (int x = -7; x <= 7; x++)
            {
                for (int z = -7; z <= 7; z++)
                {
                    boolean outer = Math.abs(x) == 7 || Math.abs(z) == 7;
                    level.setBlock(centre.offset(x, y, z), outer ? wall : Blocks.AIR.defaultBlockState(), 3);
                }
            }
            for (int sx : new int[] {-6, 6})
            {
                for (int sz : new int[] {-6, 6})
                {
                    level.setBlock(centre.offset(sx, y, sz), y % 5 == 0 ? light : frame, 3);
                }
            }
            if (y >= -29 && y <= -4 && y % 6 == 0)
            {
                for (int x = -5; x <= 5; x++)
                {
                    level.setBlock(centre.offset(x, y, -6), dark, 3);
                    level.setBlock(centre.offset(x, y, 6), dark, 3);
                }
            }
        }
        // Luminous carrier platform and colour-coded depth markings.
        for (int x = -6; x <= 6; x++)
        {
            for (int z = -6; z <= 6; z++)
            {
                boolean rim = Math.abs(x) == 6 || Math.abs(z) == 6;
                level.setBlock(centre.offset(x, -30, z), rim ? light : dark, 3);
            }
            for (int y = -28; y <= 4; y += 4)
            {
                level.setBlock(centre.offset(x, y, 7), accent, 3);
            }
        }
        level.setBlock(centre.offset(0, -30, 0), Blocks.LODESTONE.defaultBlockState(), 3);
        // Split surface shutter, left open along the centreline for sorties.
        for (int i = -7; i <= 7; i++)
        {
            level.setBlock(centre.offset(i, 1, -8), accent, 3);
            level.setBlock(centre.offset(i, 1, 8), accent, 3);
            level.setBlock(centre.offset(-8, 1, i), frame, 3);
            level.setBlock(centre.offset(8, 1, i), frame, 3);
        }
    }

    /**
     * Dorsal entry-plug access. The lift starts in the transverse gallery and
     * ends beside the Unit's upper back, so a pilot cannot board a caged EVA
     * from ground level. The catwalk stays outside the 8.5-block carrier
     * envelope and therefore cannot snag the frame during launch.
     */
    private static void buildEntryGantry(ServerLevel level, BlockPos centre, BlockState accent)
    {
        int gantryY = -8;
        BlockState frame = Blocks.IRON_BLOCK.defaultBlockState();
        BlockState dark = Blocks.BLACK_CONCRETE.defaultBlockState();
        BlockState light = Blocks.SEA_LANTERN.defaultBlockState();
        BlockState ladder = Blocks.LADDER.defaultBlockState().setValue(LadderBlock.FACING, Direction.NORTH);

        // Vertical service lift from the existing low access gallery.
        for (int y = -26; y <= -7; y++)
        {
            level.setBlock(centre.offset(0, y, 14), frame, 3);
            level.setBlock(centre.offset(0, y, 13), ladder, 3);
            if (y % 4 == 0)
            {
                level.setBlock(centre.offset(1, y, 14), light, 3);
            }
        }

        // Enclosed high catwalk. Its inner lip at z=6 is within interaction
        // reach of the body but remains clear of the launch hitbox.
        for (int z = 6; z <= 14; z++)
        {
            for (int x = -3; x <= 3; x++)
            {
                level.setBlock(centre.offset(x, gantryY, z), x == 0 && z % 3 == 0 ? accent : dark, 3);
                if (Math.abs(x) == 3)
                {
                    level.setBlock(centre.offset(x, gantryY + 1, z), Blocks.IRON_BARS.defaultBlockState(), 3);
                    level.setBlock(centre.offset(x, gantryY + 3, z), frame, 3);
                }
            }
            level.setBlock(centre.offset(0, gantryY + 4, z), z % 3 == 0 ? light : frame, 3);
        }

        // Cut a personnel doorway through the shaft shell at upper-back height.
        for (int x = -2; x <= 2; x++)
        {
            for (int y = gantryY + 1; y <= gantryY + 3; y++)
            {
                level.setBlock(centre.offset(x, y, 7), Blocks.AIR.defaultBlockState(), 3);
            }
        }
        level.setBlock(centre.offset(-3, gantryY + 2, 7), accent, 3);
        level.setBlock(centre.offset(3, gantryY + 2, 7), accent, 3);
    }

    private static void deployUnit(ServerLevel level, BlockPos bay, EvaUnit01Entity unit)
    {
        if (unit == null)
        {
            return;
        }
        // Face away from the +Z service gallery, placing the gantry at the
        // dorsal/rear side of every Unit rather than in front of its face.
        unit.moveTo(bay.getX() + 0.5D, bay.getY() - 29.0D, bay.getZ() + 0.5D, 180.0F, 0.0F);
        unit.setPersistenceRequired();
        level.addFreshEntity(unit);
    }

    private static void buildCommandBunker(ServerLevel level, BlockPos centre, BlockState armor,
                                           BlockState nerv, BlockState glass)
    {
        for (int y = 0; y <= 9; y++)
        {
            int rx = 15 - y;
            int rz = 8 - Math.min(y, 6);
            for (int x = -rx; x <= rx; x++)
            {
                for (int z = -rz; z <= rz; z++)
                {
                    boolean shell = Math.abs(x) == rx || Math.abs(z) == rz || y == 0;
                    if (shell)
                    {
                        level.setBlock(centre.offset(x, y, z), y >= 5 && Math.abs(z) == rz ? glass : armor, 3);
                    }
                }
            }
        }
        for (int x = -10; x <= 10; x++)
        {
            level.setBlock(centre.offset(x, 1, -8), x % 4 == 0 ? Blocks.REDSTONE_LAMP.defaultBlockState() : nerv, 3);
        }
    }

    private static void buildRetractableTower(ServerLevel level, BlockPos base,
                                              BlockState armor, BlockState glass)
    {
        for (int y = 0; y <= 22; y++)
        {
            int half = y > 17 ? 2 : 3;
            for (int x = -half; x <= half; x++)
            {
                for (int z = -half; z <= half; z++)
                {
                    if (Math.abs(x) == half || Math.abs(z) == half)
                    {
                        level.setBlock(base.offset(x, y, z), y % 5 == 2 ? glass : armor, 3);
                    }
                }
            }
        }
    }
}
