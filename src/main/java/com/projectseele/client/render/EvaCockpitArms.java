package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.model.geom.ModelLayerLocation;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;

/** Camera-space EVA arms. Unlike the world model, these cannot be culled by first-person rendering. */
public final class EvaCockpitArms
{
    public static final ModelLayerLocation LAYER = new ModelLayerLocation(
            new ResourceLocation(ProjectSeele.MODID, "eva_cockpit_arms"), "main");
    private static final ResourceLocation TEXTURE = new ResourceLocation(
            ProjectSeele.MODID, "textures/entity/eva_cockpit_arms.png");

    public static final int ACTION_NONE = 0;
    public static final int ACTION_RIGHT = 1;
    public static final int ACTION_LEFT = 2;
    public static final int ACTION_SMASH = 3;
    public static final int ACTION_FIRE = 4;
    public static final int ACTION_STOMP = 5;

    private final ModelPart root;
    private final ModelPart armLeft;
    private final ModelPart forearmLeft;
    private final ModelPart armRight;
    private final ModelPart forearmRight;
    private final ModelPart knife;
    private final ModelPart cannon;

    public EvaCockpitArms(ModelPart root)
    {
        this.root = root;
        this.armLeft = root.getChild("arm_left");
        this.forearmLeft = this.armLeft.getChild("forearm_left");
        this.armRight = root.getChild("arm_right");
        this.forearmRight = this.armRight.getChild("forearm_right");
        this.knife = this.forearmRight.getChild("hand_right").getChild("knife");
        this.cannon = root.getChild("cannon");
    }

    public static LayerDefinition createLayer()
    {
        MeshDefinition mesh = new MeshDefinition();
        PartDefinition root = mesh.getRoot();

        PartDefinition left = root.addOrReplaceChild("arm_left",
                CubeListBuilder.create().texOffs(152, 44)
                        .addBox(-3.5F, -2.0F, -3.5F, 7.0F, 18.0F, 7.0F),
                PartPose.offset(7.0F, 4.0F, 5.0F));
        PartDefinition leftForearm = left.addOrReplaceChild("forearm_left",
                CubeListBuilder.create().texOffs(216, 44)
                        .addBox(-3.2F, -1.0F, -3.2F, 6.4F, 19.0F, 6.4F),
                PartPose.offset(0.0F, 15.0F, 0.0F));
        leftForearm.addOrReplaceChild("hand_left",
                CubeListBuilder.create().texOffs(32, 100)
                        .addBox(-4.0F, -1.0F, -4.0F, 8.0F, 9.0F, 8.0F),
                PartPose.offset(0.0F, 17.0F, 0.0F));

        PartDefinition right = root.addOrReplaceChild("arm_right",
                CubeListBuilder.create().texOffs(184, 44)
                        .addBox(-3.5F, -2.0F, -3.5F, 7.0F, 18.0F, 7.0F),
                PartPose.offset(-7.0F, 4.0F, 5.0F));
        PartDefinition rightForearm = right.addOrReplaceChild("forearm_right",
                CubeListBuilder.create().texOffs(0, 100)
                        .addBox(-3.2F, -1.0F, -3.2F, 6.4F, 19.0F, 6.4F),
                PartPose.offset(0.0F, 15.0F, 0.0F));
        PartDefinition rightHand = rightForearm.addOrReplaceChild("hand_right",
                CubeListBuilder.create().texOffs(70, 100)
                        .addBox(-4.0F, -1.0F, -4.0F, 8.0F, 9.0F, 8.0F),
                PartPose.offset(0.0F, 17.0F, 0.0F));
        rightHand.addOrReplaceChild("knife",
                CubeListBuilder.create().texOffs(190, 140)
                        .addBox(-1.7F, 4.0F, -1.7F, 3.4F, 25.0F, 3.4F),
                PartPose.ZERO);

        root.addOrReplaceChild("cannon",
                CubeListBuilder.create()
                        .texOffs(120, 158).addBox(-4.5F, -3.5F, -29.0F, 9.0F, 8.0F, 27.0F)
                        .texOffs(176, 158).addBox(-2.5F, -1.8F, -48.0F, 5.0F, 5.0F, 20.0F)
                        .texOffs(214, 178).addBox(-4.0F, 2.5F, -8.0F, 8.0F, 5.0F, 13.0F)
                        .texOffs(208, 140).addBox(-1.7F, -7.0F, -19.0F, 3.4F, 4.0F, 12.0F)
                        .texOffs(226, 140).addBox(-3.0F, -2.5F, -53.0F, 6.0F, 6.0F, 5.0F),
                PartPose.offset(-1.0F, 16.0F, -5.0F));

        return LayerDefinition.create(mesh, 256, 256);
    }

