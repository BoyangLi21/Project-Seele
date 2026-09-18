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
            "fuyutsuki", hair("receding", .68F, .70F, .68F));
    private static final ModelPart CROSS = cross();
    private static final ModelPart FU_COAT = fuyutsukiCoat(false);
    private static final ModelPart FU_COLLAR = fuyutsukiCoat(true);
    private static final ModelPart FU_BROWS = fuyutsukiBrows();

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
        if (style.equals("receding"))
        {
            // A high forehead with swept-back grey temples, not a full fringe.
            box(mesh,"rear_crown",-4.08F,-8.18F,-.5F,8.16F,.8F,4.5F,0);
            box(mesh,"nape",-4.12F,-7.6F,3.48F,8.24F,5.2F,.7F,0);
            for (int side : new int[] {-1,1})
            {
                box(mesh,"temple"+side,side<0?-4.3F:3.7F,-7.2F,-2.5F,.6F,4.5F,6.3F,0);
                box(mesh,"sideburn"+side,side<0?-4.22F:3.72F,-3.5F,-2.5F,.5F,1.7F,1.4F,0);
                box(mesh,"swept_ridge"+side,side<0?-3.9F:2.2F,-8.05F,-2.1F,1.7F,.7F,4.2F,side*.09F);
            }
            return new Hair(LayerDefinition.create(mesh,32,32).bakeRoot(),r,g,b);
        }
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

    private static ModelPart fuyutsukiCoat(boolean trim)
    {
        var mesh=new MeshDefinition();
        if(trim)
        {
            box(mesh,"high_collar_left",-2.7F,-.6F,-2.2F,1.7F,2.2F,.3F,-.08F);
            box(mesh,"high_collar_right",1,-.6F,-2.2F,1.7F,2.2F,.3F,.08F);
            box(mesh,"front_placket",-.17F,2,-2.21F,.34F,9.5F,.15F,0);
        }
        else
        {
            box(mesh,"shoulder_yoke",-4.15F,.15F,-2.12F,8.3F,1.1F,4.24F,0);
            box(mesh,"coat_left",-4.12F,9.5F,-2.14F,3.9F,3.8F,4.28F,-.012F);
            box(mesh,"coat_right",.22F,9.5F,-2.14F,3.9F,3.8F,4.28F,.012F);
        }
        return LayerDefinition.create(mesh,32,32).bakeRoot();
    }
    private static ModelPart fuyutsukiBrows()
    {
        var mesh=new MeshDefinition();
        box(mesh,"brow_left",-2.85F,-5.05F,-4.12F,1.65F,.24F,.22F,-.06F);
        box(mesh,"brow_right",1.15F,-5.05F,-4.12F,1.65F,.24F,.22F,.06F);
        return LayerDefinition.create(mesh,16,16).bakeRoot();
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
        if(entity.skin().equals("fuyutsuki"))FU_BROWS.render(poses,vertices,light,OverlayTexture.NO_OVERLAY,.51F,.53F,.50F,1);
        poses.popPose();
        if(entity.skin().equals("fuyutsuki"))
        {
            poses.pushPose();getParentModel().body.translateAndRotate(poses);
            FU_COAT.render(poses,vertices,light,OverlayTexture.NO_OVERLAY,.33F,.37F,.29F,1);
            FU_COLLAR.render(poses,vertices,light,OverlayTexture.NO_OVERLAY,.23F,.16F,.13F,1);poses.popPose();
        }
        if (entity.skin().equals("misato"))
        {
            poses.pushPose();getParentModel().body.translateAndRotate(poses);
            CROSS.render(poses, vertices, light, OverlayTexture.NO_OVERLAY, .90F, .76F, .38F, 1);
            poses.popPose();
        }
    }
}
