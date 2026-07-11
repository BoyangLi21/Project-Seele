package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * Deterministic two-segment first-person body rig. Every shoulder, elbow and
 * hand is placed in camera space, so world-model pivots and resource-pack UV
 * layouts cannot flip, shorten or merge the pilot's arms.
 */
public final class EvaCockpitArmsRenderer
{
    private static final ResourceLocation WHITE_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/ramiel.png");

    public EvaCockpitArmsRenderer(EntityRendererProvider.Context context)
    {
    }

    public void renderCockpit(EvaUnit01Entity entity, float partialTick, PoseStack poseStack,
                              MultiBufferSource bufferSource, int packedLight)
    {
        VertexConsumer consumer = bufferSource.getBuffer(RenderType.entityTranslucent(WHITE_TEXTURE));
        float[] armor = armorColor(entity.getUnitVariant());
        float[] accent = accentColor(entity.getUnitVariant());
        float time = entity.tickCount + partialTick;
        boolean moving = entity.getDeltaMovement().horizontalDistanceSqr() > 0.001D;
        float stride = moving ? Mth.sin(time * (entity.isPilotSprinting() ? 0.72F : 0.46F)) : 0.0F;
        float breathe = Mth.sin(time * 0.09F) * 0.012F;

        // Both segments keep a fixed length.  Their small, opposite shoulder
        // rotations read as a human arm swing without the telescoping effect
        // produced by translating the hand straight toward the camera.
        Arm left = articulatedArm(-1.0F, stride * 0.12F, breathe);
        Arm right = articulatedArm(1.0F, -stride * 0.12F, breathe);

        int weapon = entity.getWeapon();
        if (entity.isPilotProne())
        {
            left = new Arm(left.shoulder, point(-1.02F, -0.68F, -2.20F), point(-0.70F, -0.50F, -2.78F));
            right = new Arm(right.shoulder, point(1.02F, -0.68F, -2.20F), point(0.70F, -0.50F, -2.78F));
        }
        else if (weapon == EvaUnit01Entity.WEAPON_CANNON)
        {
            // Right hand owns the trigger; the left crosses under the receiver
            // and visibly supports the forward half of the weapon.
            left = new Arm(left.shoulder, point(-0.75F, -0.66F, -2.15F), point(-0.15F, -0.42F, -2.48F));
            right = new Arm(right.shoulder, point(1.02F, -0.66F, -2.08F), point(0.68F, -0.45F, -2.30F));
        }
        else if (weapon == EvaUnit01Entity.WEAPON_KNIFE)
        {
            right = new Arm(right.shoulder, point(1.12F, -0.61F, -2.20F), point(0.90F, -0.31F, -2.55F));
        }

        float swing = entity.getCockpitAttackAnim(partialTick);
        if (swing > 0.0F && weapon != EvaUnit01Entity.WEAPON_CANNON)
        {
            float arc = Mth.sin(Mth.sqrt(swing) * Mth.PI);
            if (entity.isCockpitSwingingLeft())
            {
                left = swingArm(left, -1.0F, arc);
            }
            else
            {
                right = swingArm(right, 1.0F, arc);
            }
        }
        float smash = entity.getCockpitSmashAnim(partialTick);
        if (smash > 0.0F && weapon != EvaUnit01Entity.WEAPON_CANNON)
        {
            left = smashArm(left, -1.0F, smash);
            right = smashArm(right, 1.0F, smash);
        }

        poseStack.pushPose();
        renderArm(poseStack, consumer, left, armor, accent);
        renderArm(poseStack, consumer, right, armor, accent);
        if (weapon == EvaUnit01Entity.WEAPON_KNIFE)
        {
            renderKnife(poseStack, consumer, right.hand);
        }
        else if (weapon == EvaUnit01Entity.WEAPON_CANNON)
        {
            renderCannon(poseStack, consumer, right.hand, left.hand);
        }
        poseStack.popPose();
    }

