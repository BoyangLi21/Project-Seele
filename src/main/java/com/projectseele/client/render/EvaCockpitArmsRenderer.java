package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * Dedicated first-person cockpit rig, built like an FPS viewmodel: two thick
 * segmented arms (upper stub, forearm, wrist ring, fist with knuckles) posed
 * in camera space, lit by world light with per-face shading so they read as
 * armored volume instead of glowing noodles. Weapon models (prog knife,
 * positron rifle) hang off the same hand anchors.
 */
public final class EvaCockpitArmsRenderer
{
    private static final ResourceLocation WHITE_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/ramiel.png");

    // Segment cross-sections (blocks). The old rig used 0.085 — noodles.
    private static final float UPPER_R = 0.190F;
    private static final float FOREARM_R = 0.155F;
    private static final float WRIST_R = 0.175F;

    public EvaCockpitArmsRenderer(net.minecraft.client.renderer.entity.EntityRendererProvider.Context context)
    {
    }

    public void renderCockpit(EvaUnit01Entity entity, float partialTick, PoseStack poseStack,
                              MultiBufferSource bufferSource, int packedLight)
    {
        VertexConsumer consumer = bufferSource.getBuffer(RenderType.entityCutoutNoCull(WHITE_TEXTURE));
        float[] armor = armorColor(entity.getUnitVariant());
        float[] accent = accentColor(entity.getUnitVariant());
        float[] joint = {0.10F, 0.10F, 0.12F, 1.0F};

        float time = entity.tickCount + partialTick;
        boolean moving = entity.getDeltaMovement().horizontalDistanceSqr() > 0.001D;
        float stride = moving ? Mth.sin(time * (entity.isPilotSprinting() ? 0.72F : 0.46F)) * 0.05F : 0.0F;
        float breathe = Mth.sin(time * 0.09F) * 0.015F;

        int weapon = entity.getWeapon();
        Arm right;
        Arm left;
        if (entity.isPilotProne())
        {
            // Braced on the forearms, elbows at the lower screen corners.
            right = new Arm(v(1.30F, -1.15F, -0.70F), v(0.85F, -0.78F, -1.35F), v(0.34F, -0.62F, -1.90F));
            left = new Arm(v(-1.30F, -1.15F, -0.70F), v(-0.85F, -0.78F, -1.35F), v(-0.34F, -0.62F, -1.90F));
        }
        else if (weapon == EvaUnit01Entity.WEAPON_CANNON)
        {
            // Shouldered rifle: right hand on the grip near the chest, left
            // arm extended to the forestock.
            right = new Arm(v(1.30F, -1.25F, -0.45F), v(0.78F, -0.70F, -0.95F), v(0.42F, -0.48F, -1.35F));
            left = new Arm(v(-1.35F, -1.30F, -0.55F), v(-0.62F, -0.72F, -1.55F), v(-0.10F, -0.50F, -2.35F));
        }
        else
        {
            // Boxer's guard, right fist a little forward.
            right = new Arm(v(1.35F, -1.30F + breathe, -0.55F),
                    v(0.85F, -0.70F + breathe, -1.20F),
                    v(0.52F, -0.40F + breathe + stride, -1.85F));
            left = new Arm(v(-1.35F, -1.30F - breathe, -0.55F),
                    v(-0.85F, -0.68F - breathe, -1.30F),
                    v(-0.50F, -0.36F - breathe - stride, -1.95F));
        }

        // ----- strike animation offsets -----
        float swing = entity.getCockpitAttackAnim(partialTick);
        if (swing > 0.0F && weapon != EvaUnit01Entity.WEAPON_CANNON && !entity.isPilotProne())
        {
            float arc = Mth.sin(Mth.sqrt(swing) * Mth.PI);
            if (entity.isCockpitSwingingLeft())
            {
                left = punch(left, arc);
            }
            else
            {
                right = punch(right, arc);
            }
        }
        float smash = entity.getCockpitSmashAnim(partialTick);
        if (smash > 0.0F && weapon != EvaUnit01Entity.WEAPON_CANNON && !entity.isPilotProne())
        {
            right = smashArm(right, 1.0F, smash);
            left = smashArm(left, -1.0F, smash);
        }

        poseStack.pushPose();
        renderArm(poseStack, consumer, right, armor, accent, joint, packedLight);
        renderArm(poseStack, consumer, left, armor, accent, joint, packedLight);
        if (weapon == EvaUnit01Entity.WEAPON_KNIFE && !entity.isPilotProne())
        {
            renderKnife(poseStack, consumer, right.hand, packedLight);
        }
        else if (weapon == EvaUnit01Entity.WEAPON_CANNON)
        {
            renderRifle(poseStack, consumer, entity, right.hand, left.hand, packedLight);
        }
        poseStack.popPose();
    }

    // ----- poses -----

