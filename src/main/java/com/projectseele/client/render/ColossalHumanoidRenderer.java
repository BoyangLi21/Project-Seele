package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.MassProductionEvaEntity;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/** Original direct-geometry renderer for Sachiel and SEELE's white production units. */
public class ColossalHumanoidRenderer<T extends LivingEntity> extends EntityRenderer<T>
{
    public enum Style { SACHIEL, SHAMSHEL, ZERUEL, MASS_PRODUCTION }

    private static final ResourceLocation TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/ramiel.png");
    private final Style style;

    public ColossalHumanoidRenderer(EntityRendererProvider.Context context, Style style)
    {
        super(context);
        this.style = style;
        this.shadowRadius = style == Style.SACHIEL ? 3.8F : 4.5F;
    }

    @Override
    public void render(T entity, float yaw, float partialTick, PoseStack stack,
                       MultiBufferSource buffers, int packedLight)
    {
        stack.pushPose();
        stack.mulPose(com.mojang.math.Axis.YP.rotationDegrees(180.0F - yaw));
        VertexConsumer consumer = buffers.getBuffer(RenderType.entityTranslucent(TEXTURE));
        float walk = entity.getDeltaMovement().horizontalDistanceSqr() > 0.002D
                ? Mth.sin((entity.tickCount + partialTick) * 0.34F) : 0.0F;
        if (this.style == Style.SACHIEL)
        {
            renderSachiel(stack, consumer, walk);
        }
        else if (this.style == Style.SHAMSHEL)
        {
            renderShamshel(stack, consumer, entity.tickCount + partialTick);
        }
        else if (this.style == Style.ZERUEL)
        {
            renderZeruel(stack, consumer, entity.tickCount + partialTick);
        }
        else
        {
            MassProductionEvaEntity mass = entity instanceof MassProductionEvaEntity mp ? mp : null;
            renderMassProduction(stack, consumer, walk,
                    mass != null && mass.isReviving(), mass != null && mass.isRitualFormation(),
                    mass != null ? mass.getAttackAnim(partialTick) : 0.0F);
        }
        stack.popPose();
        super.render(entity, yaw, partialTick, stack, buffers, packedLight);
    }

    private static void renderSachiel(PoseStack stack, VertexConsumer c, float walk)
    {
        float[] flesh = {0.14F, 0.17F, 0.16F, 1.0F};
        float[] bone = {0.80F, 0.82F, 0.76F, 1.0F};
        float[] core = {1.0F, 0.12F, 0.10F, 1.0F};
        boxAt(stack, c, 0, 9.5F, 0, 3.2F, 5.0F, 2.0F, flesh);
        boxAt(stack, c, 0, 15.0F, 0, 4.6F, 6.0F, 2.5F, flesh);
        boxAt(stack, c, 0, 21.2F, 0, 2.7F, 3.2F, 2.4F, bone);
        boxAt(stack, c, 0, 20.8F, -2.2F, 1.25F, 0.75F, 0.35F, core);
        boxAt(stack, c, 0, 15.0F, -2.55F, 1.35F, 1.35F, 0.35F, core);
        segment(stack, c, v(-3.8F,17.5F,0), v(-6.0F,12.0F + walk,0), 1.2F, flesh);
        segment(stack, c, v(-6.0F,12.0F + walk,0), v(-5.4F,6.0F + walk,0), 0.92F, bone);
        segment(stack, c, v(3.8F,17.5F,0), v(6.0F,12.0F - walk,0), 1.2F, flesh);
        segment(stack, c, v(6.0F,12.0F - walk,0), v(5.4F,6.0F - walk,0), 0.92F, bone);
        segment(stack, c, v(-1.7F,8.0F,0), v(-2.2F,3.7F - walk,0), 1.25F, flesh);
        segment(stack, c, v(-2.2F,3.7F - walk,0), v(-2.0F,0.6F,0), 1.0F, bone);
        segment(stack, c, v(1.7F,8.0F,0), v(2.2F,3.7F + walk,0), 1.25F, flesh);
        segment(stack, c, v(2.2F,3.7F + walk,0), v(2.0F,0.6F,0), 1.0F, bone);
    }

