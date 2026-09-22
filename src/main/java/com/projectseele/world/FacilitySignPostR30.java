package com.projectseele.world;

import net.minecraft.core.*;
import net.minecraft.world.level.*;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.state.*;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.phys.shapes.*;

/** A narrow station-sign stanchion with an optional real bracket, not a solid walkway obstruction. */
public final class FacilitySignPostR30 extends HorizontalDirectionalBlock
{
    public static final BooleanProperty ARM=BooleanProperty.create("arm");
    private static final VoxelShape POST=Block.box(6,0,6,10,16,10);
    public FacilitySignPostR30(Properties p){super(p);registerDefaultState(stateDefinition.any().setValue(FACING,Direction.NORTH).setValue(ARM,false));}
    @Override protected void createBlockStateDefinition(StateDefinition.Builder<Block,BlockState> builder){builder.add(FACING,ARM);}
    @Override public VoxelShape getShape(BlockState s,BlockGetter l,BlockPos p,CollisionContext c)
    {
        if(!s.getValue(ARM))return POST;
        return Shapes.or(POST,switch(s.getValue(FACING)){case NORTH->Block.box(6,8,0,10,12,10);case SOUTH->Block.box(6,8,6,10,12,16);case EAST->Block.box(6,8,6,16,12,10);case WEST->Block.box(0,8,6,10,12,10);default->POST;});
    }
    @Override public BlockState rotate(BlockState s,Rotation r){return s.setValue(FACING,r.rotate(s.getValue(FACING)));}
    @Override public BlockState mirror(BlockState s,Mirror m){return rotate(s,m.getRotation(s.getValue(FACING)));}
}
