package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.entity.*;
import net.minecraft.world.level.block.state.*;
import com.projectseele.registry.ModBlockEntities;

public final class StationDepartureBoardBlock extends HorizontalDirectionalBlock implements EntityBlock
{
    public static final net.minecraft.world.level.block.state.properties.BooleanProperty WAYFINDING = net.minecraft.world.level.block.state.properties.BooleanProperty.create("wayfinding");
    public StationDepartureBoardBlock(Properties properties)
    {
        super(properties);registerDefaultState(stateDefinition.any().setValue(FACING, Direction.NORTH).setValue(WAYFINDING,false));
    }
    @Override protected void createBlockStateDefinition(StateDefinition.Builder<Block,BlockState> builder) { builder.add(FACING,WAYFINDING); }
    @Override public BlockState getStateForPlacement(net.minecraft.world.item.context.BlockPlaceContext context) { return defaultBlockState().setValue(FACING,context.getHorizontalDirection().getOpposite()); }
    @Override public BlockState rotate(BlockState state,Rotation rotation) { return state.setValue(FACING,rotation.rotate(state.getValue(FACING))); }
    @Override public BlockState mirror(BlockState state,Mirror mirror) { return rotate(state,mirror.getRotation(state.getValue(FACING))); }
    @Override public BlockEntity newBlockEntity(BlockPos pos,BlockState state) { return new StationDepartureBoardBlockEntity(pos,state); }
    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level,BlockState state,BlockEntityType<T> type)
    {
        return level.isClientSide || type != ModBlockEntities.STATION_DEPARTURE_BOARD.get() ? null : (l,p,s,be) -> ((StationDepartureBoardBlockEntity)be).tickServer();
    }
    @Override public net.minecraft.world.phys.shapes.VoxelShape getShape(BlockState state,net.minecraft.world.level.BlockGetter level,BlockPos pos,net.minecraft.world.phys.shapes.CollisionContext context)
    {
        double top=state.getValue(WAYFINDING)?31:20;
        return state.getValue(FACING).getAxis()==Direction.Axis.Z ? Block.box(-16,4,6,32,top,10) : Block.box(6,4,-16,10,top,32);
    }
}
