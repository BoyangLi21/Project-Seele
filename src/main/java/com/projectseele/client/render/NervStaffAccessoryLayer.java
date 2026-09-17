package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.projectseele.entity.NervStaffEntity;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import java.util.Map;

/** Lightweight physical hair and accessories, attached to the animated head/body. */
public final class NervStaffAccessoryLayer extends RenderLayer<NervStaffEntity, PlayerModel<NervStaffEntity>>
{
    private static final ResourceLocation WHITE = new ResourceLocation("minecraft", "textures/block/white_concrete.png");
    private record Hair(ModelPart mesh, float red, float green, float blue) {}
    private static final Map<String, Hair> HAIR = Map.of(
            "misato", hair("long", .22F, .13F, .34F),
            "ritsuko", hair("bob", .80F, .65F, .24F),
            "maya", hair("short", .24F, .14F, .08F),
            "fuyutsuki", hair("swept", .72F, .74F, .73F));
    private static final ModelPart CROSS = cross();

    public NervStaffAccessoryLayer(RenderLayerParent<NervStaffEntity, PlayerModel<NervStaffEntity>> renderer)
    {
        super(renderer);
    }

    private static void box(MeshDefinition mesh, String name, float x, float y, float z,
                            float w, float h, float d, float tilt)
    {
        mesh.getRoot().addOrReplaceChild(name, CubeListBuilder.create().texOffs(0, 0)
                .addBox(x, y, z, w, h, d), PartPose.rotation(0, 0, tilt));
    }

    private static Hair hair(String style, float r, float g, float b)
    {
        MeshDefinition mesh = new MeshDefinition();
        box(mesh, "crown", -4.2F, -8.3F, -3.7F, 8.4F, 1.2F, 7.7F, 0);
        box(mesh, "back", -4.25F, -7.5F, 3.5F, 8.5F, 5.8F, .9F, 0);
        if (style.equals("long"))
        {
            for (int side : new int[] {-1, 1})
            {
                box(mesh, "temple" + side, side < 0 ? -4.6F : 3.8F, -7.4F, -2.8F, .8F, 7.8F, 6.5F, side * .025F);
                box(mesh, "long_lock" + side, side < 0 ? -4.4F : 2.6F, -2.0F, 3.6F, 1.8F, 7.5F, 1.2F, side * .06F);
            }
            box(mesh, "back_length", -3.5F, -2, 3.7F, 7, 6, 1.1F, 0);
            box(mesh, "fringe_left", -4, -7.7F, -4.3F, 3.3F, 1.5F, .65F, -.08F);
            box(mesh, "fringe_right", .8F, -7.7F, -4.3F, 3.2F, 1.8F, .65F, .07F);
        }
        else if (style.equals("bob"))
        {
            box(mesh, "side_left", -4.6F, -7.4F, -2.8F, 1.0F, 7.2F, 6.9F, -.025F);
            box(mesh, "side_right", 3.6F, -7.4F, -2.8F, 1.0F, 6.6F, 6.9F, .025F);
            box(mesh, "bob_nape", -4.1F, -2.2F, 3.2F, 8.2F, 2.6F, 1.2F, 0);
            box(mesh, "side_part", -4.1F, -7.6F, -4.25F, 5.0F, 1.7F, .65F, -.10F);
            box(mesh, "part_tip", -3.9F, -6.8F, -4.2F, 1.1F, 2.1F, .7F, -.04F);
        }
        else
        {
            box(mesh, "temple_left", -4.4F, -7.3F, -.8F, .8F, 4.1F, 4.9F, 0);
            box(mesh, "temple_right", 3.6F, -7.3F, -.8F, .8F, 4.1F, 4.9F, 0);
            box(mesh, "swept_fringe", -3.8F, -8.1F, -4.15F, 7.4F, style.equals("swept") ? .8F : 1.5F, .65F, -.045F);
        }
        return new Hair(LayerDefinition.create(mesh, 32, 32).bakeRoot(), r, g, b);
    }

    private static ModelPart cross()
    {
        MeshDefinition mesh = new MeshDefinition();
        box(mesh, "chain", -.12F, .4F, -2.2F, .24F, 2.2F, .2F, 0);
        box(mesh, "vertical", -.19F, 2.3F, -2.35F, .38F, 1.9F, .3F, 0);
        box(mesh, "horizontal", -.72F, 2.75F, -2.35F, 1.44F, .38F, .3F, 0);
        return LayerDefinition.create(mesh, 16, 16).bakeRoot();
    }

    @Override
    public void render(PoseStack poses, MultiBufferSource buffers, int light, NervStaffEntity entity,
                       float swing, float amount, float partial, float age, float yaw, float pitch)
    {
        Hair hair = HAIR.get(entity.skin());
        if (hair == null || entity.isInvisible()) return;
        var vertices = buffers.getBuffer(RenderType.entityCutoutNoCull(WHITE));
        poses.pushPose();
        getParentModel().head.translateAndRotate(poses);
        hair.mesh().render(poses, vertices, light, OverlayTexture.NO_OVERLAY, hair.red(), hair.green(), hair.blue(), 1);
        poses.popPose();
        if (entity.skin().equals("misato"))
        {
            poses.pushPose();getParentModel().body.translateAndRotate(poses);
            CROSS.render(poses, vertices, light, OverlayTexture.NO_OVERLAY, .90F, .76F, .38F, 1);
            poses.popPose();
        }
    }
}
