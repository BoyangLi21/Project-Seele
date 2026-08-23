package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.client.CommanderPoseClient;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeDeformation;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.LivingEntityRenderer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;

/** Two-piece elbows for the seated Commander Ikari thinking pose. */
public final class GendoPoseArmLayer extends RenderLayer<AbstractClientPlayer,
        PlayerModel<AbstractClientPlayer>>
{
    private static final float SOURCE_LENGTH = 8.0F;
    private static final FirstPersonRig FIRST_PERSON_STANDARD =
            new FirstPersonRig(false);
    private static final FirstPersonRig FIRST_PERSON_SLIM =
            new FirstPersonRig(true);

    private final ModelPart rightArm;
    private final ModelPart leftArm;
    private final ModelPart rightSleeve;
    private final ModelPart leftSleeve;

    public GendoPoseArmLayer(
            RenderLayerParent<AbstractClientPlayer,
                    PlayerModel<AbstractClientPlayer>> parent,
            boolean slim)
    {
        super(parent);
        float width = slim ? 3.0F : 4.0F;
        this.rightArm = segment(40, 16, width, 0.0F);
        this.leftArm = segment(32, 48, width, 0.0F);
        this.rightSleeve = segment(40, 32, width, 0.25F);
        this.leftSleeve = segment(48, 48, width, 0.25F);
    }

    @Override
    public void render(PoseStack poses, MultiBufferSource buffers,
            int packedLight, AbstractClientPlayer player,
            float limbSwing, float limbSwingAmount, float partialTick,
            float ageInTicks, float netHeadYaw, float headPitch)
    {
        if (!CommanderPoseClient.isActive(player))
        {
            return;
        }
        VertexConsumer skin = buffers.getBuffer(RenderType.entityTranslucent(
                player.getSkinTextureLocation()));
        int overlay = LivingEntityRenderer.getOverlayCoords(player, 0.0F);

        Vec3 rightShoulder = new Vec3(-5.0D, 2.0D, 0.0D);
        Vec3 leftShoulder = new Vec3(5.0D, 2.0D, 0.0D);
        // The table is in front of the chair: move both elbows forward and
        // down onto its edge, then fold the forearms back up to the mouth.
        // The approved command chair sits at z=314.5 and the nearest desk
        // slab begins at z=315 with its top at y=-328.  Converting that world
        // offset into the 16-pixel humanoid rig puts the elbow centres here:
        // 0.75 block forward and 1.15 blocks above the seated entity origin.
        // With the complete player translated 0.25 block forward and leaned
        // 20 degrees, these inverse-transformed points place the elbows just
        // below the shoulders on the y=-328 desk top.  The forearms then fold
        // upward to the mouth instead of making the elbow rise above the arm.
        Vec3 rightElbow = new Vec3(-4.60D, 3.80D, -3.80D);
        Vec3 leftElbow = new Vec3(4.60D, 3.80D, -3.80D);
        Vec3 rightHand = new Vec3(-0.20D, -1.50D, -5.00D);
        Vec3 leftHand = new Vec3(0.20D, -1.50D, -5.00D);

        renderLimb(poses, skin, packedLight, overlay, this.rightArm,
                this.rightSleeve, rightShoulder, rightElbow);
        renderLimb(poses, skin, packedLight, overlay, this.rightArm,
                this.rightSleeve, rightElbow, rightHand);
        renderLimb(poses, skin, packedLight, overlay, this.leftArm,
                this.leftSleeve, leftShoulder, leftElbow);
        renderLimb(poses, skin, packedLight, overlay, this.leftArm,
                this.leftSleeve, leftElbow, leftHand);
    }

    /** Draws both bent arms once in camera space; RenderHandEvent fires twice. */
    public static void renderFirstPerson(PoseStack poses,
            MultiBufferSource buffers, int packedLight,
            AbstractClientPlayer player)
    {
        FirstPersonRig rig = "slim".equals(player.getModelName())
                ? FIRST_PERSON_SLIM : FIRST_PERSON_STANDARD;
        VertexConsumer skin = buffers.getBuffer(RenderType.entityTranslucent(
                player.getSkinTextureLocation()));

        Vec3 rightShoulder = new Vec3(0.52D, -0.34D, -0.48D);
        Vec3 leftShoulder = new Vec3(-0.52D, -0.34D, -0.48D);
        Vec3 rightElbow = new Vec3(0.40D, -0.58D, -0.72D);
        Vec3 leftElbow = new Vec3(-0.40D, -0.58D, -0.72D);
        Vec3 rightHand = new Vec3(0.08D, -0.18D, -0.62D);
        Vec3 leftHand = new Vec3(-0.08D, -0.18D, -0.62D);

        renderCameraLimb(poses, skin, packedLight, rig.rightArm(),
                rig.rightSleeve(), rightShoulder, rightElbow);
        renderCameraLimb(poses, skin, packedLight, rig.rightArm(),
                rig.rightSleeve(), rightElbow, rightHand);
        renderCameraLimb(poses, skin, packedLight, rig.leftArm(),
                rig.leftSleeve(), leftShoulder, leftElbow);
        renderCameraLimb(poses, skin, packedLight, rig.leftArm(),
                rig.leftSleeve(), leftElbow, leftHand);
    }

    private static void renderCameraLimb(PoseStack poses,
            VertexConsumer buffer, int light, ModelPart skin,
            ModelPart sleeve, Vec3 start, Vec3 end)
    {
        Vec3 delta = end.subtract(start);
        float length = (float)delta.length();
        if (length < 1.0E-4F)
        {
            return;
        }
        Quaternionf rotation = rotationFromDownAxis(delta.scale(1.0D / length));
        poses.pushPose();
        poses.translate(start.x, start.y, start.z);
        poses.mulPose(rotation);
        poses.scale(1.0F, length / (SOURCE_LENGTH / 16.0F), 1.0F);
        skin.render(poses, buffer, light, OverlayTexture.NO_OVERLAY);
        sleeve.render(poses, buffer, light, OverlayTexture.NO_OVERLAY);
        poses.popPose();
    }

    private static void renderLimb(PoseStack poses, VertexConsumer buffer,
            int light, int overlay, ModelPart skin, ModelPart sleeve,
            Vec3 start, Vec3 end)
    {
        Vec3 delta = end.subtract(start);
        float length = (float)delta.length();
        if (length < 1.0E-4F)
        {
            return;
        }
        Vec3 direction = delta.scale(1.0D / length);
        Quaternionf rotation = rotationFromDownAxis(direction);

        poses.pushPose();
        poses.translate(start.x / 16.0D, start.y / 16.0D,
                start.z / 16.0D);
        poses.mulPose(rotation);
        poses.scale(1.0F, length / SOURCE_LENGTH, 1.0F);
        skin.render(poses, buffer, light, overlay);
        sleeve.render(poses, buffer, light, overlay);
        poses.popPose();
    }

    private static Quaternionf rotationFromDownAxis(Vec3 direction)
    {
        float dot = (float)Math.max(-1.0D,
                Math.min(1.0D, direction.y));
        float angle = (float)Math.acos(dot);
        float axisX = (float)direction.z;
        float axisZ = (float)-direction.x;
        float axisLength = (float)Math.sqrt(axisX * axisX + axisZ * axisZ);
        if (axisLength < 1.0E-5F)
        {
            return dot < 0.0F
                    ? new Quaternionf().rotationX((float)Math.PI)
                    : new Quaternionf();
        }
        return new Quaternionf().fromAxisAngleRad(
                axisX / axisLength, 0.0F, axisZ / axisLength, angle);
    }

    private static ModelPart segment(int u, int v, float width,
                                     float deformation)
    {
        MeshDefinition mesh = new MeshDefinition();
        PartDefinition root = mesh.getRoot();
        root.addOrReplaceChild("segment",
                CubeListBuilder.create().texOffs(u, v).addBox(
                        -width * 0.5F, 0.0F, -2.0F,
                        width, SOURCE_LENGTH, 4.0F,
                        new CubeDeformation(deformation)),
                PartPose.ZERO);
        return LayerDefinition.create(mesh, 64, 64).bakeRoot()
                .getChild("segment");
    }

    private record FirstPersonRig(ModelPart rightArm, ModelPart leftArm,
                                  ModelPart rightSleeve,
                                  ModelPart leftSleeve)
    {
        private FirstPersonRig(boolean slim)
        {
            this(segment(40, 16, slim ? 3.0F : 4.0F, 0.0F),
                    segment(32, 48, slim ? 3.0F : 4.0F, 0.0F),
                    segment(40, 32, slim ? 3.0F : 4.0F, 0.25F),
                    segment(48, 48, slim ? 3.0F : 4.0F, 0.25F));
        }
    }
}
