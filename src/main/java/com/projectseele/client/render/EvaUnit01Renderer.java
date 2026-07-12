package com.projectseele.client.render;

import java.util.Set;
import java.util.function.Consumer;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.util.Mth;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/**
 * GeckoLib-driven EVA renderer.
 *
 * Stances come from each model family's animation set. A final shared arm
 * constraint runs after GeckoLib evaluation for live pilot aim and guard.
 * First person renders those exact same arm/weapon bones while clipping the
 * head, torso and legs that would otherwise occlude the camera.
 */
public class EvaUnit01Renderer extends GeoEntityRenderer<EvaUnit01Entity>
{
    /** Bone subtrees hidden from the pilot camera (their own head). */
    private static final Set<String> HEAD_BONES = Set.of("head", "Head", "Neck", "horn");
    /**
     * Bones whose OWN cubes hide in first person (children keep rendering,
     * so the arms survive): the chest plate and shoulder pylons sit right at
     * eye height and otherwise wall off the pilot's forward view.
     */
    private static final Set<String> TORSO_COVER_BONES = Set.of(
            "torso_upper", "pylon_l", "pylon_r",
            "Upperbody", "Armor2");
    private static final Set<String> LOWER_COVER_BONES = Set.of(
            "pelvis", "torso_lower", "Lowerbody", "Armor");
    private static final Set<String> LEG_ROOT_BONES = Set.of(
            "leg_l", "leg_r", "Leftleg", "Rightleg");

    private boolean pilotView;

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
            bone.setHidden(false);
            bone.setChildrenHidden(false);
        });
        if (firstPerson)
        {
            // Hide the pilot's own head and the chest/shoulder armor at eye
            // level; only the shared animated arms and weapons remain.
            forEachBone(model, bone ->
            {
                if (HEAD_BONES.contains(bone.getName()))
                {
                    hideSubtree(bone);
                }
                else if (TORSO_COVER_BONES.contains(bone.getName())
                        || LOWER_COVER_BONES.contains(bone.getName()))
                {
                    bone.setHidden(true);
                }
                else if (LEG_ROOT_BONES.contains(bone.getName()))
                {
                    hideSubtree(bone);
                }
            });
        }
        // Weapon visibility applies on top in every view.
        setWeaponVisibility(model, "knife", animatable.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE);
        setWeaponVisibility(model, "cannon", animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON);
        setWeaponVisibility(model, "lance", animatable.getWeapon() == EvaUnit01Entity.WEAPON_LANCE);
        boolean activating = animatable.getActivationTicks() > 0;
        setWeaponVisibility(model, "entry_plug", activating);
        setWeaponVisibility(model, "plug_hatch_l", activating);
        setWeaponVisibility(model, "plug_hatch_r", activating);
    }

    /** Apply the final shared pose only after GeckoLib has evaluated animations. */
    @Override
    public void renderRecursively(PoseStack poseStack, EvaUnit01Entity entity, GeoBone bone,
                                  RenderType renderType, MultiBufferSource bufferSource,
                                  VertexConsumer buffer, boolean isReRender, float partialTick,
                                  int packedLight, int packedOverlay, float red, float green,
                                  float blue, float alpha)
    {
        applySharedArmPose(entity, bone, partialTick);
        super.renderRecursively(poseStack, entity, bone, renderType, bufferSource, buffer,
                isReRender, partialTick, packedLight, packedOverlay, red, green, blue, alpha);
    }

    /** Authoritative joint pose shared by first- and third-person rendering. */
    private static void applySharedArmPose(EvaUnit01Entity entity, GeoBone bone, float partialTick)
    {
        if (entity.isPilotProne() || entity.isPilotCrouching() || entity.isCrucified()
                || entity.getActivationTicks() > 0)
        {
            return;
        }
        String name = bone.getName();
        if (entity.getWeapon() == EvaUnit01Entity.WEAPON_CANNON)
        {
            float pitch = -Mth.clamp(entity.getXRot(), -42.0F, 42.0F) * Mth.DEG_TO_RAD * 0.55F;
            switch (name)
            {
                case "torso_upper", "Upperbody" ->
                {
                    bone.setRotY(0.0F);
                    bone.setRotZ(0.0F);
                }
                // SmOd's authored punch reaches the forward contact plane at
                // about -100 degrees. Values around -50/-70 remain behind
                // the eye/shoulder plane even though they look plausible on
                // paper, which caused both the backwards third-person arms
                // and the empty pilot view.
                case "arm_r", "Rightarm" -> setRotation(bone, -1.72F + pitch, -0.08F, -0.05F);
                case "forearm_r", "Lowerarm" -> setRotation(bone, -0.12F, 0.0F, 0.0F);
                case "arm_l", "Leftarm" -> setRotation(bone, -1.62F + pitch * 0.82F, 0.08F, -0.18F);
                case "forearm_l", "Lowerarm2" -> setRotation(bone, -0.18F, 0.10F, 0.0F);
                default -> { }
            }
            return;
        }
        if (entity.getCockpitAttackAnim(partialTick) > 0.0F
                || entity.getCockpitSmashAnim(partialTick) > 0.0F)
        {
            return;
        }
        if (entity.getWeapon() == EvaUnit01Entity.WEAPON_LANCE)
        {
            // Longinus is held low in both hands. Pilot and external views
            // share these exact joints; there is no detached cockpit prop.
            switch (name)
            {
                case "arm_r", "Rightarm" -> setRotation(bone, -1.68F, -0.08F, -0.06F);
                case "forearm_r", "Lowerarm" -> setRotation(bone, -0.18F, 0.0F, 0.0F);
                case "arm_l", "Leftarm" -> setRotation(bone, -1.54F, 0.16F, -0.16F);
                case "forearm_l", "Lowerarm2" -> setRotation(bone, -0.24F, 0.12F, 0.0F);
                default -> { }
            }
            return;
        }
        boolean moving = entity.getDeltaMovement().horizontalDistanceSqr() > 0.001D;
        float phase = moving ? Mth.sin((entity.tickCount + partialTick) * 0.42F) * 0.12F : 0.0F;
        // A forward ready-guard keeps the real shoulder-to-hand chain within
        // the EVA's eye line. It reads naturally in third person and means
        // first person does not need a second pair of floating arms.
        float rightBase = entity.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE ? -1.75F : -1.67F;
        switch (name)
        {
            case "arm_r", "Rightarm" -> setRotation(bone, rightBase + phase, -0.05F, -0.07F);
            case "forearm_r", "Lowerarm" -> setRotation(bone,
                    entity.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE ? -0.18F : -0.10F, 0.0F, 0.0F);
            case "arm_l", "Leftarm" -> setRotation(bone, -1.67F - phase, 0.05F, 0.07F);
            case "forearm_l", "Lowerarm2" -> setRotation(bone, -0.10F, 0.0F, 0.0F);
            default -> { }
        }
    }

    private static void setRotation(GeoBone bone, float x, float y, float z)
    {
        bone.setRotX(x);
        bone.setRotY(y);
        bone.setRotZ(z);
    }

    private static void setWeaponVisibility(BakedGeoModel model, String name, boolean active)
    {
        model.getBone(name).ifPresent(bone ->
                bone.setHidden(bone.isHidden() || !active));
    }

    private static void hideSubtree(GeoBone bone)
    {
        bone.setHidden(true);
        for (GeoBone child : bone.getChildBones())
        {
            hideSubtree(child);
        }
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
