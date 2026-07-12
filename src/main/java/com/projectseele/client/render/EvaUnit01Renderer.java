package com.projectseele.client.render;

import java.util.function.Consumer;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/**
 * GeckoLib-driven EVA renderer.
 *
 * GeckoLib is the sole authority for body and arm poses. This renderer only
 * selects visible weapon bones and clips camera-obstructing body cubes from
 * the pilot view; it must never overwrite authored joint rotations.
 */
public class EvaUnit01Renderer extends GeoEntityRenderer<EvaUnit01Entity>
{
    private boolean pilotView;
    private boolean pilotArmPass;
    private double pilotArmSeparation;

    public EvaUnit01Renderer(EntityRendererProvider.Context context)
    {
        super(context, new EvaUnit01GeoModel());
        this.shadowRadius = 3.6F;
        this.withScale(2.5F);
    }

    @Override
    public void render(EvaUnit01Entity entity, float entityYaw, float partialTick, PoseStack poseStack,
                       MultiBufferSource bufferSource, int packedLight)
    {
        Minecraft minecraft = Minecraft.getInstance();
        this.pilotView = minecraft.options.getCameraType().isFirstPerson()
                && minecraft.getCameraEntity() != null
                && minecraft.getCameraEntity().getVehicle() == entity;
        super.render(entity, entityYaw, partialTick, poseStack, bufferSource, packedLight);
    }

    /**
     * Draw the real animated arm subtrees as a camera-space viewmodel. This
     * reuses the exact GeckoLib pose evaluated for the third-person model;
     * the only first-person-specific values are projection scale/placement.
     */
    public void renderPilotArms(EvaUnit01Entity entity, float partialTick, PoseStack poseStack,
                                MultiBufferSource bufferSource, int packedLight)
    {
        float oldWidth = this.scaleWidth;
        float oldHeight = this.scaleHeight;
        boolean oldPilotView = this.pilotView;
        this.pilotArmPass = true;
        this.pilotView = true;
        this.pilotArmSeparation = switch (entity.getWeapon())
        {
            case EvaUnit01Entity.WEAPON_CANNON -> 0.60D;
            case EvaUnit01Entity.WEAPON_KNIFE -> 1.15D;
            default -> 1.55D;
        };
        this.scaleWidth = 0.38F;
        this.scaleHeight = 0.38F;
        poseStack.pushPose();
        poseStack.translate(0.0D, -4.95D, -2.15D);
        try
        {
            super.render(entity, 0.0F, partialTick, poseStack, bufferSource, packedLight);
        }
        finally
        {
            poseStack.popPose();
            this.scaleWidth = oldWidth;
            this.scaleHeight = oldHeight;
            this.pilotView = oldPilotView;
            this.pilotArmPass = false;
        }
    }

    @Override
    public void renderRecursively(PoseStack poseStack, EvaUnit01Entity animatable, GeoBone bone,
                                  RenderType renderType, MultiBufferSource bufferSource,
                                  VertexConsumer buffer, boolean isReRender, float partialTick,
                                  int packedLight, int packedOverlay, float red, float green,
                                  float blue, float alpha)
    {
        if (this.pilotArmPass && isIndividualArmRoot(bone))
        {
            poseStack.pushPose();
            // GeoEntityRenderer turns the model 180 degrees before this
            // recursion, so camera-space left/right is the inverse of the
            // source model's X sign.
            poseStack.translate(isRightArm(bone) ? this.pilotArmSeparation
                    : -this.pilotArmSeparation, 0.0D, 0.0D);
            super.renderRecursively(poseStack, animatable, bone, renderType, bufferSource,
                    buffer, isReRender, partialTick, packedLight, packedOverlay,
                    red, green, blue, alpha);
            poseStack.popPose();
            return;
        }
        super.renderRecursively(poseStack, animatable, bone, renderType, bufferSource,
                buffer, isReRender, partialTick, packedLight, packedOverlay,
                red, green, blue, alpha);
    }

    @Override
    public void preRender(PoseStack poseStack, EvaUnit01Entity animatable, BakedGeoModel model,
                          @Nullable MultiBufferSource bufferSource, @Nullable VertexConsumer buffer,
                          boolean isReRender, float partialTick, int packedLight, int packedOverlay,
                          float red, float green, float blue, float alpha)
    {
        super.preRender(poseStack, animatable, model, bufferSource, buffer, isReRender,
                partialTick, packedLight, packedOverlay, red, green, blue, alpha);
        forEachBone(model, bone ->
        {
            bone.setHidden(this.pilotView && (!this.pilotArmPass || !isArmBone(bone)));
            bone.setChildrenHidden(false);
        });
        // Weapon visibility applies on top in every view.
        setWeaponVisibility(model, "knife", animatable.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE);
        setWeaponVisibility(model, "cannon", animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON);
        setWeaponVisibility(model, "lance", animatable.getWeapon() == EvaUnit01Entity.WEAPON_LANCE);
        boolean activating = animatable.getActivationTicks() > 0;
        setWeaponVisibility(model, "entry_plug", activating);
        setWeaponVisibility(model, "plug_hatch_l", activating);
        setWeaponVisibility(model, "plug_hatch_r", activating);
    }

    private static void setWeaponVisibility(BakedGeoModel model, String name, boolean active)
    {
        model.getBone(name).ifPresent(bone ->
                bone.setHidden(bone.isHidden() || !active));
    }

    private static boolean isArmBone(GeoBone bone)
    {
        for (GeoBone cursor = bone; cursor != null; cursor = cursor.getParent())
        {
            String name = cursor.getName();
            if (name.equals("Arms") || name.equals("arm_l") || name.equals("arm_r")
                    || name.equals("Leftarm") || name.equals("Rightarm"))
            {
                return true;
            }
        }
        return false;
    }

    private static boolean isIndividualArmRoot(GeoBone bone)
    {
        String name = bone.getName();
        return name.equals("arm_l") || name.equals("arm_r")
                || name.equals("Leftarm") || name.equals("Rightarm");
    }

    private static boolean isRightArm(GeoBone bone)
    {
        String name = bone.getName();
        return name.equals("arm_r") || name.equals("Rightarm");
    }

    private static void forEachBone(BakedGeoModel model, Consumer<GeoBone> action)
    {
        for (GeoBone bone : model.topLevelBones())
        {
            walkBone(bone, action);
        }
    }

    private static void walkBone(GeoBone bone, Consumer<GeoBone> action)
    {
        action.accept(bone);
        for (GeoBone child : bone.getChildBones())
        {
            walkBone(child, action);
        }
    }
}
