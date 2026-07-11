package com.projectseele.client.render;

import java.util.Set;
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
 * GeckoLib-driven EVA renderer.
 *
 * Pose policy (plan A): every stance — stand, walk, kneel, prone, aim,
 * strikes — comes from the animation json of the active model, and each
 * model family ships its own animation set tuned to its own skeleton. The
 * only procedural layer left is the additive vertical aim-follow while the
 * cannon is out, because pilot view pitch is live input, not a stance.
 *
 * First person is the Unit's own body: the world model keeps rendering with
 * only the head bones hidden (the camera sits inside them), so the arms,
 * weapons and stances the pilot sees are EXACTLY the third-person ones —
 * same bones, same animations, same texture.
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
            "Upperbody", "Armor2", "Armor3", "Armor4");

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
            // level; arms, legs and weapons remain — the body IS the view.
            forEachBone(model, bone ->
            {
                if (HEAD_BONES.contains(bone.getName()))
                {
                    hideSubtree(bone);
                }
                else if (TORSO_COVER_BONES.contains(bone.getName()))
                {
                    bone.setHidden(true);
                }
            });
            if (animatable.getWeapon() != EvaUnit01Entity.WEAPON_CANNON
                    && !animatable.isPilotProne() && !animatable.isCrucified())
            {
                // Idle arms hang at the sides, below the pilot camera; raise
                // them into frame (additive, so swings still read on top).
                raiseArm(model, "arm_r", "forearm_r");
                raiseArm(model, "arm_l", "forearm_l");
                raiseArm(model, "Rightarm", "Lowerarm");
                raiseArm(model, "Leftarm", "Lowerarm2");
            }
        }
        if (!firstPerson && animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON)
        {
            // Additive vertical aim-follow on top of the aim animation.
            float pitch = -Mth.clamp(animatable.getXRot(), -45.0F, 45.0F) * Mth.DEG_TO_RAD * 0.55F;
            aimArm(model, "arm_r", pitch);
            aimArm(model, "arm_l", pitch * 0.82F);
            aimArm(model, "Rightarm", pitch);
            aimArm(model, "Leftarm", pitch * 0.82F);
        }
        // Weapon visibility applies on top in every view.
        setWeaponVisibility(model, "knife", animatable.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE);
        setWeaponVisibility(model, "cannon", animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON);
    }

    private static void aimArm(BakedGeoModel model, String name, float pitchRad)
    {
        model.getBone(name).ifPresent(bone -> bone.setRotX(bone.getRotX() + pitchRad));
    }

    /** First-person guard: shoulder up ~66°, elbow bent, added over the anim. */
    private static void raiseArm(BakedGeoModel model, String arm, String forearm)
    {
        model.getBone(arm).ifPresent(bone -> bone.setRotX(bone.getRotX() - 1.15F));
        model.getBone(forearm).ifPresent(bone -> bone.setRotX(bone.getRotX() - 0.30F));
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
