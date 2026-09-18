package com.projectseele.world;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
/** Controlled by logistics only; neighbouring redstone cannot override a warning. */
public final class FacilityBeaconBlock extends Block
{
    public FacilityBeaconBlock(Properties properties){super(properties);registerDefaultState(stateDefinition.any().setValue(BlockStateProperties.LIT,false));}
    @Override protected void createBlockStateDefinition(StateDefinition.Builder<Block,BlockState> builder){builder.add(BlockStateProperties.LIT);}
}
