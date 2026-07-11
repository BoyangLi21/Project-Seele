package com.projectseele.fx;

import net.minecraft.world.phys.Vec3;

/**
 * The canonical Golden Dawn Tree of Life, upright (Keter apex, Malkuth
 * base), shared by the server (which parks the nine Mass-Production Evas on
 * the outer Sephirot) and the client sky effect (rings, paths, and the
 * crucified Unit-01 at Tiferet) so entities and light sit on the same spots.
 */
public final class TreeOfLifeLayout
{
    // Compact enough to read as one symbol while still framing 26-block EVAs.
    public static final float COLUMN_X = 42.0F;
    public static final float ROW_Y = 28.0F;
    public static final int TIFERET = 5;

    /** Local plane coordinates (x across, y up), index 0..9 = Keter..Malkuth. */
    public static final float[][] NODES = {
            {0.0F, 6.4F},   // 1 Keter (apex)
            {-1.0F, 5.4F},  // 2 Chokmah
            {1.0F, 5.4F},   // 3 Binah
            {-1.0F, 4.0F},  // 4 Chesed
            {1.0F, 4.0F},   // 5 Gevurah
            {0.0F, 3.2F},   // 6 Tiferet (centre: Unit-01)
            {-1.0F, 2.0F},  // 7 Netzach
            {1.0F, 2.0F},   // 8 Hod
            {0.0F, 1.2F},   // 9 Yesod
            {0.0F, 0.0F}    // 10 Malkuth (base)
    };

    /** The canonical 22 paths (verified against the traditional diagram). */
    public static final int[][] PATHS = {
            {0,1},{0,2},{0,5},{1,2},{1,3},{1,5},{2,4},{2,5},
            {3,4},{3,5},{3,6},{4,5},{4,7},{5,6},{5,7},{5,8},
            {6,7},{6,8},{7,8},{6,9},{7,9},{8,9}
    };

    private TreeOfLifeLayout() {}

    public static float localX(int index)
    {
        return NODES[index][0] * COLUMN_X;
    }

    public static float localY(int index)
    {
        return NODES[index][1] * ROW_Y;
    }

    /** World position of a Sephira for a tree rooted at origin, facing yaw. */
    public static Vec3 worldNode(Vec3 origin, float yawRad, int index)
    {
        float x = localX(index);
        float y = localY(index);
        double sin = Math.sin(yawRad);
        double cos = Math.cos(yawRad);
        // The tree plane's local +X maps into the horizontal plane rotated by yaw.
        return new Vec3(origin.x + x * cos, origin.y + y, origin.z - x * sin);
    }
}
