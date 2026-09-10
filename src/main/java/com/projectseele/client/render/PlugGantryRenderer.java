package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.VertexFormat;
import com.mojang.blaze3d.vertex.VertexBuffer;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.renderer.GameRenderer;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.entity.NervCarrierPlatformEntity;
import com.projectseele.world.EntryPlugKinematics;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;

/** Original rail hoist: twin girders, reeved winches, four ropes and a two-axis plug chuck. */
public final class PlugGantryRenderer
{
    private static final ResourceLocation PAINT=new ResourceLocation("minecraft","textures/block/white_concrete.png");
    private static final int GREEN=0x566a51, EDGE=0x8d9a86, STEEL=0xadb7bb, DARK=0x222d32, GOLD=0xb69347;
    private final PoseStack poses; private final VertexConsumer buffer; private final int light;private final BufferBuilder baking;
    private static VertexBuffer TOP,YOKE,CHUCK;
    private PlugGantryRenderer(PoseStack poses, MultiBufferSource buffers, int light)
    {this.poses=poses;this.buffer=buffers.getBuffer(RenderType.entitySolid(PAINT));this.light=light;this.baking=null;}
    private PlugGantryRenderer(BufferBuilder builder){this.poses=new PoseStack();this.buffer=builder;this.light=15728880;this.baking=builder;}
    public static void render(NervCarrierPlatformEntity entity,float partial,PoseStack poses,MultiBufferSource buffers,int light)
    {new PlugGantryRenderer(poses,buffers,light).draw(entity,partial);}
    private void draw(NervCarrierPlatformEntity entity,float partial)
    {
        gpu(topMesh(),poses,light);
        Vec3 lower=v(0,entity.getCraneBottomOffset(partial),0);
        EntryPlugCarrierEntity plug=entity.getCranePlug();
        com.projectseele.world.RigidTransform transform=plug==null?null:plug.getInterpolatedCanonicalTransform(partial);
        if(transform!=null)lower=transform.transformPoint(EntryPlugKinematics.CRANE_ATTACHMENT_P).subtract(entity.getPosition(partial));
        Vec3 yoke=lower.add(0,1.6,0);
        for(double x:new double[]{-2.4,2.4})for(double z:new double[]{-.78,.78})
        {
            Vec3 end=yoke.add(x,0,z);rod(v(x,-.7,z),end,.045,STEEL);
            cylinder(end.add(0,-.12,-.20),end.add(0,-.12,.20),.25,.10,DARK,16);
        }
        poses.pushPose();poses.translate(yoke.x,yoke.y,yoke.z);gpu(yokeMesh(),poses,light);poses.popPose();
        // The gimbal centre and its rotating collar derive from the capsule's exact render transform.
        rod(yoke.add(-2.45,-.2,0),lower.add(-1.50,0,0),.17,STEEL);rod(yoke.add(2.45,-.2,0),lower.add(1.50,0,0),.17,STEEL);
        poses.pushPose();poses.translate(lower.x,lower.y,lower.z);
        if(transform!=null)poses.mulPose(transform.rotation());
        gpu(chuckMesh(),poses,light);
        poses.popPose();
    }
    private static VertexBuffer bake(java.util.function.Consumer<PlugGantryRenderer> author)
    {
        BufferBuilder builder=new BufferBuilder(262144);builder.begin(VertexFormat.Mode.QUADS,DefaultVertexFormat.POSITION_COLOR);author.accept(new PlugGantryRenderer(builder));
        VertexBuffer mesh=new VertexBuffer(VertexBuffer.Usage.STATIC);mesh.bind();mesh.upload(builder.end());VertexBuffer.unbind();return mesh;
    }
    private static VertexBuffer topMesh(){if(TOP==null)TOP=bake(PlugGantryRenderer::top);return TOP;}
    private static VertexBuffer yokeMesh(){if(YOKE==null)YOKE=bake(PlugGantryRenderer::yoke);return YOKE;}
    private static VertexBuffer chuckMesh(){if(CHUCK==null)CHUCK=bake(PlugGantryRenderer::chuck);return CHUCK;}
    private static void gpu(VertexBuffer mesh,PoseStack poses,int light)
    {
        var type=RenderType.debugQuads();type.setupRenderState();float illumination=.32F+.68F*Math.max((light>>4)&15,(light>>20)&15)/15F;
        RenderSystem.setShaderColor(illumination,illumination,illumination,1);mesh.bind();mesh.drawWithShader(poses.last().pose(),RenderSystem.getProjectionMatrix(),GameRenderer.getPositionColorShader());VertexBuffer.unbind();RenderSystem.setShaderColor(1,1,1,1);type.clearRenderState();
    }
    private void top()
    {
        for(double z:new double[]{-1.65,1.65})
        {
            box(-6.6,-.10,z-.25,13.2,.16,.50,GREEN);box(-6.6,.90,z-.25,13.2,.16,.50,GREEN);box(-6.6,.06,z-.08,13.2,.84,.16,EDGE);
            for(double x:new double[]{-6,6}){box(x-.5,-.12,z-.5,1,1.1,1,GREEN);cylinder(v(x,-.06,z-.52),v(x,-.06,z+.52),.38,.16,DARK,24);}
        }
        box(-3,-.65,-1.7,6,.28,3.4,GREEN);
        for(double x:new double[]{-2.30,2.30})
        {
            cylinder(v(x,-.06,-1.25),v(x,-.06,1.25),.48,.14,STEEL,24);
            for(int n=0;n<15;n++)cylinder(v(x,-.06,-1.20+n*.16),v(x,-.06,-1.16+n*.16),.51,.48,DARK,24);
            box(x-.52,-.25,1.25,1.04,.9,.72,GREEN);cylinder(v(x,.15,1.97),v(x,.15,2.08),.32,0,STEEL,20);
            for(double z:new double[]{-1.08,1.08})box(x-.7,-.64,z-.18,1.4,.18,.36,GOLD);
        }
        box(-.62,-.45,-1.1,1.24,1.5,1.9,GREEN);
        for(int i=0;i<6;i++)box(-.55,.10+i*.12,-1.14,1.1,.035,.08,DARK);
        // Rounded motor casings, cooling fins and flexible hydraulic lines are real mesh surfaces.
        for(double side:new double[]{-1,1})
        {
            Vec3 centre=v(side*3.65,.03,.15);cylinder(centre.add(-.85,0,0),centre.add(.85,0,0),.50,0,GREEN,48);
            for(int i=0;i<14;i++)cylinder(centre.add(-.72+i*.11,0,0),centre.add(-.68+i*.11,0,0),.54,.49,EDGE,48);
            for(int i=0;i<8;i++){double a=i*Math.PI/4;Vec3 ring=v(0,Math.cos(a)*.39,Math.sin(a)*.39);cylinder(centre.add(.85,0,0).add(ring),centre.add(.90,0,0).add(ring),.045,0,STEEL,10);}
            Vec3 last=centre.add(side*.9,.1,0);
            for(int i=1;i<=24;i++){double t=i/24D;Vec3 next=v(side*(4.55+Math.sin(t*Math.PI)*.6),.13-Math.sin(t*Math.PI)*.38,t*1.1+.15);rod(last,next,.055,DARK);last=next;}
        }
    }
    private void yoke()
    {
        box(0-3,0-.25,0-1.05,6,.38,.28,GREEN);box(0-3,0-.25,0+.77,6,.38,.28,GREEN);
        for(double x:new double[]{-2.5,2.5})box(0+x-.2,0-.28,0-1.05,.4,.5,2.1,EDGE);
    }
    private void chuck()
    {
        cylinder(v(0,0,-.42),v(0,0,.32),1.62,1.18,GREEN,40);
        cylinder(v(0,0,-.48),v(0,0,-.37),1.70,1.20,STEEL,40);
        cylinder(v(0,0,.29),v(0,0,.44),1.66,1.22,GOLD,40);
        for(int i=0;i<8;i++)
        {
            double a=i*Math.PI/4;Vec3 r=v(Math.cos(a),Math.sin(a),0);
            cylinder(r.scale(1.45).add(0,0,.44),r.scale(1.45).add(0,0,.53),.08,0,DARK,10);
            if(i%2==0){rod(r.scale(1.62).add(0,0,-.25),r.scale(1.27).add(0,0,-.8),.11,STEEL);}
        }
    }
    private void box(double x,double y,double z,double w,double h,double d,int colour)
    {
        Vec3 a=v(x,y,z),b=v(x+w,y,z),c=v(x+w,y+h,z),e=v(x,y+h,z),f=v(x,y,z+d),g=v(x+w,y,z+d),i=v(x+w,y+h,z+d),j=v(x,y+h,z+d);
        quad(a,e,c,b,colour);quad(f,g,i,j,colour);quad(a,f,j,e,colour);quad(b,c,i,g,colour);quad(e,j,i,c,colour);quad(a,b,g,f,colour);
    }
    private void rod(Vec3 a,Vec3 b,double radius,int colour){cylinder(a,b,radius,0,colour,12);}
    private void cylinder(Vec3 a,Vec3 b,double radius,double inside,int colour,int segments)
    {
        Vec3 axis=b.subtract(a).normalize(),x=axis.cross(Math.abs(axis.y)<.9?v(0,1,0):v(1,0,0)).normalize(),y=axis.cross(x);
        for(int n=0;n<segments;n++)
        {
            double s=2*Math.PI*n/segments,t=2*Math.PI*(n+1)/segments;
            Vec3 r=x.scale(Math.cos(s)).add(y.scale(Math.sin(s))),q=x.scale(Math.cos(t)).add(y.scale(Math.sin(t)));
            quad(a.add(r.scale(radius)),a.add(q.scale(radius)),b.add(q.scale(radius)),b.add(r.scale(radius)),colour);
            quad(a.add(r.scale(inside)),a.add(q.scale(inside)),a.add(q.scale(radius)),a.add(r.scale(radius)),colour);
            quad(b.add(r.scale(radius)),b.add(q.scale(radius)),b.add(q.scale(inside)),b.add(r.scale(inside)),colour);
            if(inside>0)quad(a.add(r.scale(inside)),b.add(r.scale(inside)),b.add(q.scale(inside)),a.add(q.scale(inside)),DARK);
        }
    }
    private void quad(Vec3 a,Vec3 b,Vec3 c,Vec3 d,int colour)
    {
        Vec3 n=b.subtract(a).cross(c.subtract(a));if(n.lengthSqr()<1e-12)return;n=n.normalize();
        float red=((colour>>16)&255)/255F,green=((colour>>8)&255)/255F,blue=(colour&255)/255F;
        if(baking!=null)
        {
            float shade=(float)(.64+.36*Math.max(0,n.dot(v(-.3,.8,-.45).normalize())));
            for(Vec3 p:new Vec3[]{a,b,c,d})baking.vertex((float)p.x,(float)p.y,(float)p.z).color(red*shade,green*shade,blue*shade,1).endVertex();return;
        }
        for(Vec3 p:new Vec3[]{a,b,c,d})buffer.vertex(poses.last().pose(),(float)p.x,(float)p.y,(float)p.z).color(red,green,blue,1).uv(.5F,.5F).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(light).normal(poses.last().normal(),(float)n.x,(float)n.y,(float)n.z).endVertex();
    }
    private static Vec3 v(double x,double y,double z){return new Vec3(x,y,z);}
}
