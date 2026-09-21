package com.projectseele.world;

/** One C1-continuous rail curve: hard initial catapult, steady climb, soft arrival. */
public final class LaunchMotionR29
{
    private static final double[] TIME = {0, .073, .20, .90, 1};
    private static final double[] HEIGHT = {0, .14, .30, .95, 1};
    private static final double[] SPEED = {0, 2.0, .85, .65, 0};

    public static double progress(double time)
    {
        if (time <= 0) return 0;
        if (time >= 1) return 1;
        int i = 0;
        while (time > TIME[i + 1]) i++;
        double span = TIME[i + 1] - TIME[i];
        double u = (time - TIME[i]) / span, u2 = u * u, u3 = u2 * u;
        return (2 * u3 - 3 * u2 + 1) * HEIGHT[i]
                + (u3 - 2 * u2 + u) * span * SPEED[i]
                + (-2 * u3 + 3 * u2) * HEIGHT[i + 1]
                + (u3 - u2) * span * SPEED[i + 1];
    }
    private LaunchMotionR29() {}
}
