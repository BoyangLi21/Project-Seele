package com.projectseele.client.render;

import java.util.Set;
import java.util.function.Consumer;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.config.SeeleConfig;
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
 * from its own first-person camera; a second camera-space pass renders the
 * same animated arm bones used by the world model.
 */
public class EvaUnit01Renderer extends GeoEntityRenderer<EvaUnit01Entity>
{
    /** Camera-space limbs only. Their shoulders begin below the viewport. */
    private static final Set<String> PILOT_BONES = Set.of(
            "arm_l", "forearm_l", "hand_l", "arm_r", "forearm_r", "hand_r",
            "knife", "cannon", "shield",
            "brazoizquierda", "brazobajo", "brazoderecho", "brazoderechobajo",
            "Leftarm", "Lowerarm2", "Rightarm", "Lowerarm");

    private boolean pilotView;
    private boolean pilotArmPass;

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

    /** Renders the real, animated arm bones directly in camera space. */
    public void renderPilotArms(EvaUnit01Entity entity, float partialTick, PoseStack poseStack,
                                MultiBufferSource bufferSource, int packedLight)
    {
        this.pilotArmPass = true;
        poseStack.pushPose();
        poseStack.translate(0.0D, SeeleConfig.COCKPIT_ARM_Y.get(), SeeleConfig.COCKPIT_ARM_Z.get());
        float armScale = SeeleConfig.COCKPIT_ARM_SCALE.get().floatValue();
        poseStack.scale(armScale, armScale, armScale);
        try
        {
            super.render(entity, 0.0F, partialTick, poseStack, bufferSource, packedLight);
        }
        finally
        {
            poseStack.popPose();
            this.pilotArmPass = false;
        }
    }

    @Override
    protected void applyRotations(EvaUnit01Entity entity, PoseStack poseStack,
                                  float ageInTicks, float rotationYaw, float partialTick)
    {
        if (this.pilotArmPass)
        {
            // This pass already lives in camera space. No entity/world
            // rotation belongs here: the pilot looks in the same direction
            // as the Eva, not back at a model facing the camera.
            return;
        }
        super.applyRotations(entity, poseStack, ageInTicks, rotationYaw, partialTick);
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
        if (this.pilotArmPass)
        {
            forEachBone(model, bone ->
            {
                bone.setHidden(!PILOT_BONES.contains(bone.getName()));
                bone.setChildrenHidden(false);
            });
        }
        else
        {
            forEachBone(model, bone ->
            {
                bone.setHidden(firstPerson);
                bone.setChildrenHidden(false);
            });
        }
        if ((!firstPerson || this.pilotArmPass) && animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON)
        {
            // The animation establishes a proper two-hand firing stance;
            // this procedural layer follows the pilot's vertical aim.
            float pitch = -Mth.clamp(animatable.getXRot(), -55.0F, 55.0F) * Mth.DEG_TO_RAD;
            aimArm(model, "arm_r", pitch);
            aimArm(model, "arm_l", pitch * 0.82F);
            aimArm(model, "brazoderecho", pitch);
            aimArm(model, "brazoizquierda", pitch * 0.82F);
        }
        else if (this.pilotArmPass && animatable.getWeapon() != EvaUnit01Entity.WEAPON_CANNON)
        {
            // Bare hands / knife: lift the arms off their sides into a raised
            // combat guard so the pilot sees fists in front, not two planks
            // hanging past the bottom of the screen. Additive, so the swing
            // animations still read on top. Right arm (+z tuck) leads.
            poseGuard(model, "arm_r", "forearm_r", -1.02F, -0.62F, 0.30F);
            poseGuard(model, "arm_l", "forearm_l", -0.92F, -0.55F, -0.30F);
            poseGuard(model, "Rightarm", "Lowerarm", -1.02F, -0.62F, 0.30F);
            poseGuard(model, "Leftarm", "Lowerarm2", -0.92F, -0.55F, -0.30F);
            poseGuard(model, "brazoderecho", "brazoderechobajo", -1.02F, -0.62F, 0.30F);
            poseGuard(model, "brazoizquierda", "brazobajo", -0.92F, -0.55F, -0.30F);
        }
        // Weapon visibility applies on top in every view.
        model.getBone("knife").ifPresent(bone ->
                bone.setHidden(bone.isHidden() || animatable.getWeapon() != EvaUnit01Entity.WEAPON_KNIFE));
        model.getBone("cannon").ifPresent(bone ->
                bone.setHidden(bone.isHidden() || animatable.getWeapon() != EvaUnit01Entity.WEAPON_CANNON));
    }

    private static void aimArm(BakedGeoModel model, String name, float pitchRad)
    {
        model.getBone(name).ifPresent(bone -> bone.setRotX(bone.getRotX() + pitchRad));
    }

    /** Raises one arm into a bent-elbow guard: shoulder pitch/yaw + elbow bend. */
    private static void poseGuard(BakedGeoModel model, String arm, String forearm,
                                  float shoulderPitch, float shoulderYaw, float elbowYaw)
    {
        model.getBone(arm).ifPresent(bone ->
        {
            bone.setRotX(bone.getRotX() + shoulderPitch);
            bone.setRotY(bone.getRotY() + shoulderYaw);
        });
        model.getBone(forearm).ifPresent(bone ->
        {
            bone.setRotX(bone.getRotX() - 0.55F);
            bone.setRotY(bone.getRotY() + elbowYaw);
        });
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
