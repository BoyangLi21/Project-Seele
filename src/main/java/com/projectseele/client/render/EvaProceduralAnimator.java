package com.projectseele.client.render;

import java.util.HashMap;
import java.util.Map;

import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import software.bernie.geckolib.cache.object.BakedGeoModel;

/**
 * Render-rate inertial layer applied after authored GeckoLib clips.
 *
 * <p>The server remains authoritative for collision and combat. This layer
 * supplies the weight transfer, acceleration lag and turn counter-rotation
 * that cannot be represented by a 20 Hz locomotion enum alone.</p>
 */
public final class EvaProceduralAnimator
{
    private static final Map<Integer, MotionState> STATES = new HashMap<>();

    private EvaProceduralAnimator() {}

    public static void apply(EvaUnit01Entity entity, BakedGeoModel model,
                             float partialTick)
    {
        if (entity.isNervLogisticsLocked() || entity.isCrucified()
                || entity.isPilotProne())
        {
            STATES.remove(entity.getId());
            return;
        }
        if (STATES.size() > 32)
        {
            STATES.clear();
        }
        MotionState state = STATES.computeIfAbsent(entity.getId(),
                ignored -> new MotionState());
        long now = System.nanoTime();
        Vec3 position = new Vec3(
                Mth.lerp((double)partialTick, entity.xOld, entity.getX()),
                Mth.lerp((double)partialTick, entity.yOld, entity.getY()),
                Mth.lerp((double)partialTick, entity.zOld, entity.getZ()));
        float yaw = Mth.rotLerp(partialTick, entity.yRotO,
                entity.getYRot());

        if (!state.initialized)
        {
            state.initialized = true;
            state.lastNanos = now;
            state.lastPosition = position;
            state.lastYaw = yaw;
            return;
        }
        double dt = Mth.clamp((now - state.lastNanos) / 1_000_000_000.0D,
                1.0D / 240.0D, 0.08D);
        if (now == state.lastNanos)
        {
            return;
        }

        double measuredSpeed = position.subtract(state.lastPosition)
                .multiply(1.0D, 0.0D, 1.0D).length() / dt;
        double targetSpeed = Math.min(24.0D,
                Math.max(measuredSpeed,
                        entity.visualHorizontalSpeedForRender()));
        double acceleration = (targetSpeed - state.speed) / dt;
        double yawRate = Mth.wrapDegrees(yaw - state.lastYaw) / dt;
        state.speed = smooth(state.speed, targetSpeed, 10.0D, dt);
        state.acceleration = smooth(state.acceleration,
                Mth.clamp(acceleration, -35.0D, 35.0D), 7.0D, dt);
        state.turnRate = smooth(state.turnRate,
                Mth.clamp(yawRate, -220.0D, 220.0D), 9.0D, dt);
        state.air = smooth(state.air,
                entity.isVisuallyAirborneForRender() ? 1.0D : 0.0D,
                entity.isVisuallyAirborneForRender() ? 13.0D : 18.0D, dt);

        double speed01 = Mth.clamp(state.speed / 11.0D, 0.0D, 1.0D);
        double accelerationLean = Mth.clamp(state.acceleration * 0.065D,
                -2.8D, 2.8D);
        double forwardLean = speed01
                * (entity.isPilotSprinting() ? 7.0D : 3.2D)
                + accelerationLean;
        double turnBank = Mth.clamp(state.turnRate * -0.030D,
                -6.5D, 6.5D) * speed01;
        double vertical = Mth.clamp(
                entity.visualVerticalSpeedForRender() * -0.16D,
                -4.5D, 5.5D) * state.air;

        addRotation(model, "torso_lower",
                forwardLean * 0.62D + vertical * 0.55D,
                turnBank * -0.22D, turnBank * 0.72D);
        addRotation(model, "torso_upper",
                forwardLean * 0.38D + vertical * 0.45D,
                turnBank * 0.34D, turnBank * 0.28D);
        addRotation(model, "head", -vertical * 0.18D,
                turnBank * -0.18D, turnBank * -0.22D);

        state.lastNanos = now;
        state.lastPosition = position;
        state.lastYaw = yaw;
    }

    private static void addRotation(BakedGeoModel model, String name,
                                    double xDegrees, double yDegrees,
                                    double zDegrees)
    {
        model.getBone(name).ifPresent(bone ->
        {
            bone.setRotX(bone.getRotX() + (float)Math.toRadians(xDegrees));
            bone.setRotY(bone.getRotY() + (float)Math.toRadians(yDegrees));
            bone.setRotZ(bone.getRotZ() + (float)Math.toRadians(zDegrees));
        });
    }

    private static double smooth(double current, double target,
                                 double response, double dt)
    {
        double weight = 1.0D - Math.exp(-response * dt);
        return current + (target - current) * weight;
    }

    private static final class MotionState
    {
        private boolean initialized;
        private long lastNanos;
        private Vec3 lastPosition = Vec3.ZERO;
        private float lastYaw;
        private double speed;
        private double acceleration;
        private double turnRate;
        private double air;
    }
}
