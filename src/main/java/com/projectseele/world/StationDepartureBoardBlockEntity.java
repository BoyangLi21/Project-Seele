package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModBlockEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.game.ClientboundBlockEntityDataPacket;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import java.util.List;

public final class StationDepartureBoardBlockEntity extends BlockEntity
{
    private BlockPos platform = BlockPos.ZERO;
    private String station = "", route = "";
    private List<String> rows = List.of("運行情報を確認中");
    private boolean warned;
    private long linkedPlatformId = -1, nativeClock;
    private List<Long> departures = List.of();
    public StationDepartureBoardBlockEntity(BlockPos pos, BlockState state) { super(ModBlockEntities.STATION_DEPARTURE_BOARD.get(),pos,state); }
    public String title() { return route + "  発車案内 / JST"; }
    public String station() { return station; }
    public List<String> rows() { return rows; }
    public long linkedPlatformId() { return linkedPlatformId; }
    public long nativeClock() { return nativeClock; }
    public List<Long> departureTimes() { return departures; }
    public void tickServer()
    {
        if (level == null || level.getGameTime() % 20 != Math.floorMod(worldPosition.asLong(),20)) return;
        try
        {
            var snapshot = NativeStationDepartures.read(platform);
            linkedPlatformId = snapshot.platformId();nativeClock = snapshot.clock();departures = snapshot.departures();
            if (!rows.equals(snapshot.rows()))
            {
                rows = snapshot.rows();setChanged();
                level.sendBlockUpdated(worldPosition,getBlockState(),getBlockState(),Block.UPDATE_CLIENTS);
            }
        }
        catch (ReflectiveOperationException failure)
        {
            if (!warned) { warned = true;ProjectSeele.LOGGER.warn("Station board could not read native MTR departures at {}",worldPosition,failure); }
        }
    }
    @Override protected void saveAdditional(CompoundTag tag)
    {
        super.saveAdditional(tag);tag.putLong("PlatformCentre",platform.asLong());tag.putString("Station",station);tag.putString("Route",route);
        tag.putString("Row0",rows.isEmpty()?"":rows.get(0));tag.putString("Row1",rows.size()>1?rows.get(1):"");
    }
    @Override public void load(CompoundTag tag)
    {
        super.load(tag);platform=BlockPos.of(tag.getLong("PlatformCentre"));station=tag.getString("Station");route=tag.getString("Route");
        rows=tag.getString("Row1").isEmpty()?List.of(tag.getString("Row0")):List.of(tag.getString("Row0"),tag.getString("Row1"));
    }
    @Override public CompoundTag getUpdateTag() { return saveWithoutMetadata(); }
    @Override public ClientboundBlockEntityDataPacket getUpdatePacket() { return ClientboundBlockEntityDataPacket.create(this); }
    @Override public net.minecraft.world.phys.AABB getRenderBoundingBox() { return new net.minecraft.world.phys.AABB(worldPosition).inflate(2); }
}