    public void render(PoseStack poseStack, MultiBufferSource buffers, int packedLight,
                       EvaUnit01Entity eva, float partialTick, int action, int actionTicks)
    {
        this.root.getAllParts().forEach(ModelPart::resetPose);
        this.knife.visible = eva.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE;
        this.cannon.visible = eva.getWeapon() == EvaUnit01Entity.WEAPON_CANNON;

        float time = eva.tickCount + partialTick;
        float breathe = Mth.sin(time * 0.08F) * 0.018F;
        float actionProgress = actionTicks > 0 ? Mth.sin((12 - Math.min(12, actionTicks)) / 12.0F * Mth.PI) : 0.0F;

        if (eva.getWeapon() == EvaUnit01Entity.WEAPON_CANNON)
        {
            // Right hand grips the trigger group; left hand reaches further
            // forward under the barrel instead of mirroring the right arm.
            this.armRight.xRot = -1.38F + breathe;
            this.armRight.yRot = -0.10F;
            this.armRight.zRot = -0.12F;
            this.forearmRight.xRot = -0.30F;
            this.armLeft.xRot = -1.18F - breathe;
            this.armLeft.yRot = -0.42F;
            this.armLeft.zRot = 0.34F;
            this.forearmLeft.xRot = -0.62F;
            this.forearmLeft.yRot = -0.18F;
            if (action == ACTION_FIRE)
            {
                float recoil = actionProgress * 0.22F;
                this.armRight.xRot += recoil;
                this.armLeft.xRot += recoil * 0.8F;
                this.cannon.z += actionProgress * 3.0F;
            }
        }
        else
        {
            this.armRight.xRot = -1.05F + breathe;
            this.armRight.yRot = -0.12F;
            this.armRight.zRot = -0.16F;
            this.armLeft.xRot = -1.05F - breathe;
            this.armLeft.yRot = 0.12F;
            this.armLeft.zRot = 0.16F;
            if (action == ACTION_RIGHT)
            {
                this.armRight.xRot -= actionProgress * 0.72F;
                this.armRight.yRot += actionProgress * 0.28F;
            }
            else if (action == ACTION_LEFT)
            {
                this.armLeft.xRot -= actionProgress * 0.72F;
                this.armLeft.yRot -= actionProgress * 0.28F;
            }
            else if (action == ACTION_SMASH || action == ACTION_STOMP)
            {
                this.armRight.xRot -= actionProgress * 0.34F;
                this.armLeft.xRot -= actionProgress * 0.34F;
            }
        }

        poseStack.pushPose();
        poseStack.translate(0.0D, eva.isPilotProne() ? 0.86D : eva.isPilotCrouching() ? 0.72D : 0.58D, -0.45D);
        poseStack.mulPose(Axis.XP.rotationDegrees(-7.0F));
        poseStack.scale(0.52F, 0.52F, 0.52F);
        VertexConsumer consumer = buffers.getBuffer(RenderType.entityCutoutNoCull(TEXTURE));
        this.root.render(poseStack, consumer, packedLight, OverlayTexture.NO_OVERLAY,
                1.0F, 1.0F, 1.0F, 1.0F);
        poseStack.popPose();
    }
}
