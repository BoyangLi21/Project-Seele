package com.projectseele.world;

import net.minecraft.core.*;
import net.minecraft.world.*;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.*;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.state.*;
import net.minecraft.world.level.block.state.properties.IntegerProperty;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.shapes.*;

/** Physical upper cells let vanilla picking/collision find the entire tall fixture. */
public final class PeriodFixturePartBlock extends Block
{
    public static final IntegerProperty OFFSET=IntegerProperty.create("offset",1,2);
    public PeriodFixturePartBlock(Properties properties){super(properties);registerDefaultState(stateDefinition.any().setValue(OFFSET,1));}
    @Override protected void createBlockStateDefinition(StateDefinition.Builder<Block,BlockState> builder){builder.add(OFFSET);}
    private BlockPos root(BlockState state,BlockPos pos){return pos.below(state.getValue(OFFSET));}
    private boolean valid(BlockState state,BlockGetter level,BlockPos pos)
    {
        var base=level.getBlockState(root(state,pos));return base.getBlock() instanceof PeriodFixtureBlock
                &&PeriodFixtureBlock.upperCells(base.getValue(PeriodFixtureBlock.KIND))>=state.getValue(OFFSET);
    }
    @Override public RenderShape getRenderShape(BlockState state){return RenderShape.INVISIBLE;}
    // Lighting runs while chunks are incomplete and may run off-thread.
    // It must not ask the owning Level to load the base of a proxy part.
    @Override public boolean propagatesSkylightDown(BlockState state,BlockGetter level,BlockPos pos){return true;}
    @Override public int getLightBlock(BlockState state,BlockGetter level,BlockPos pos){return 0;}
    @Override public VoxelShape getOcclusionShape(BlockState state,BlockGetter level,BlockPos pos){return Shapes.empty();}
    @Override public VoxelShape getShape(BlockState state,BlockGetter level,BlockPos pos,CollisionContext context)
    {
        if(!valid(state,level,pos))return Shapes.empty();var base=level.getBlockState(root(state,pos));
        return PeriodFixtureBlock.slice(PeriodFixtureBlock.fullShape(base).move(0,-state.getValue(OFFSET),0));
    }
    @Override public BlockState updateShape(BlockState state,Direction direction,BlockState other,LevelAccessor level,BlockPos pos,BlockPos otherPos)
    {return valid(state,level,pos)?state:Blocks.AIR.defaultBlockState();}
    @Override public InteractionResult use(BlockState state,Level level,BlockPos pos,Player player,InteractionHand hand,BlockHitResult hit)
    {
        BlockPos root=root(state,pos);var base=level.getBlockState(root);
        return valid(state,level,pos)?base.use(level,player,hand,new BlockHitResult(hit.getLocation(),hit.getDirection(),root,hit.isInside())):InteractionResult.PASS;
    }
    @Override public void onRemove(BlockState state,Level level,BlockPos pos,BlockState replacement,boolean moving)
    {
        if(!level.isClientSide&&replacement.getBlock()!=this&&valid(state,level,pos))level.destroyBlock(root(state,pos),true);
        super.onRemove(state,level,pos,replacement,moving);
    }
    @Override public void playerWillDestroy(Level level,BlockPos pos,BlockState state,Player player)
    {
        if(!level.isClientSide&&valid(state,level,pos))level.destroyBlock(root(state,pos),!player.isCreative());
        super.playerWillDestroy(level,pos,state,player);
    }
    @Override public net.minecraft.world.item.ItemStack getCloneItemStack(BlockGetter level,BlockPos pos,BlockState state)
    {
        var base=level.getBlockState(root(state,pos));return valid(state,level,pos)?base.getBlock().getCloneItemStack(level,root(state,pos),base):net.minecraft.world.item.ItemStack.EMPTY;
    }
}
