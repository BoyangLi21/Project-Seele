package com.projectseele.util;

import java.util.Random;
import net.minecraft.world.level.biome.BiomeManager;

/** Compare against the actual unmixed Minecraft method, including cache collisions. */
public final class BiomeCornerCacheTest
{
    public static void main(String[] args)throws Exception
    {
        var vanilla=BiomeManager.class.getDeclaredMethod("getFiddledDistance",long.class,int.class,int.class,int.class,double.class,double.class,double.class);
        vanilla.setAccessible(true);Random random=new Random(1701);
        long[] seeds={0,1,-1,Long.MIN_VALUE,Long.MAX_VALUE,8936273262L};int checked=0;
        for(long seed:seeds)for(int n=0;n<12000;n++)
        {
            int x=n%2==0?random.nextInt(24)-12:random.nextInt(15000000)-7500000;
            int y=random.nextInt(4096)-2048,z=n%2==0?random.nextInt(24)-12:random.nextInt(15000000)-7500000;
            for(int repeat=0;repeat<3;repeat++)
            {
                double dx=(random.nextInt(8)-4)/4.0,dy=(random.nextInt(8)-4)/4.0,dz=(random.nextInt(8)-4)/4.0;
                double expected=(double)vanilla.invoke(null,seed,x,y,z,dx,dy,dz),actual=BiomeCornerCache.distance(seed,x,y,z,dx,dy,dz);
                if(Double.doubleToLongBits(actual)!=Double.doubleToLongBits(expected))throw new AssertionError("Biome selection changed at "+x+","+y+","+z);
                checked++;
            }
        }
        System.out.println("Exact vanilla biome-corner comparisons passed: "+checked);
    }
}