    /** Exact world-space two-hand rifle rig used while the SmOd arm bones are hidden. */
    public static void renderWorldCannonRig(EvaUnit01Entity entity, PoseStack stack,
                                            MultiBufferSource bufferSource)
    {
        VertexConsumer consumer = bufferSource.getBuffer(RenderType.entityTranslucent(WHITE_TEXTURE));
        float[] armor = armorColor(entity.getUnitVariant());
        float[] accent = accentColor(entity.getUnitVariant());
        float[] receiver = {0.18F, 0.21F, 0.27F, 1.0F};
        float[] barrel = {0.62F, 0.68F, 0.76F, 1.0F};
        Vec3 facing = entity.getForward().multiply(1.0D, 0.0D, 1.0D).normalize();
        Vector3f forward = point((float) facing.x, 0.0F, (float) facing.z);
        Vector3f side = point(-forward.z, 0.0F, forward.x);

        Vector3f rightShoulder = combine(side, -3.7F, forward, 0.0F, 22.0F);
        Vector3f leftShoulder = combine(side, 3.7F, forward, 0.0F, 22.0F);
        Vector3f rightElbow = combine(side, -2.8F, forward, 2.8F, 19.5F);
        Vector3f leftElbow = combine(side, 2.6F, forward, 3.0F, 19.5F);
        Vector3f triggerHand = combine(side, -1.0F, forward, 5.3F, 18.2F);
        Vector3f supportHand = combine(side, 0.35F, forward, 7.2F, 18.4F);
        Vector3f receiverFront = combine(side, -0.25F, forward, 8.0F, 18.5F);
        Vector3f muzzle = combine(side, -0.1F, forward, 23.0F, 18.8F);

        drawSegment(stack, consumer, rightShoulder, rightElbow, 1.15F, armor);
        drawSegment(stack, consumer, rightElbow, triggerHand, 1.0F, accent);
        drawSegment(stack, consumer, leftShoulder, leftElbow, 1.15F, armor);
        drawSegment(stack, consumer, leftElbow, supportHand, 1.0F, accent);
        drawWorldFist(stack, consumer, triggerHand, armor);
        drawWorldFist(stack, consumer, supportHand, armor);
        drawSegment(stack, consumer, triggerHand, receiverFront, 1.45F, receiver);
        drawSegment(stack, consumer, receiverFront, muzzle, 0.68F, barrel);
        drawSegment(stack, consumer, supportHand, receiverFront, 0.45F, receiver);
    }

    private static Vector3f combine(Vector3f side, float sideAmount, Vector3f forward,
                                    float forwardAmount, float y)
    {
        return new Vector3f(side).mul(sideAmount).add(new Vector3f(forward).mul(forwardAmount)).add(0.0F, y, 0.0F);
    }

    private static void drawWorldFist(PoseStack stack, VertexConsumer consumer,
                                      Vector3f hand, float[] color)
    {
        stack.pushPose();
        stack.translate(hand.x, hand.y, hand.z);
        drawBox(stack, consumer, -1.15F, -0.85F, -1.0F, 1.15F, 0.85F, 1.0F, color);
        stack.popPose();
    }

    private static Arm swingArm(Arm arm, float side, float arc)
    {
        Vector3f elbow = new Vector3f(arm.elbow).add(-side * 0.28F * arc, 0.20F * arc, -0.24F * arc);
        Vector3f hand = new Vector3f(arm.hand).add(-side * 0.64F * arc, 0.43F * arc, -0.58F * arc);
        return new Arm(arm.shoulder, elbow, hand);
    }

    private static Arm articulatedArm(float side, float swing, float breathe)
    {
        Vector3f shoulder = point(side * 1.52F, -1.02F + breathe, -1.40F);
        Vector3f elbow = new Vector3f(shoulder).add(segmentVector(side, -0.28F, 0.84F,
                -0.18F + swing * 0.55F));
        Vector3f hand = new Vector3f(elbow).add(segmentVector(side, -0.12F, 0.80F,
                -0.20F + swing * 0.38F));
        return new Arm(shoulder, elbow, hand);
    }

