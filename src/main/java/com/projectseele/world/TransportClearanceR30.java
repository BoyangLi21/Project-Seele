package com.projectseele.world;

import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkStatus;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraft.util.Mth;
import net.minecraft.world.level.levelgen.Heightmap;

/** A pickup checks the whole vertical corridor, including the aircraft's wings. */
public final class TransportClearanceR30
{
    public static final double HOIST_OFFSET=112;
    private static final TicketType<ChunkPos> AIRSPACE=TicketType.create("airlift_clearance_r30",java.util.Comparator.comparingLong(ChunkPos::toLong),120);
    public static String pickupProblem(ServerLevel level,EvaUnit01Entity eva)
    {
        var centre=new ChunkPos(eva.blockPosition());boolean loaded=true;
        level.getChunkSource().addRegionTicket(AIRSPACE,centre,8,centre);
        for(int x=centre.x-5;x<=centre.x+5;x++)for(int z=centre.z-4;z<=centre.z+4;z++)
            if(!level.getChunkSource().hasChunk(x,z)){level.getChunkSource().getChunkFuture(x,z,ChunkStatus.FULL,true);loaded=false;}
        if(!loaded)return "正在检查并加载起吊点上方空域";
        double top=level.getMaxBuildHeight(),x=eva.getX(),y=eva.getY(),z=eva.getZ(),radius=Math.max(11,eva.getBbWidth()/2D+2);
        if(y<top&&level.getBlockCollisions(eva,new AABB(x-radius,y+.1,z-radius,x+radius,top,z+radius)).iterator().hasNext())
            return "机体上方有遮挡，等待垂直起吊通道清空";
        if(y+HOIST_OFFSET-15<top&&level.getBlockCollisions(eva,new AABB(x-72,y+HOIST_OFFSET-15,z-60,x+72,top,z+60)).iterator().hasNext())
            return "运输机机翼或吊架上方有遮挡，等待空域清空";
        return "";
    }
    public static Vec3 landing(ServerLevel l,Vec3 requested,EvaUnit01Entity eva)
    {
        for(int radius:new int[]{0,16,32,48})for(int n=0;n<(radius==0?1:8);n++)
        {
            int x=Mth.floor(requested.x+radius*Math.cos(n*Math.PI/4)),z=Mth.floor(requested.z+radius*Math.sin(n*Math.PI/4));
            int y=l.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,x,z);
            while(y>l.getMinBuildHeight()+2&&l.getBlockState(new BlockPos(x,y-1,z)).getCollisionShape(l,new BlockPos(x,y-1,z)).isEmpty())y--;
            Vec3 p=new Vec3(x+.5,y,z+.5);boolean ground=true;
            for(int[] o:new int[][]{{0,0},{-5,-3},{5,-3},{-5,3},{5,3}})
            {
                boolean support=false;for(int dy=1;dy<=2;dy++){BlockPos q=BlockPos.containing(p.add(o[0],-dy,o[1]));if(!l.getBlockState(q).getCollisionShape(l,q).isEmpty()){support=true;break;}}
                if(!support){ground=false;break;}
            }
            double half=Math.max(11,eva.getBbWidth()/2D+2);
            if(!ground||!l.noCollision(eva,new AABB(p.x-half,p.y+.08,p.z-half,p.x+half,p.y+63,p.z+half)))continue;
            if(l.getBlockCollisions(eva,new AABB(p.x-72,p.y+HOIST_OFFSET-15,p.z-60,p.x+72,p.y+HOIST_OFFSET+22,p.z+60)).iterator().hasNext())continue;
            if(!l.getEntities(eva,new AABB(p.x-14,p.y,p.z-14,p.x+14,p.y+65,p.z+14),e->e instanceof EvaUnit01Entity&&e.isAlive()).isEmpty())continue;
            return p;
        }
        return null;
    }
    private TransportClearanceR30() {}
}