    private static void renderMassProduction(PoseStack stack, VertexConsumer c, float walk,
                                             boolean reviving, boolean ritual, float attack)
    {
        float fade = reviving ? 0.42F : 1.0F;
        float[] white = {0.88F, 0.86F, 0.80F, fade};
        float[] dark = {0.20F, 0.17F, 0.16F, fade};
        float[] red = {0.92F, 0.06F, 0.08F, 1.0F};
        boxAt(stack, c, 0, 12.0F, 0, 3.5F, 5.5F, 2.0F, white);
        boxAt(stack, c, 0, 18.0F, 0, 4.4F, 5.8F, 2.4F, white);
        boxAt(stack, c, 0, 23.0F, 0, 2.5F, 2.5F, 2.1F, white);
        boxAt(stack, c, 0, 22.2F, -2.15F, 1.9F, 0.45F, 0.25F, red);
        boxAt(stack, c, 0, 17.6F, -2.48F, 1.2F, 1.2F, 0.28F, red);
        if (ritual)
        {
            segment(stack, c, v(-3.7F,19.2F,0), v(-10.2F,19.2F,0), 1.25F, white);
            segment(stack, c, v(-10.2F,19.2F,0), v(-16.2F,18.7F,0), 0.92F, dark);
            segment(stack, c, v(3.7F,19.2F,0), v(10.2F,19.2F,0), 1.25F, white);
            segment(stack, c, v(10.2F,19.2F,0), v(16.2F,18.7F,0), 0.92F, dark);
        }
        else
        {
            segment(stack, c, v(-3.7F,19.2F,0), v(-5.1F,13.6F + walk,0), 1.25F, white);
            segment(stack, c, v(-5.1F,13.6F + walk,0), v(-4.6F,8.0F + walk,0), 0.92F, dark);
            float thrust = Mth.sin(attack * Mth.PI);
            segment(stack, c, v(3.7F,19.2F,0), v(5.1F,14.0F - walk,-5.0F * thrust), 1.25F, white);
            segment(stack, c, v(5.1F,14.0F - walk,-5.0F * thrust),
                    v(4.6F,9.0F - walk,-11.0F * thrust), 0.92F, dark);
        }
        segment(stack, c, v(-1.8F,10.5F,0), v(-2.3F,5.3F - walk,0), 1.30F, white);
        segment(stack, c, v(-2.3F,5.3F - walk,0), v(-2.0F,0.8F,0), 1.0F, dark);
        segment(stack, c, v(1.8F,10.5F,0), v(2.3F,5.3F + walk,0), 1.30F, white);
        segment(stack, c, v(2.3F,5.3F + walk,0), v(2.0F,0.8F,0), 1.0F, dark);
        // Four long wing spars give the unit its unmistakable circling silhouette.
        segment(stack, c, v(-2.6F,18.0F,1.5F), v(-15.0F,25.0F,5.0F), 0.72F, white);
        segment(stack, c, v(-2.8F,16.0F,1.5F), v(-13.0F,10.0F,6.0F), 0.64F, white);
        segment(stack, c, v(2.6F,18.0F,1.5F), v(15.0F,25.0F,5.0F), 0.72F, white);
        segment(stack, c, v(2.8F,16.0F,1.5F), v(13.0F,10.0F,6.0F), 0.64F, white);
        // Double-bladed replica spear.
        float spearThrust = ritual ? 0.0F : Mth.sin(attack * Mth.PI) * 10.0F;
        segment(stack, c, v(4.6F,8.0F,-spearThrust), v(5.8F,-1.0F,-1.0F - spearThrust), 0.32F, dark);
        segment(stack, c, v(5.8F,-1.0F,-1.0F - spearThrust),
                v(5.0F,-5.0F,-1.3F - spearThrust), 0.52F, red);
    }

    private static void renderShamshel(PoseStack stack, VertexConsumer c, float time)
    {
        float pulse = 0.85F + 0.15F * Mth.sin(time * 0.14F);
        float[] shell = {0.34F, 0.08F, 0.17F, 1.0F};
        float[] fin = {0.72F, 0.19F, 0.25F, 1.0F};
        float[] core = {1.0F, 0.16F * pulse, 0.10F, 1.0F};
        boxAt(stack, c, 0, 9.0F, 0, 3.1F, 7.5F, 2.6F, shell);
        boxAt(stack, c, 0, 17.0F, 0, 2.0F, 2.2F, 1.8F, shell);
        boxAt(stack, c, 0, 11.0F, -2.8F, 1.5F, 1.5F, 0.25F, core);
        segment(stack, c, v(-2.2F,14.0F,0), v(-8.5F,18.0F,1.0F), 0.75F, fin);
        segment(stack, c, v(2.2F,14.0F,0), v(8.5F,18.0F,1.0F), 0.75F, fin);
        segment(stack, c, v(-2.8F,7.0F,0), v(-8.0F,3.0F,1.5F), 0.68F, fin);
        segment(stack, c, v(2.8F,7.0F,0), v(8.0F,3.0F,1.5F), 0.68F, fin);
        float wave = Mth.sin(time * 0.22F) * 2.5F;
        segment(stack, c, v(-2.8F,10.5F,-1), v(-8.0F,8.5F,-5), 0.38F, core);
        segment(stack, c, v(-8.0F,8.5F,-5), v(-13.0F,7.0F + wave,-12), 0.26F, core);
        segment(stack, c, v(2.8F,10.5F,-1), v(8.0F,8.5F,-5), 0.38F, core);
        segment(stack, c, v(8.0F,8.5F,-5), v(13.0F,7.0F - wave,-12), 0.26F, core);
    }