    private static Arm smashArm(Arm arm, float side, float progress)
    {
        float lift = Mth.sin(progress * Mth.PI);
        float drive = Mth.clamp((progress - 0.48F) / 0.52F, 0.0F, 1.0F);
        Vector3f elbow = new Vector3f(arm.elbow)
                .add(-side * 0.12F * lift, 0.25F * lift - 0.26F * drive, -0.12F * lift);
        Vector3f hand = new Vector3f(arm.hand)
                .add(-side * 0.28F * lift, 0.52F * lift - 0.62F * drive, -0.38F * lift);
        return new Arm(arm.shoulder, elbow, hand);
    }

    private static Vector3f segmentVector(float side, float inward, float length, float pitch)
    {
        float x = -side * inward;
        float yzLength = Mth.sqrt(length * length - inward * inward);
        return point(x, Mth.sin(pitch) * yzLength, -Mth.cos(pitch) * yzLength);
    }

    private static void renderArm(PoseStack stack, VertexConsumer consumer, Arm arm,
                                  float[] armor, float[] accent)
    {
        drawSegment(stack, consumer, arm.shoulder, arm.elbow, 0.085F, armor);
        drawSegment(stack, consumer, arm.elbow, arm.hand, 0.095F, accent);
        drawFist(stack, consumer, arm.hand, armor);
    }

    private static void drawFist(PoseStack stack, VertexConsumer consumer, Vector3f hand, float[] color)
    {
        stack.pushPose();
        stack.translate(hand.x, hand.y, hand.z);
        drawBox(stack, consumer, -0.135F, -0.11F, -0.13F, 0.135F, 0.11F, 0.13F, color);
        for (int i = 0; i < 4; i++)
        {
            float x = -0.12F + i * 0.08F;
            drawBox(stack, consumer, x - 0.03F, 0.075F, -0.15F,
                    x + 0.03F, 0.145F, -0.07F, color);
        }
        stack.popPose();
    }

    private static void renderKnife(PoseStack stack, VertexConsumer consumer, Vector3f hand)
    {
        float[] dark = {0.12F, 0.14F, 0.18F, 1.0F};
        float[] steel = {0.82F, 0.87F, 0.92F, 1.0F};
        Vector3f gripEnd = new Vector3f(hand).add(-0.05F, 0.25F, -0.08F);
        Vector3f bladeMid = new Vector3f(hand).add(-0.28F, 0.84F, -0.30F);
        Vector3f tip = new Vector3f(hand).add(-0.42F, 1.28F, -0.46F);
        drawSegment(stack, consumer, hand, gripEnd, 0.075F, dark);
        drawSegment(stack, consumer, gripEnd, bladeMid, 0.095F, steel);
        drawSegment(stack, consumer, bladeMid, tip, 0.052F, steel);
        stack.pushPose();
        stack.translate(gripEnd.x, gripEnd.y, gripEnd.z);
        drawBox(stack, consumer, -0.21F, -0.035F, -0.07F, 0.21F, 0.035F, 0.07F, dark);
        stack.popPose();
    }

    private static void renderCannon(PoseStack stack, VertexConsumer consumer,
                                     Vector3f triggerHand, Vector3f supportHand)
    {
        float[] receiver = {0.20F, 0.23F, 0.30F, 1.0F};
        float[] steel = {0.68F, 0.74F, 0.82F, 1.0F};
        float[] hot = {1.0F, 0.55F, 0.16F, 1.0F};
        Vector3f receiverFront = new Vector3f(0.10F, -0.18F, -2.90F);
        Vector3f barrelEnd = new Vector3f(0.0F, 0.02F, -3.78F);
        drawSegment(stack, consumer, triggerHand, receiverFront, 0.11F, receiver);
        drawSegment(stack, consumer, receiverFront, barrelEnd, 0.055F, steel);
        drawSegment(stack, consumer, supportHand, receiverFront, 0.045F, receiver);
        stack.pushPose();
        stack.translate(receiverFront.x, receiverFront.y + 0.18F, receiverFront.z + 0.02F);
        drawBox(stack, consumer, -0.075F, -0.035F, -0.15F, 0.075F, 0.05F, 0.15F, receiver);
        stack.popPose();
        stack.pushPose();
        stack.translate(barrelEnd.x, barrelEnd.y, barrelEnd.z);
        drawBox(stack, consumer, -0.08F, -0.08F, -0.05F, 0.08F, 0.08F, 0.05F, hot);
        stack.popPose();
    }

