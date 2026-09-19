package com.projectseele.client.render;

import com.google.gson.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.Sheets;
import net.minecraft.client.resources.model.Material;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.entity.BlockEntity;
import java.util.*;

/** Presentation only, restricted to the documented NERV side rooms. */
public final class NervChestFinishR24
{
    private static final Material METAL=new Material(Sheets.CHEST_SHEET,new ResourceLocation("projectseele","entity/chest/nerv_equipment_r24"));
    private static List<int[]> rooms;
    private static List<int[]> rooms()
    {
        if(rooms!=null)return rooms;var result=new ArrayList<int[]>();
        try(var reader=Minecraft.getInstance().getResourceManager().getResource(new ResourceLocation("projectseele","style/nerv_side_rooms_r24.json")).orElseThrow().openAsReader())
        {
            for(var value:JsonParser.parseReader(reader).getAsJsonObject().getAsJsonArray("rooms"))
            {var r=value.getAsJsonObject();var b=r.getAsJsonArray("bounds");int f=r.get("floor").getAsInt();result.add(new int[]{b.get(0).getAsInt(),b.get(1).getAsInt(),b.get(2).getAsInt(),b.get(3).getAsInt(),f+1,f+10});}
        }
        catch(Exception error){com.projectseele.ProjectSeele.LOGGER.warn("NERV room finish unavailable",error);}
        rooms=List.copyOf(result);return rooms;
    }
    public static Material material(BlockEntity entity)
    {
        if(entity.getLevel()==null||!entity.getLevel().dimension().location().toString().equals("projectseele:geofront"))return null;
        var p=entity.getBlockPos();
        // The accepted main command suite and surface/UN/residential storage
        // retain their own appearance and all original block/inventory data.
        if(p.getX()>=6&&p.getX()<=52&&p.getY()>=-445&&p.getY()<=-388&&p.getZ()>=262&&p.getZ()<=365)return null;
        for(var b:rooms())if(p.getX()>=b[0]&&p.getX()<=b[1]&&p.getZ()>=b[2]&&p.getZ()<=b[3]&&p.getY()>=b[4]&&p.getY()<=b[5])return METAL;
        return null;
    }
    public static void clear(){rooms=null;}
    private NervChestFinishR24(){}
}
