package com.projectseele.client.render;

import java.util.function.Consumer;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.util.Mth;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/**
 * GeckoLib-driven Unit-01. Weapon bones (prog knife, positron cannon) are
 * toggled from the entity's synced weapon state. The world model is hidden
 * from its own first-person camera; a dedicated camera-space rig represents
 * the pilot's body without importing any world-model rotation.
 */
public class EvaUnit01Renderer extends GeoEntityRenderer<EvaUnit01Entity>
{
    private boolean pilotView;
    private final EvaCockpitArmsRenderer cockpitArmsRenderer;

    public EvaUnit01Renderer(EntityRendererProvider.Context context)
    {
        super(context, new EvaUnit01GeoModel());
        this.cockpitArmsRenderer = new EvaCockpitArmsRenderer(context);
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

    /** Renders the action-synchronised arm rig directly in camera space. */
    public void renderPilotArms(EvaUnit01Entity entity, float partialTick, PoseStack poseStack,
                                MultiBufferSource bufferSource, int packedLight)
    {
        this.cockpitArmsRenderer.renderCockpit(entity, partialTick, poseStack, bufferSource, packedLight);
    }

    @Override
    public void preRender(PoseStack poseStack, EvaUnit01Entity animatable, BakedGeoModel model,
                          @Nullable MultiBufferSource bufferSource, @Nullable VertexConsumer buffer,
                          boolean isReRender, float partialTick, int packedLight, int packedOverlay,
                          float red, float green, float blue, float alpha)
    {
        super.preRender(poseStack, animatable, model, bufferSource, buffer, isReRender,
                partialTick, packedLight, packedOverlay, red, green, blue, alpha);
        boolean firstPerson = this.pilotView;
        forEachBone(model, bone ->
        {
            bone.setHidden(firstPerson);
            bone.setChildrenHidden(false);
        });
        if (!firstPerson && animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                && !animatable.isPilotCrouching() && !animatable.isPilotProne())
        {
            // Keep the SmOd skeleton's aim animation intact. Replacing its
            // shoulder rotations with values authored for the fallback model
            // is what kicked the support arm up and out to the left.
            // This layer establishes the cross-body support grip and then
            // follows vertical pilot aim.
            setWorldCannonPose(model);
            float pitch = -Mth.clamp(animatable.getXRot(), -45.0F, 45.0F) * Mth.DEG_TO_RAD * 0.5F;
            aimArm(model, "arm_r", pitch);
            aimArm(model, "arm_l", pitch * 0.82F);
            aimArm(model, "Rightarm", pitch);
            aimArm(model, "Leftarm", pitch * 0.82F);
            aimArm(model, "brazoderecho", pitch);
            aimArm(model, "brazoizquierda", pitch * 0.82F);
        }
        // Weapon visibility applies on top in every view.
        setWeaponVisibility(model, "knife", animatable.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE);
        setWeaponVisibility(model, "cannon", animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON);
    }

    private static void aimArm(BakedGeoModel model, String name, float pitchRad)
    {
        model.getBone(name).ifPresent(bone -> bone.setRotX(bone.getRotX() + pitchRad));
    }

    private static void setWorldCannonPose(BakedGeoModel model)
    {
        setArmPose(model, "arm_r", "forearm_r", -1.62F, -0.08F, -0.04F, -0.10F, 0.0F, 0.0F);
        setArmPose(model, "arm_l", "forearm_l", -1.45F, -1.35F, 0.08F, -0.35F, -0.60F, 0.0F);
        setArmPose(model, "Rightarm", "Lowerarm", -1.62F, -0.08F, -0.04F, -0.10F, 0.0F, 0.0F);
        setArmPose(model, "Leftarm", "Lowerarm2", -1.45F, -1.35F, 0.08F, -0.35F, -0.60F, 0.0F);
        setArmPose(model, "brazoderecho", "brazoderechobajo", -1.62F, -0.08F, -0.04F, -0.10F, 0.0F, 0.0F);
        setArmPose(model, "brazoizquierda", "brazobajo", -1.45F, -1.35F, 0.08F, -0.35F, -0.60F, 0.0F);
    }

    /** Pins one arm to a fixed bent-elbow pose (absolute, kills idle sway). */
    private static void setArmPose(BakedGeoModel model, String arm, String forearm,
                                   float shoulderPitch, float shoulderYaw, float shoulderRoll,
                                   float elbowPitch, float elbowYaw, float elbowRoll)
    {
        model.getBone(arm).ifPresent(bone ->
        {
            bone.setRotX(shoulderPitch);
            bone.setRotY(shoulderYaw);
            bone.setRotZ(shoulderRoll);
        });
        model.getBone(forearm).ifPresent(bone ->
        {
            bone.setRotX(elbowPitch);
            bone.setRotY(elbowYaw);
            bone.setRotZ(elbowRoll);
        });
    }

    private static void setWeaponVisibility(BakedGeoModel model, String name, boolean active)
    {
        model.getBone(name).ifPresent(bone ->
                bone.setHidden(bone.isHidden() || !active));
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
