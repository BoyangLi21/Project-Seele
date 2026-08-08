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
            /*
             * The real pilot is nested player -> plug -> EVA.  A stale sensor
             * or preview camera can survive the last launch frame even after
             * the chassis has arrived correctly, leaving first person looking
             * at the bottom of the shaft.  Reclaim the ordinary player camera
             * only when this packet targets that player's actual root vehicle;
             * spectators and command-room feeds remain untouched.
             */
            if (minecraft.player != null
                    && minecraft.player.getRootVehicle() == eva
                    && minecraft.getCameraEntity() != minecraft.player)
            {
                minecraft.setCameraEntity(minecraft.player);
            }
        }
    }
}
