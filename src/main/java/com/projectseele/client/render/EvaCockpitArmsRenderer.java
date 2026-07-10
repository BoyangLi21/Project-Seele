package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.util.Mth;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/**
 * Independent first-person rig. World shoulder transforms never enter this
 * renderer, so the two hands remain attached to the pilot's body sides while
 * still reacting to the same movement, stance, weapon and swing state.
 */
public class EvaCockpitArmsRenderer extends GeoEntityRenderer<EvaUnit01Entity>
{
    public EvaCockpitArmsRenderer(EntityRendererProvider.Context context)
    {
        super(context, new EvaCockpitArmsGeoModel());
        this.shadowRadius = 0.0F;
    }

    public void renderCockpit(EvaUnit01Entity entity, float partialTick, PoseStack poseStack,
                              MultiBufferSource bufferSource, int packedLight)
    {
        poseStack.pushPose();
        poseStack.translate(0.0D, -0.82D, -1.68D);
        poseStack.scale(0.40F, 0.40F, 0.40F);
        // The pilot is looking through an internally lit entry-plug display.
        // Keeping the rig full-bright also prevents the knife/cannon from
        // turning into black silhouettes at night.
        super.render(entity, 0.0F, partialTick, poseStack, bufferSource, LightTexture.FULL_BRIGHT);
        poseStack.popPose();
    }

    @Override
    protected void applyRotations(EvaUnit01Entity entity, PoseStack poseStack,
                                  float ageInTicks, float rotationYaw, float partialTick)
    {
        // The RenderHandEvent pose stack is already camera-space.
    }

    @Override
    public void preRender(PoseStack poseStack, EvaUnit01Entity entity, BakedGeoModel model,
                          @Nullable MultiBufferSource bufferSource, @Nullable VertexConsumer buffer,
                          boolean isReRender, float partialTick, int packedLight, int packedOverlay,
                          float red, float green, float blue, float alpha)
    {
        super.preRender(poseStack, entity, model, bufferSource, buffer, isReRender,
                partialTick, packedLight, packedOverlay, red, green, blue, alpha);

        GeoBone left = model.getBone("cockpit_left_arm").orElse(null);
        GeoBone right = model.getBone("cockpit_right_arm").orElse(null);
        if (left == null || right == null)
        {
            return;
        }

        reset(left);
        reset(right);
        left.setPosX(20.0F);
        right.setPosX(-20.0F);

        float time = entity.tickCount + partialTick;
        boolean moving = entity.getDeltaMovement().horizontalDistanceSqr() > 0.001D;
        float stride = moving ? Mth.sin(time * (entity.isPilotSprinting() ? 0.72F : 0.46F)) : 0.0F;
        float bob = moving ? Mth.abs(Mth.cos(time * 0.46F)) * 0.35F : Mth.sin(time * 0.08F) * 0.08F;

        // Rotate past ninety degrees so the shoulder enters from the lower
        // corner and the hand reaches forward/up into view. A sub-90-degree
        // pitch makes the hand retreat below the hotbar and leaves only a
        // pair of floating forearm blocks visible.
        float leftPitch = -2.35F + stride * 0.12F;
        float rightPitch = -2.35F - stride * 0.12F;
        // Almost no roll at rest: the arms should continue down the body
        // sides instead of converging into a floating X in the screen centre.
        float leftRoll = -0.035F;
        float rightRoll = 0.035F;

        int weapon = entity.getWeapon();
        if (entity.isPilotProne())
        {
            leftPitch = -1.82F + stride * 0.10F;
            rightPitch = -1.82F - stride * 0.10F;
            leftRoll = -0.10F;
            rightRoll = 0.10F;
            left.setPosY(-0.8F + bob);
            right.setPosY(-0.8F + bob);
        }
        else if (weapon == EvaUnit01Entity.WEAPON_CANNON)
        {
            leftPitch = -1.92F;
            rightPitch = -1.98F;
            leftRoll = -0.08F;
            rightRoll = 0.05F;
            left.setPosX(-5.5F);
            left.setPosY(0.9F);
            right.setPosX(-10.0F);
            right.setPosY(0.25F);
        }
        else if (weapon == EvaUnit01Entity.WEAPON_KNIFE)
        {
            rightPitch = -2.30F;
            rightRoll = -0.10F;
            leftPitch = -2.28F;
        }

        float swing = entity.getCockpitAttackAnim(partialTick);
        if (swing > 0.0F && weapon != EvaUnit01Entity.WEAPON_CANNON)
        {
            float arc = Mth.sin(Mth.sqrt(swing) * Mth.PI);
            if (entity.isCockpitSwingingLeft())
            {
                leftPitch -= arc * 0.72F;
                leftRoll += arc * 0.68F;
            }
            else
            {
                rightPitch -= arc * 0.72F;
                rightRoll -= arc * 0.68F;
            }
        }

        left.setRotX(leftPitch);
        left.setRotY(-0.06F);
        left.setRotZ(leftRoll);
        left.setPosY(left.getPosY() + bob);
        right.setRotX(rightPitch);
        right.setRotY(0.06F);
        right.setRotZ(rightRoll);
        right.setPosY(right.getPosY() + bob);

        model.getBone("cockpit_knife").ifPresent(bone ->
        {
            bone.setHidden(weapon != EvaUnit01Entity.WEAPON_KNIFE);
            // The hand itself points into depth; counter-rotate the knife so
            // its tapered silhouette rises from the fist instead of showing
            // only the guard as a tiny sideways arrow.
            bone.setRotX(-0.80F);
            bone.setRotY(0.0F);
            bone.setRotZ(-1.05F);
            bone.setScaleX(0.75F);
            bone.setScaleY(0.75F);
            bone.setScaleZ(0.75F);
        });
        model.getBone("cockpit_cannon").ifPresent(bone ->
        {
            bone.setHidden(weapon != EvaUnit01Entity.WEAPON_CANNON);
            // Aim the barrel away from the near plane and up toward the
            // crosshair. The previous equivalent angle pointed it toward the
            // camera, collapsing the cannon into a vertical black stack.
            bone.setRotX(-2.10F);
            bone.setRotY(-0.10F);
            bone.setRotZ(-0.45F);
            bone.setScaleX(0.46F);
            bone.setScaleY(0.46F);
            bone.setScaleZ(0.46F);
        });
    }

    private static void reset(GeoBone bone)
    {
        bone.setRotX(0.0F);
        bone.setRotY(0.0F);
        bone.setRotZ(0.0F);
        bone.setPosX(0.0F);
        bone.setPosY(0.0F);
        bone.setPosZ(0.0F);
        bone.setHidden(false);
    }
}