    private static void drawSegment(PoseStack stack, VertexConsumer consumer,
                                    Vector3f from, Vector3f to, float radius, float[] color)
    {
        Vector3f delta = new Vector3f(to).sub(from);
        float length = delta.length();
        if (length < 1.0E-4F)
        {
            return;
        }
        Vector3f midpoint = new Vector3f(from).add(to).mul(0.5F);
        Quaternionf rotation = new Quaternionf().rotationTo(new Vector3f(0.0F, 1.0F, 0.0F), delta.normalize());
        stack.pushPose();
        stack.translate(midpoint.x, midpoint.y, midpoint.z);
        stack.mulPose(rotation);
        drawBox(stack, consumer, -radius, -length * 0.5F, -radius,
                radius, length * 0.5F, radius, color);
        stack.popPose();
    }

    private static void drawBox(PoseStack stack, VertexConsumer consumer,
                                float x0, float y0, float z0, float x1, float y1, float z1, float[] c)
    {
        Matrix4f pose = stack.last().pose();
        Matrix3f normal = stack.last().normal();
        quad(pose, normal, consumer, x0, y0, z1, x1, y0, z1, x1, y1, z1, x0, y1, z1, 0, 0, 1, c);
        quad(pose, normal, consumer, x1, y0, z0, x0, y0, z0, x0, y1, z0, x1, y1, z0, 0, 0, -1, c);
        quad(pose, normal, consumer, x1, y0, z1, x1, y0, z0, x1, y1, z0, x1, y1, z1, 1, 0, 0, c);
        quad(pose, normal, consumer, x0, y0, z0, x0, y0, z1, x0, y1, z1, x0, y1, z0, -1, 0, 0, c);
        quad(pose, normal, consumer, x0, y1, z1, x1, y1, z1, x1, y1, z0, x0, y1, z0, 0, 1, 0, c);
        quad(pose, normal, consumer, x0, y0, z0, x1, y0, z0, x1, y0, z1, x0, y0, z1, 0, -1, 0, c);
    }

    private static void quad(Matrix4f pose, Matrix3f normal, VertexConsumer consumer,
                             float ax, float ay, float az, float bx, float by, float bz,
                             float cx, float cy, float cz, float dx, float dy, float dz,
                             float nx, float ny, float nz, float[] color)
    {
        vertex(pose, normal, consumer, ax, ay, az, 0, 1, nx, ny, nz, color);
        vertex(pose, normal, consumer, bx, by, bz, 1, 1, nx, ny, nz, color);
        vertex(pose, normal, consumer, cx, cy, cz, 1, 0, nx, ny, nz, color);
        vertex(pose, normal, consumer, dx, dy, dz, 0, 0, nx, ny, nz, color);
    }

    private static void vertex(Matrix4f pose, Matrix3f normal, VertexConsumer consumer,
                               float x, float y, float z, float u, float v,
                               float nx, float ny, float nz, float[] color)
    {
        consumer.vertex(pose, x, y, z)
                .color(color[0], color[1], color[2], color[3])
                .uv(u, v)
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(LightTexture.FULL_BRIGHT)
                .normal(normal, nx, ny, nz)
                .endVertex();
    }

    private static Vector3f point(float x, float y, float z)
    {
        return new Vector3f(x, y, z);
    }

    private static float[] armorColor(int variant)
    {
        return switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> new float[] {0.93F, 0.55F, 0.12F, 1.0F};
            case EvaUnit01Entity.UNIT_02 -> new float[] {0.78F, 0.08F, 0.10F, 1.0F};
            default -> new float[] {0.43F, 0.17F, 0.70F, 1.0F};
        };
    }

    private static float[] accentColor(int variant)
    {
        return switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> new float[] {0.92F, 0.92F, 0.88F, 1.0F};
            case EvaUnit01Entity.UNIT_02 -> new float[] {0.16F, 0.16F, 0.18F, 1.0F};
            default -> new float[] {0.22F, 0.72F, 0.18F, 1.0F};
        };
    }

    private record Arm(Vector3f shoulder, Vector3f elbow, Vector3f hand)
    {
    }
}
