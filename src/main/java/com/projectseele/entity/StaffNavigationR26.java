package com.projectseele.entity;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.navigation.GroundPathNavigation;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.pathfinder.*;

/** Staff routes go around furniture, including the otherwise walkable seat top. */
public final class StaffNavigationR26 extends GroundPathNavigation
{
    public StaffNavigationR26(Mob mob, Level level) { super(mob,level); }
    private static boolean furniture(BlockGetter level, BlockPos pos)
    {
        String id=BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock()).getPath();
        return id.contains("chair")||id.endsWith("_stool")||id.equals("command_seat_back");
    }
    @Override protected PathFinder createPathFinder(int range)
    {
        this.nodeEvaluator=new WalkNodeEvaluator()
        {
            @Override public BlockPathTypes getBlockPathType(BlockGetter level,int x,int y,int z)
            {
                BlockPos pos=new BlockPos(x,y,z);
                if(furniture(level,pos)||furniture(level,pos.below()))return BlockPathTypes.BLOCKED;
                return super.getBlockPathType(level,x,y,z);
            }
        };
        this.nodeEvaluator.setCanPassDoors(true);
        this.nodeEvaluator.setCanOpenDoors(true);
        return new PathFinder(this.nodeEvaluator,range);
    }
}