    /** Straight jab toward the reticle with elbow follow-through. */
    private static Arm punch(Arm arm, float arc)
    {
        Vector3f target = v(arm.hand.x * 0.12F, -0.16F, -2.95F);
        Vector3f hand = new Vector3f(arm.hand).lerp(target, arc);
        Vector3f elbow = new Vector3f(arm.elbow).lerp(
                v(arm.elbow.x * 0.45F, -0.45F, -1.9F), arc * 0.8F);
        return new Arm(arm.shoulder, elbow, hand);
    }

    private static Arm smashArm(Arm arm, float side, float progress)
    {
        float lift = Mth.sin(Mth.clamp(progress / 0.48F, 0.0F, 1.0F) * Mth.HALF_PI);
        float drive = Mth.clamp((progress - 0.48F) / 0.52F, 0.0F, 1.0F);
        Vector3f hand = new Vector3f(arm.hand)
                .add(-side * 0.18F * lift, 0.62F * lift - 1.05F * drive, 0.12F * lift - 0.55F * drive);
        Vector3f elbow = new Vector3f(arm.elbow)
                .add(-side * 0.10F * lift, 0.30F * lift - 0.45F * drive, 0.05F * lift - 0.25F * drive);
        return new Arm(arm.shoulder, elbow, hand);
    }

    // ----- rendering -----

    private static void renderArm(PoseStack stack, VertexConsumer consumer, Arm arm,
                                  float[] armor, float[] accent, float[] joint, int light)
    {
        // Upper stub reaching in from off-screen.
        drawSegment(stack, consumer, arm.shoulder, arm.elbow, UPPER_R, armor, light);
        // Elbow joint ball.
        drawCube(stack, consumer, arm.elbow, WRIST_R, joint, light);
        // Forearm with an accent stripe segment near the wrist.
        Vector3f wrist = new Vector3f(arm.elbow).lerp(arm.hand, 0.82F);
        drawSegment(stack, consumer, arm.elbow, wrist, FOREARM_R, armor, light);
        drawSegment(stack, consumer, wrist, arm.hand, WRIST_R, accent, light);
        drawFist(stack, consumer, arm, armor, joint, light);
    }

    /** Armored fist: palm block plus four knuckle plates facing the reticle. */
    private static void drawFist(PoseStack stack, VertexConsumer consumer, Arm arm,
                                 float[] armor, float[] joint, int light)
    {
        Vector3f aim = new Vector3f(arm.hand).sub(arm.elbow).normalize();
        Quaternionf rot = new Quaternionf().rotationTo(new Vector3f(0, 0, -1), aim);
        stack.pushPose();
        stack.translate(arm.hand.x, arm.hand.y, arm.hand.z);
        stack.mulPose(rot);
        drawBox(stack, consumer, -0.20F, -0.17F, -0.16F, 0.20F, 0.17F, 0.16F, armor, light);
        for (int i = 0; i < 4; i++)
        {
            float x = -0.155F + i * 0.103F;
            drawBox(stack, consumer, x - 0.042F, -0.06F, -0.235F, x + 0.042F, 0.10F, -0.14F, joint, light);
        }
        stack.popPose();
    }

    private static void renderKnife(PoseStack stack, VertexConsumer consumer, Vector3f hand, int light)
    {
        float[] grip = {0.10F, 0.11F, 0.14F, 1.0F};
        float[] steel = {0.80F, 0.85F, 0.91F, 1.0F};
        float[] edge = {0.95F, 0.98F, 1.0F, 1.0F};
        // Blade runs forward-up out of the fist toward the reticle.
        Vector3f dir = new Vector3f(-0.16F, 0.34F, -0.93F).normalize();
        Vector3f gripEnd = new Vector3f(hand).add(new Vector3f(dir).mul(0.30F));
        Vector3f bladeBase = new Vector3f(hand).add(new Vector3f(dir).mul(0.38F));
        Vector3f tip = new Vector3f(hand).add(new Vector3f(dir).mul(1.55F));
        drawSegment(stack, consumer, hand, gripEnd, 0.075F, grip, light);
        drawSegment(stack, consumer, bladeBase, tip, 0.085F, steel, light);
        Vector3f edgeBase = new Vector3f(bladeBase).add(0.0F, 0.045F, 0.0F);
        Vector3f edgeTip = new Vector3f(tip).add(0.0F, 0.035F, 0.0F);
        drawSegment(stack, consumer, edgeBase, edgeTip, 0.028F, edge, light);
    }

