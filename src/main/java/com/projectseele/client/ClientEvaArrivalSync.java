package com.projectseele.client;

import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;

/** Client-only bridge for the locally authoritative ridden-EVA correction. */
public final class ClientEvaArrivalSync
{
    private ClientEvaArrivalSync() {}

    public static void apply(int entityId, double x, double y, double z,
            float yaw, float pitch)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null)
        {
            return;
        }
        Entity entity = minecraft.level.getEntity(entityId);
        if (entity instanceof EvaUnit01Entity eva)
        {
            eva.applyClientArrivalSync(x, y, z, yaw, pitch);
        }
    }
}
