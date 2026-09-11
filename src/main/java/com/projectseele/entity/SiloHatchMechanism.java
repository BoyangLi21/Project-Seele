package com.projectseele.entity;

import net.minecraft.util.Mth;

/** Rigid lift-and-stack shutters fitting the existing 42 metre shaft pitch. */
public final class SiloHatchMechanism
{
    public static final int PANELS = 4;
    public static final double WIDTH = 4.0D;
    public static final double POCKET_X = 16.4D;
    public static final double CASE_OUTER_X = 20.7D;
    public static final double PANEL_TOP = .98D;

    public record Panel(double x, double y) {}

    public static Panel panel(int index, float open)
    {
        // Separate the tiers before translating: a panel never passes through
        // the panel above it, the frame, or the neighbouring shaft's mechanism.
        double lift = smooth(open / .30F);
        double travel = smooth((open - .30F) / .70F);
        double closedX = index * WIDTH;
        return new Panel(closedX + (POCKET_X - closedX) * travel,
                (1.10D + (PANELS - 1 - index) * 1.10D) * lift);
    }

    private static double smooth(float value)
    {
        double t = Mth.clamp(value, 0, 1);
        return t * t * (3 - 2 * t);
    }

    private SiloHatchMechanism() {}
}