    private static void renderZeruel(PoseStack stack, VertexConsumer c, float time)
    {
        float[] shell = {0.91F, 0.90F, 0.84F, 1.0F};
        float[] black = {0.07F, 0.06F, 0.06F, 1.0F};
        float[] core = {1.0F, 0.08F, 0.08F, 1.0F};
        boxAt(stack, c, 0, 12.0F, 0, 5.4F, 7.0F, 3.0F, shell);
        boxAt(stack, c, 0, 20.0F, 0, 4.1F, 4.2F, 2.7F, shell);
        boxAt(stack, c, 0, 25.0F, 0, 3.0F, 2.7F, 2.4F, black);
        boxAt(stack, c, -1.15F, 25.2F, -2.45F, 0.45F, 0.28F, 0.20F, core);
        boxAt(stack, c, 1.15F, 25.2F, -2.45F, 0.45F, 0.28F, 0.20F, core);
        boxAt(stack, c, 0, 17.5F, -3.05F, 1.8F, 1.8F, 0.30F, core);
        float sweep = Mth.sin(time * 0.09F) * 1.2F;
        // Layered flat arm ribbons, long enough to read as city-cutting blades.
        segment(stack, c, v(-4.0F,21.0F,0), v(-11.0F,18.0F + sweep,-1), 1.6F, shell);
        segment(stack, c, v(-11.0F,18.0F + sweep,-1), v(-23.0F,14.0F - sweep,-3), 1.15F, shell);
        segment(stack, c, v(4.0F,21.0F,0), v(11.0F,18.0F - sweep,-1), 1.6F, shell);
        segment(stack, c, v(11.0F,18.0F - sweep,-1), v(23.0F,14.0F + sweep,-3), 1.15F, shell);
        segment(stack, c, v(-2.2F,8.0F,0), v(-2.8F,1.0F,0), 1.6F, black);
        segment(stack, c, v(2.2F,8.0F,0), v(2.8F,1.0F,0), 1.6F, black);
    }

    private static Vector3f v(float x, float y, float z) { return new Vector3f(x,y,z); }

    private static void boxAt(PoseStack s, VertexConsumer c, float x,float y,float z,
                              float hx,float hy,float hz,float[] color)
    {
        s.pushPose(); s.translate(x,y,z); box(s,c,-hx,-hy,-hz,hx,hy,hz,color); s.popPose();
    }

    private static void segment(PoseStack s, VertexConsumer c, Vector3f a, Vector3f b,
                                float radius, float[] color)
    {
        Vector3f d = new Vector3f(b).sub(a); float len = d.length();
        Vector3f mid = new Vector3f(a).add(b).mul(0.5F);
        Quaternionf q = new Quaternionf().rotationTo(new Vector3f(0,1,0), d.normalize());
        s.pushPose(); s.translate(mid.x,mid.y,mid.z); s.mulPose(q);
        box(s,c,-radius,-len*0.5F,-radius,radius,len*0.5F,radius,color); s.popPose();
    }

    private static void box(PoseStack s, VertexConsumer c,float x0,float y0,float z0,float x1,float y1,float z1,float[] k)
    {
        Matrix4f p=s.last().pose(); Matrix3f n=s.last().normal();
        quad(p,n,c,x0,y0,z1,x1,y0,z1,x1,y1,z1,x0,y1,z1,0,0,1,k);
        quad(p,n,c,x1,y0,z0,x0,y0,z0,x0,y1,z0,x1,y1,z0,0,0,-1,k);
        quad(p,n,c,x1,y0,z1,x1,y0,z0,x1,y1,z0,x1,y1,z1,1,0,0,k);
        quad(p,n,c,x0,y0,z0,x0,y0,z1,x0,y1,z1,x0,y1,z0,-1,0,0,k);
        quad(p,n,c,x0,y1,z1,x1,y1,z1,x1,y1,z0,x0,y1,z0,0,1,0,k);
        quad(p,n,c,x0,y0,z0,x1,y0,z0,x1,y0,z1,x0,y0,z1,0,-1,0,k);
    }

    private static void quad(Matrix4f p,Matrix3f n,VertexConsumer c,float ax,float ay,float az,float bx,float by,float bz,float cx,float cy,float cz,float dx,float dy,float dz,float nx,float ny,float nz,float[] k)
    {
        vertex(p,n,c,ax,ay,az,0,1,nx,ny,nz,k); vertex(p,n,c,bx,by,bz,1,1,nx,ny,nz,k);
        vertex(p,n,c,cx,cy,cz,1,0,nx,ny,nz,k); vertex(p,n,c,dx,dy,dz,0,0,nx,ny,nz,k);
    }

    private static void vertex(Matrix4f p,Matrix3f n,VertexConsumer c,float x,float y,float z,float u,float v,float nx,float ny,float nz,float[] k)
    {
        c.vertex(p,x,y,z).color(k[0],k[1],k[2],k[3]).uv(u,v).overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(LightTexture.FULL_BRIGHT).normal(n,nx,ny,nz).endVertex();
    }

    @Override
    public ResourceLocation getTextureLocation(T entity)
    {
        return TEXTURE;
    }
}
