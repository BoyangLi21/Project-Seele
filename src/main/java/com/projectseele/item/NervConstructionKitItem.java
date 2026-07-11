package com.projectseele.item;

import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/** Builds an original compact NERV sortie complex for visual and combat testing. */
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
        BlockState floor = Blocks.SMOOTH_STONE.defaultBlockState();
        BlockState armor = Blocks.GRAY_CONCRETE.defaultBlockState();
        BlockState nerv = Blocks.BLACK_CONCRETE.defaultBlockState();
        BlockState warning = Blocks.ORANGE_CONCRETE.defaultBlockState();
        BlockState glass = Blocks.TINTED_GLASS.defaultBlockState();

        for (int x = -24; x <= 24; x++)
        {
            for (int z = -24; z <= 24; z++)
            {
                level.setBlock(origin.offset(x, 0, z), floor, 3);
            }
        }
        // Central 11x11 launch shaft and alternating warning stripes.
        for (int y = 1; y <= 34; y++)
        {
            for (int x = -6; x <= 6; x++)
            {
                for (int z = -6; z <= 6; z++)
                {
                    boolean wall = Math.abs(x) >= 5 || Math.abs(z) >= 5;
                    if (wall)
                    {
                        level.setBlock(origin.offset(x, y, z), (y / 3) % 2 == 0 ? armor : warning, 3);
                    }
                }
            }
        }
        // EVA restraint cage: four pylons, cross braces and a luminous launch bed.
        for (int y = 1; y <= 25; y++)
        {
            for (int sx : new int[] {-4, 4})
            {
                for (int sz : new int[] {-4, 4})
                {
                    level.setBlock(origin.offset(sx, y, sz), nerv, 3);
                }
            }
            if (y % 6 == 0)
            {
                for (int x = -4; x <= 4; x++)
                {
                    level.setBlock(origin.offset(x, y, -4), nerv, 3);
                    level.setBlock(origin.offset(x, y, 4), nerv, 3);
                }
            }
        }
        for (int x = -4; x <= 4; x++)
        {
            for (int z = -4; z <= 4; z++)
            {
                level.setBlock(origin.offset(x, 1, z), (Math.abs(x) == 4 || Math.abs(z) == 4)
                        ? Blocks.SEA_LANTERN.defaultBlockState() : nerv, 3);
            }
        }
        // Low command pyramid beside the shaft.
        BlockPos pyramid = origin.offset(14, 1, 12);
        for (int y = 0; y < 9; y++)
        {
            int radius = 10 - y;
            for (int x = -radius; x <= radius; x++)
            {
                for (int z = -radius; z <= radius; z++)
                {
                    if (Math.abs(x) == radius || Math.abs(z) == radius || y == 0)
                    {
                        level.setBlock(pyramid.offset(x, y, z), y >= 6 ? glass : armor, 3);
                    }
                }
            }
        }
        // Four retractable-city silhouettes around the perimeter.
        for (int[] tower : new int[][] {{-18,-18},{-18,18},{18,-18},{18,18}})
        {
            for (int y = 1; y <= 18; y++)
            {
                int half = y > 14 ? 2 : 3;
                for (int x = -half; x <= half; x++)
                {
                    for (int z = -half; z <= half; z++)
                    {
                        if (Math.abs(x) == half || Math.abs(z) == half)
                        {
                            level.setBlock(origin.offset(tower[0] + x, y, tower[1] + z),
                                    y % 5 == 0 ? glass : armor, 3);
                        }
                    }
                }
            }
        }
        if (context.getPlayer() != null)
        {
            context.getPlayer().displayClientMessage(Component.translatable("message.projectseele.nerv_built"), false);
        }
        return InteractionResult.CONSUME;
    }
}
