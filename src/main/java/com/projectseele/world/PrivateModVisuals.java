package com.projectseele.world;

import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;

/**
 * Registry-only visual compatibility for private test dependencies.
 *
 * <p>Project SEELE remains authoritative for every transform and state
 * transition.  These helpers may select a registered third-party block for a
 * cell SEELE already owns, but never call third-party controllers or APIs.</p>
 */
final class PrivateModVisuals
{
    private PrivateModVisuals() {}

    static BlockState block(String namespace, String path,
                            BlockState fallback)
    {
        return BuiltInRegistries.BLOCK.getOptional(
                        new ResourceLocation(namespace, path))
                .filter(block -> block != Blocks.AIR)
                .map(Block::defaultBlockState)
                .orElse(fallback);
    }

    static BlockState facing(BlockState state, Direction facing)
    {
        return state.hasProperty(BlockStateProperties.FACING)
                ? state.setValue(BlockStateProperties.FACING, facing)
                : state;
    }

    static BlockState axis(BlockState state, Direction.Axis axis)
    {
        return state.hasProperty(BlockStateProperties.AXIS)
                ? state.setValue(BlockStateProperties.AXIS, axis)
                : state;
    }

    /**
     * Applies a third-party block-state value without linking against that
     * mod's property classes.  This is used only for visual-only private
     * compatibility blocks such as Create girders.
     */
    static BlockState property(BlockState state, String name, String value)
    {
        for (Property<?> property : state.getProperties())
        {
            if (property.getName().equals(name))
            {
                return parsedProperty(state, property, value);
            }
        }
        return state;
    }

    private static <T extends Comparable<T>> BlockState parsedProperty(
            BlockState state, Property<T> property, String value)
    {
        return property.getValue(value)
                .map(parsed -> state.setValue(property, parsed))
                .orElse(state);
    }

    static boolean is(BlockState state, String namespace, String path)
    {
        return BuiltInRegistries.BLOCK.getOptional(
                        new ResourceLocation(namespace, path))
                .filter(block -> block != Blocks.AIR)
                .map(state::is)
                .orElse(false);
    }
}
