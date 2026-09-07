package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/** Static CRT furnishing; campaign control consoles retain their own authority. */
public final class NervWorkstationBlock extends HorizontalDirectionalBlock
{
    private static final VoxelShape NS = Shapes.or(Block.box(4,0,5,12,2,13),Block.box(1,2,4,15,13,14));
    private static final VoxelShape EW = Shapes.or(Block.box(5,0,4,13,2,12),Block.box(4,2,1,14,13,15));
    private static final VoxelShape NORTH = Shapes.or(Block.box(4,0,3,12,2,11),Block.box(1,2,2,15,13,12));
    private static final VoxelShape WEST = Shapes.or(Block.box(3,0,4,11,2,12),Block.box(2,2,1,12,13,15));

    public NervWorkstationBlock(Properties properties)
    {
        super(properties);
        registerDefaultState(stateDefinition.any().setValue(FACING,Direction.SOUTH));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block,BlockState> builder)
    {
        builder.add(FACING);
    }

    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context)
    {
        return defaultBlockState().setValue(FACING,context.getHorizontalDirection().getOpposite());
    }

    @Override
    public VoxelShape getShape(BlockState state,BlockGetter level,BlockPos position,CollisionContext context)
    {
        return switch(state.getValue(FACING))
        {
            case NORTH -> NORTH;
            case WEST -> WEST;
            case EAST -> EW;
            default -> NS;
        };
    }

    @Override
    public BlockState rotate(BlockState state,Rotation rotation)
    {
        return state.setValue(FACING,rotation.rotate(state.getValue(FACING)));
    }

    @Override
    public BlockState mirror(BlockState state,Mirror mirror)
    {
        return rotate(state,mirror.getRotation(state.getValue(FACING)));
    }
}
