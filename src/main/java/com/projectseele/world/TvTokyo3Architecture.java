package com.projectseele.world;

import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/** Original modular facades for the private TV preview, in the active EVA scale. */
public final class TvTokyo3Architecture
{
    private TvTokyo3Architecture() {}

    public static ThirdTokyoSurfaceBuilder.TowerSpec spec(ThirdTokyoSurfaceBuilder.TowerSpec original)
    {
        int x = original.x(), z = original.z();
        int hash = Math.floorMod(x / 40 * 31 + z / 40 * 17, 97);
        int height = original.outerWard() ? 20 + (hash % 4) * 7
                : hash % 11 == 0 ? 96 + (hash % 4) * 8 : 44 + (hash % 6) * 6;
        return new ThirdTokyoSurfaceBuilder.TowerSpec(x, z, height,
                original.outerWard() ? 9 : hash % 11 == 0 ? 10 : 9,
                original.outerWard(), true);
    }

    public static BlockState wall(int y, int span, ThirdTokyoSurfaceBuilder.TowerSpec tower)
    {
        int style = Math.floorMod(tower.x() / 40 * 17 + tower.z() / 40 * 13, 6);
        int edge = Math.abs(span), half = tower.halfSize();
        BlockState pale = (style == 1 || style == 4 ? Blocks.WHITE_CONCRETE : Blocks.LIGHT_GRAY_CONCRETE).defaultBlockState();
        BlockState frame = Blocks.POLISHED_ANDESITE.defaultBlockState();
        BlockState dark = Blocks.DEEPSLATE_TILES.defaultBlockState();
        BlockState glass = Blocks.GRAY_STAINED_GLASS.defaultBlockState();
        if (y <= 4) return edge >= half - 1 && y == 3
                ? Blocks.RED_TERRACOTTA.defaultBlockState() : dark;
        if (edge == half) return frame;
        if (y > tower.height() - 7)
            return edge % 3 == 0 || y == tower.height() - 6 ? frame : dark;
        if (tower.outerWard())
            return edge >= half - 1 || y % 5 == 0 ? pale : y % 5 <= 2 ? glass : frame;
        return switch (style)
        {
            // Paired narrow service slots, broad opaque armour cheeks.
            case 0 -> edge == 2 || edge == 6 ? dark : y % 12 == 0 ? frame : pale;
            // Vertical structural rhythm with small, deeply shaded openings.
            case 1 -> span % 4 == 0 ? frame : y % 7 == 3 || y % 7 == 4 ? glass : pale;
            // Repeated equipment cassettes, with their seams held in shadow.
            case 2 -> y % 14 <= 1 || edge >= half - 1 ? dark
                    : y % 14 == 3 || y % 14 == 11 ? frame : edge % 5 == 0 ? dark : pale;
            // Quiet civilian office bands within the same restrained palette.
            case 3 -> edge % 5 == 0 ? frame : y % 6 <= 1 ? glass : pale;
            // Opaque armoured spine with intermittent horizontal ventilation.
            case 4 -> edge <= 1 ? dark : y % 10 == 2 && edge <= half - 2 ? dark : pale;
            default -> y % 9 <= 1 ? frame : edge == 4 || edge == 5 ? glass
                    : edge >= half - 1 ? dark : pale;
        };
    }
}
