package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DoubleBlockHalf;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * Two-block command-chair backrest.
 *
 * <p>The command room previously used {@code iron_trapdoor} panels as seat
 * backs.  Those are redstone components: any powered rail, button or lever
 * update in the dais swings the whole row open.  This block is inert - it
 * carries no power state and reacts to nothing - so a chair back can never be
 * toggled by the console wiring around it.</p>
 *
 * <p>{@link HorizontalDirectionalBlock#FACING} points at the seat: the padded
 * face looks that way and the panel hugs that side of its own cell, so a back
 * placed in the cell behind a chair touches the chair, exactly like the open
 * trapdoor it replaces.</p>
 */
public class CommandSeatBackBlock extends HorizontalDirectionalBlock
{
    private static final VoxelShape NORTH_SHAPE =
            Block.box(0.0D, 0.0D, 0.0D, 16.0D, 16.0D, 5.0D);
    private static final VoxelShape SOUTH_SHAPE =
            Block.box(0.0D, 0.0D, 11.0D, 16.0D, 16.0D, 16.0D);
    private static final VoxelShape WEST_SHAPE =
            Block.box(0.0D, 0.0D, 0.0D, 5.0D, 16.0D, 16.0D);
    private static final VoxelShape EAST_SHAPE =
            Block.box(11.0D, 0.0D, 0.0D, 16.0D, 16.0D, 16.0D);

    public CommandSeatBackBlock(Properties properties)
    {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any()
                .setValue(FACING, Direction.NORTH)
                .setValue(BlockStateProperties.DOUBLE_BLOCK_HALF,
                        DoubleBlockHalf.LOWER));
    }

    @Override
    protected void createBlockStateDefinition(
            StateDefinition.Builder<Block, BlockState> builder)
    {
        builder.add(FACING, BlockStateProperties.DOUBLE_BLOCK_HALF);
    }

    @Override
    public VoxelShape getShape(BlockState state, BlockGetter level,
                               BlockPos position, CollisionContext context)
    {
        return switch (state.getValue(FACING))
        {
            case SOUTH -> SOUTH_SHAPE;
            case WEST -> WEST_SHAPE;
            case EAST -> EAST_SHAPE;
            default -> NORTH_SHAPE;
        };
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context)
    {
        BlockPos position = context.getClickedPos();
        if (position.getY() >= context.getLevel().getMaxBuildHeight() - 1
                || !context.getLevel().getBlockState(position.above())
                .canBeReplaced(context))
        {
            return null;
        }
        // The padded face must look at whoever placed it: you stand in front
        // of the chair and drop the back into the cell behind it.
        return this.defaultBlockState().setValue(FACING,
                context.getHorizontalDirection().getOpposite());
    }

    @Override
    public void setPlacedBy(Level level, BlockPos position, BlockState state,
                            LivingEntity placer, ItemStack stack)
    {
        level.setBlock(position.above(), state.setValue(
                        BlockStateProperties.DOUBLE_BLOCK_HALF,
                        DoubleBlockHalf.UPPER),
                Block.UPDATE_ALL);
    }

    @Override
    public boolean canSurvive(BlockState state, LevelReader level,
                              BlockPos position)
    {
        if (state.getValue(BlockStateProperties.DOUBLE_BLOCK_HALF)
                != DoubleBlockHalf.UPPER)
        {
            return true;
        }
        BlockState below = level.getBlockState(position.below());
        return below.is(this) && below.getValue(
                BlockStateProperties.DOUBLE_BLOCK_HALF)
                == DoubleBlockHalf.LOWER;
    }

    /**
     * Removing either half removes the other one silently, so a backrest can
     * never be left as a floating upper panel.  The half the player actually
     * broke still runs its own loot table, so exactly one item drops.
     */
    @Override
    public BlockState updateShape(BlockState state, Direction direction,
                                  BlockState neighbour, LevelAccessor level,
                                  BlockPos position, BlockPos neighbourPosition)
    {
        DoubleBlockHalf half =
                state.getValue(BlockStateProperties.DOUBLE_BLOCK_HALF);
        boolean towardsOtherHalf = half == DoubleBlockHalf.LOWER
                ? direction == Direction.UP : direction == Direction.DOWN;
        if (!towardsOtherHalf)
        {
            return state;
        }
        boolean intact = neighbour.is(this)
                && neighbour.getValue(BlockStateProperties.DOUBLE_BLOCK_HALF)
                != half;
        return intact ? state : Blocks.AIR.defaultBlockState();
    }

    @Override
    public BlockState rotate(BlockState state, Rotation rotation)
    {
        return state.setValue(FACING, rotation.rotate(state.getValue(FACING)));
    }

    @Override
    public BlockState mirror(BlockState state, Mirror mirror)
    {
        return state.rotate(mirror.getRotation(state.getValue(FACING)));
    }
}
