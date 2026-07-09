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
    private static final int PILOT_SIDE_NONE = 0;
    private static final int PILOT_SIDE_RIGHT = 1;
    private static final int PILOT_SIDE_LEFT = 2;
    private static final double PILOT_ARM_SIDE_X = 2.65D;
    private static final double PILOT_ARM_SIDE_Y = -0.24D;
    private static final double PILOT_ARM_SIDE_Z = -0.42D;

    /** Camera-space right limb plus right-hand weapons. */
    private static final Set<String> PILOT_RIGHT_BONES = Set.of(
            "arm_r", "forearm_r", "hand_r", "knife", "cannon",
            "brazoderecho", "brazoderechobajo",
            "Rightarm", "Lowerarm");

    /** Camera-space left limb and Unit-00 shield. */
    private static final Set<String> PILOT_LEFT_BONES = Set.of(
            "arm_l", "forearm_l", "hand_l", "shield",
            "brazoizquierda", "brazobajo",
            "Leftarm", "Lowerarm2");

    private boolean pilotView;
    private boolean pilotArmPass;
    private int pilotArmSide = PILOT_SIDE_NONE;

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
        try
        {
            renderPilotArmSide(entity, partialTick, poseStack, bufferSource, packedLight,
                    PILOT_SIDE_LEFT, -PILOT_ARM_SIDE_X);
            renderPilotArmSide(entity, partialTick, poseStack, bufferSource, packedLight,
                    PILOT_SIDE_RIGHT, PILOT_ARM_SIDE_X);
        }
        finally
        {
            this.pilotArmSide = PILOT_SIDE_NONE;
            this.pilotArmPass = false;
        }
    }

    private void renderPilotArmSide(EvaUnit01Entity entity, float partialTick, PoseStack poseStack,
                                    MultiBufferSource bufferSource, int packedLight, int side, double x)
    {
        this.pilotArmSide = side;
        poseStack.pushPose();
        poseStack.translate(0.0D, SeeleConfig.COCKPIT_ARM_Y.get(), SeeleConfig.COCKPIT_ARM_Z.get());
        poseStack.translate(x, PILOT_ARM_SIDE_Y, PILOT_ARM_SIDE_Z);
        // Face the rig toward the camera. The raw bones point the model's
        // native front; these dials (live-editable in client config) turn them
        // to forward without a recompile.
        poseStack.mulPose(com.mojang.math.Axis.YP.rotationDegrees(SeeleConfig.COCKPIT_ARM_YAW.get().floatValue()));
        poseStack.mulPose(com.mojang.math.Axis.XP.rotationDegrees(SeeleConfig.COCKPIT_ARM_PITCH.get().floatValue()));
        float armScale = SeeleConfig.COCKPIT_ARM_SCALE.get().floatValue();
        poseStack.scale(armScale, armScale, armScale);
        super.render(entity, 0.0F, partialTick, poseStack, bufferSource, packedLight);
        poseStack.popPose();
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
            Set<String> activeBones = this.pilotArmSide == PILOT_SIDE_RIGHT
                    ? PILOT_RIGHT_BONES : PILOT_LEFT_BONES;
            forEachBone(model, bone ->
            {
                resetPilotBone(bone);
                bone.setHidden(!activeBones.contains(bone.getName()));
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
        if (this.pilotArmPass && animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON)
        {
            // First-person needs a stricter pose than the world animation:
            // the left hand supports the barrel instead of twisting across
            // the camera, and the right-hand weapon remains inside the view.
            setPilotCannonPose(model);
            float pitch = -Mth.clamp(animatable.getXRot(), -45.0F, 45.0F) * Mth.DEG_TO_RAD * 0.35F;
            aimArm(model, "arm_r", pitch);
            aimArm(model, "arm_l", pitch * 0.65F);
            aimArm(model, "Rightarm", pitch);
            aimArm(model, "Leftarm", pitch * 0.65F);
            aimArm(model, "brazoderecho", pitch);
            aimArm(model, "brazoizquierda", pitch * 0.65F);
        }
        else if (!firstPerson && animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON)
        {
            setWorldCannonPose(model);
            // The animation establishes a proper two-hand firing stance;
            // this procedural layer follows the pilot's vertical aim (gentle,
            // so it tracks aim without flinging the arms overhead).
            float pitch = -Mth.clamp(animatable.getXRot(), -45.0F, 45.0F) * Mth.DEG_TO_RAD * 0.5F;
            aimArm(model, "arm_r", pitch);
            aimArm(model, "arm_l", pitch * 0.82F);
            aimArm(model, "Rightarm", pitch);
            aimArm(model, "Leftarm", pitch * 0.82F);
            aimArm(model, "brazoderecho", pitch);
            aimArm(model, "brazoizquierda", pitch * 0.82F);
        }
        else if (this.pilotArmPass && animatable.getWeapon() != EvaUnit01Entity.WEAPON_CANNON)
        {
            // Bare hands / knife: keep a ready guard, but leave a clear gap
            // between the palms. The previous symmetric tuck pulled both
            // hands into the same centerline.
            if (animatable.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE)
            {
                setPilotKnifePose(model);
            }
            else
            {
                setOpenGuardPose(model);
            }
        }
        // Weapon visibility applies on top in every view.
        setWeaponVisibility(model, "knife", animatable.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE,
                this.pilotArmPass);
        setWeaponVisibility(model, "cannon", animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON,
                this.pilotArmPass);
    }

    private static void aimArm(BakedGeoModel model, String name, float pitchRad)
    {
        model.getBone(name).ifPresent(bone -> bone.setRotX(bone.getRotX() + pitchRad));
    }

    private static void resetPilotBone(GeoBone bone)
    {
        bone.setRotX(0.0F);
        bone.setRotY(0.0F);
        bone.setRotZ(0.0F);
        bone.setPosX(0.0F);
        bone.setPosY(0.0F);
        bone.setPosZ(0.0F);
        bone.setScaleX(1.0F);
        bone.setScaleY(1.0F);
        bone.setScaleZ(1.0F);
    }

    private static void setPilotCannonPose(BakedGeoModel model)
    {
        setArmPose(model, "arm_r", "forearm_r", -1.58F, -0.20F, -0.08F, -0.14F, 0.0F, 0.0F);
        setArmPose(model, "arm_l", "forearm_l", -1.48F, 0.42F, 0.20F, -0.22F, -0.02F, -0.02F);
        setArmPose(model, "Rightarm", "Lowerarm", -1.58F, -0.20F, -0.08F, -0.14F, 0.0F, 0.0F);
        setArmPose(model, "Leftarm", "Lowerarm2", -1.48F, 0.42F, 0.20F, -0.22F, -0.02F, -0.02F);
        setArmPose(model, "brazoderecho", "brazoderechobajo", -1.58F, -0.20F, -0.08F, -0.14F, 0.0F, 0.0F);
        setArmPose(model, "brazoizquierda", "brazobajo", -1.48F, 0.42F, 0.20F, -0.22F, -0.02F, -0.02F);
        model.getBone("cannon").ifPresent(bone ->
        {
            bone.setRotX(0.0F);
            bone.setRotY(0.0F);
            bone.setRotZ(0.0F);
        });
    }

    private static void setWorldCannonPose(BakedGeoModel model)
    {
        setArmPose(model, "arm_r", "forearm_r", -1.62F, -0.08F, -0.04F, -0.10F, 0.0F, 0.0F);
        setArmPose(model, "arm_l", "forearm_l", -1.52F, 0.36F, 0.18F, -0.24F, -0.02F, -0.02F);
        setArmPose(model, "Rightarm", "Lowerarm", -1.62F, -0.08F, -0.04F, -0.10F, 0.0F, 0.0F);
        setArmPose(model, "Leftarm", "Lowerarm2", -1.52F, 0.36F, 0.18F, -0.24F, -0.02F, -0.02F);
        setArmPose(model, "brazoderecho", "brazoderechobajo", -1.62F, -0.08F, -0.04F, -0.10F, 0.0F, 0.0F);
        setArmPose(model, "brazoizquierda", "brazobajo", -1.52F, 0.36F, 0.18F, -0.24F, -0.02F, -0.02F);
    }

    private static void setPilotKnifePose(BakedGeoModel model)
    {
        setArmPose(model, "arm_r", "forearm_r", -1.18F, -0.58F, -0.28F, -0.18F, 0.0F, -0.08F);
        setArmPose(model, "arm_l", "forearm_l", -0.86F, 0.62F, 0.42F, -0.28F, 0.0F, 0.10F);
        setArmPose(model, "Rightarm", "Lowerarm", -1.18F, -0.58F, -0.28F, -0.18F, 0.0F, -0.08F);
        setArmPose(model, "Leftarm", "Lowerarm2", -0.86F, 0.62F, 0.42F, -0.28F, 0.0F, 0.10F);
        setArmPose(model, "brazoderecho", "brazoderechobajo", -1.18F, -0.58F, -0.28F, -0.18F, 0.0F, -0.08F);
        setArmPose(model, "brazoizquierda", "brazobajo", -0.86F, 0.62F, 0.42F, -0.28F, 0.0F, 0.10F);
    }

    private static void setOpenGuardPose(BakedGeoModel model)
    {
        setArmPose(model, "arm_r", "forearm_r", -0.96F, -0.56F, -0.38F, -0.32F, 0.0F, -0.10F);
        setArmPose(model, "arm_l", "forearm_l", -0.96F, 0.56F, 0.38F, -0.32F, 0.0F, 0.10F);
        setArmPose(model, "Rightarm", "Lowerarm", -0.96F, -0.56F, -0.38F, -0.32F, 0.0F, -0.10F);
        setArmPose(model, "Leftarm", "Lowerarm2", -0.96F, 0.56F, 0.38F, -0.32F, 0.0F, 0.10F);
        setArmPose(model, "brazoderecho", "brazoderechobajo", -0.96F, -0.56F, -0.38F, -0.32F, 0.0F, -0.10F);
        setArmPose(model, "brazoizquierda", "brazobajo", -0.96F, 0.56F, 0.38F, -0.32F, 0.0F, 0.10F);
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

    private static void setWeaponVisibility(BakedGeoModel model, String name, boolean active, boolean pilotArmPass)
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
