package com.projectseele.world;

import com.projectseele.registry.ModBlockEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.*;
import net.minecraft.network.protocol.game.ClientboundBlockEntityDataPacket;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import java.util.*;

public final class PeriodFixtureBlockEntity extends BlockEntity
{
    private String title="站内导览";
    private List<String> lines=List.of("保持通道畅通", "按标识前往站台");
    private long clock, received;
    public PeriodFixtureBlockEntity(BlockPos pos,BlockState state) { super(ModBlockEntities.PERIOD_FIXTURE.get(),pos,state); }
    public String title(){return title;}
    public List<String> lines(){return lines;}
    public long clockMillis(){return clock==0?System.currentTimeMillis():clock+(System.nanoTime()-received)/1_000_000;}
    public void updateClock()
    {
        if(level==null||level.getGameTime()%20!=0)return;
        clock=System.currentTimeMillis();received=System.nanoTime();setChanged();level.sendBlockUpdated(worldPosition,getBlockState(),getBlockState(),2);
    }
    @Override protected void saveAdditional(CompoundTag tag)
    {
        super.saveAdditional(tag);tag.putString("Title",title);var list=new ListTag();lines.forEach(v->list.add(StringTag.valueOf(v)));tag.put("Lines",list);tag.putLong("Clock",clock);
    }
    @Override public void load(CompoundTag tag)
    {
        super.load(tag);if(tag.contains("Title"))title=limit(tag.getString("Title"),40);
        if(tag.contains("Lines")){var list=new ArrayList<String>();for(var item:tag.getList("Lines",8)){if(list.size()==6)break;list.add(limit(item.getAsString(),60));}lines=List.copyOf(list);}
        clock=tag.getLong("Clock");received=System.nanoTime();
    }
    private static String limit(String text,int max){return text.substring(0,Math.min(text.length(),max));}
    @Override public CompoundTag getUpdateTag(){return saveWithoutMetadata();}
    @Override public ClientboundBlockEntityDataPacket getUpdatePacket(){return ClientboundBlockEntityDataPacket.create(this);}
    @Override public AABB getRenderBoundingBox(){return new AABB(worldPosition).expandTowards(0,1.5,0).inflate(1.1,0,1.1);}
}
