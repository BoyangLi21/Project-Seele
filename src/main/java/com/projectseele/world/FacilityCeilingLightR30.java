package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

/** Thin ceiling fixture; its circuit, rather than neighbouring redstone, owns LIT. */
public final class FacilityCeilingLightR30 extends Block
{
    private static final VoxelShape SHAPE=Block.box(1,14,1,15,16,15);
    public FacilityCeilingLightR30(Properties p){super(p);registerDefaultState(stateDefinition.any().setValue(BlockStateProperties.LIT,true).setValue(BlockStateProperties.HANGING,true));}
    @Override protected void createBlockStateDefinition(StateDefinition.Builder<Block,BlockState> builder){builder.add(BlockStateProperties.LIT,BlockStateProperties.HANGING);}
    @Override public VoxelShape getShape(BlockState state,BlockGetter level,BlockPos pos,CollisionContext context){return state.getValue(BlockStateProperties.HANGING)?SHAPE:Block.box(2,0,2,14,.4,14);}
    @Override public VoxelShape getCollisionShape(BlockState state,BlockGetter level,BlockPos pos,CollisionContext context){return net.minecraft.world.phys.shapes.Shapes.empty();}
}
