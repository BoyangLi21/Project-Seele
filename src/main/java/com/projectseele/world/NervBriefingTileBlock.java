package com.projectseele.world;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.IntegerProperty;
/** Forty-eight flush tiles display one continuous 12 by 4 tactical panel. */
public final class NervBriefingTileBlock extends Block
{
    public static final IntegerProperty PART=IntegerProperty.create("part",0,47);
    public NervBriefingTileBlock(Properties p){super(p);registerDefaultState(stateDefinition.any().setValue(PART,0));}
    @Override protected void createBlockStateDefinition(StateDefinition.Builder<Block,BlockState> b){b.add(PART);}
}