    /** Shouldered positron rifle spanning the view toward the crosshair. */
    private static void renderRifle(PoseStack stack, VertexConsumer consumer, EvaUnit01Entity entity,
                                    Vector3f gripHand, Vector3f stockHand, int light)
    {
        float[] receiver = {0.16F, 0.18F, 0.24F, 1.0F};
        float[] shroud = {0.30F, 0.33F, 0.40F, 1.0F};
        float[] barrel = {0.58F, 0.63F, 0.72F, 1.0F};
        float charge = entity.chargeProgress();

        // The bore line: from just right of centre, converging on the reticle.
        Vector3f rear = v(0.46F, -0.36F, -0.85F);
        Vector3f front = v(0.02F, -0.10F, -4.30F);
        Vector3f boreDir = new Vector3f(front).sub(rear).normalize();

        Vector3f receiverEnd = new Vector3f(rear).add(new Vector3f(boreDir).mul(1.15F));
        Vector3f shroudEnd = new Vector3f(rear).add(new Vector3f(boreDir).mul(2.35F));
        // Stock reaching back into the pilot's shoulder (off-screen right).
        Vector3f stockEnd = new Vector3f(rear).sub(new Vector3f(boreDir).mul(0.75F)).add(0.18F, -0.10F, 0.0F);

        drawSegment(stack, consumer, stockEnd, rear, 0.13F, shroud, light);
        drawSegment(stack, consumer, rear, receiverEnd, 0.165F, receiver, light);
        drawSegment(stack, consumer, receiverEnd, shroudEnd, 0.115F, shroud, light);
        drawSegment(stack, consumer, shroudEnd, front, 0.075F, barrel, light);
        // Scope block above the receiver.
        Vector3f scope = new Vector3f(rear).add(new Vector3f(boreDir).mul(0.55F)).add(0.0F, 0.17F, 0.0F);
        drawCube(stack, consumer, scope, 0.085F, receiver, light);
        // Charge glow at the muzzle.
        if (charge > 0.01F)
        {
            float[] hot = {1.0F, 0.45F + 0.5F * charge, 0.15F, 1.0F};
            drawCube(stack, consumer, front, 0.05F + 0.06F * charge, hot, light);
        }
    }

    // ----- primitives -----

    private static void drawCube(PoseStack stack, VertexConsumer consumer, Vector3f at, float r,
                                 float[] color, int light)
    {
        stack.pushPose();
        stack.translate(at.x, at.y, at.z);
        drawBox(stack, consumer, -r, -r, -r, r, r, r, color, light);
        stack.popPose();
    }

    private static void drawSegment(PoseStack stack, VertexConsumer consumer,
                                    Vector3f from, Vector3f to, float radius, float[] color, int light)
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
                radius, length * 0.5F, radius, color, light);
        stack.popPose();
    }

    /** Box with per-face shading so volume reads even in flat cockpit light. */
    private static void drawBox(PoseStack stack, VertexConsumer consumer,
                                float x0, float y0, float z0, float x1, float y1, float z1,
                                float[] c, int light)
    {
        Matrix4f pose = stack.last().pose();
        Matrix3f normal = stack.last().normal();
        quad(pose, normal, consumer, light, 0.86F, x0, y0, z1, x1, y0, z1, x1, y1, z1, x0, y1, z1, 0, 0, 1, c);
        quad(pose, normal, consumer, light, 0.86F, x1, y0, z0, x0, y0, z0, x0, y1, z0, x1, y1, z0, 0, 0, -1, c);
        quad(pose, normal, consumer, light, 0.72F, x1, y0, z1, x1, y0, z0, x1, y1, z0, x1, y1, z1, 1, 0, 0, c);
        quad(pose, normal, consumer, light, 0.72F, x0, y0, z0, x0, y0, z1, x0, y1, z1, x0, y1, z0, -1, 0, 0, c);
        quad(pose, normal, consumer, light, 1.00F, x0, y1, z1, x1, y1, z1, x1, y1, z0, x0, y1, z0, 0, 1, 0, c);
        quad(pose, normal, consumer, light, 0.52F, x0, y0, z0, x1, y0, z0, x1, y0, z1, x0, y0, z1, 0, -1, 0, c);
    }

    private static void quad(Matrix4f pose, Matrix3f normal, VertexConsumer consumer, int light, float shade,
                             float ax, float ay, float az, float bx, float by, float bz,
                             float cx, float cy, float cz, float dx, float dy, float dz,
                             float nx, float ny, float nz, float[] color)
    {
        vertex(pose, normal, consumer, light, ax, ay, az, 0, 1, nx, ny, nz, color, shade);
        vertex(pose, normal, consumer, light, bx, by, bz, 1, 1, nx, ny, nz, color, shade);
        vertex(pose, normal, consumer, light, cx, cy, cz, 1, 0, nx, ny, nz, color, shade);
        vertex(pose, normal, consumer, light, dx, dy, dz, 0, 0, nx, ny, nz, color, shade);
    }

    private static void vertex(Matrix4f pose, Matrix3f normal, VertexConsumer consumer, int light,
                               float x, float y, float z, float u, float v,
                               float nx, float ny, float nz, float[] color, float shade)
    {
        consumer.vertex(pose, x, y, z)
                .color(color[0] * shade, color[1] * shade, color[2] * shade, color[3])
                .uv(u, v)
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(light)
                .normal(normal, nx, ny, nz)
                .endVertex();
    }

    private static Vector3f v(float x, float y, float z)
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
