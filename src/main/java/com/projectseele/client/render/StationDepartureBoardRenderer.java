package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import com.projectseele.world.StationDepartureBoardBlock;
import com.projectseele.world.StationDepartureBoardBlockEntity;
import net.minecraft.client.gui.Font;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.client.renderer.blockentity.BlockEntityRendererProvider;

public final class StationDepartureBoardRenderer implements BlockEntityRenderer<StationDepartureBoardBlockEntity>
{
    private final Font font;
    public StationDepartureBoardRenderer(BlockEntityRendererProvider.Context context) { font=context.getFont(); }
    @Override public void render(StationDepartureBoardBlockEntity board,float partial,PoseStack poses,MultiBufferSource buffers,int light,int overlay)
    {
        poses.pushPose();poses.translate(.5,1.08,.5);
        poses.mulPose(Axis.YP.rotationDegrees(-board.getBlockState().getValue(StationDepartureBoardBlock.FACING).toYRot()));
        poses.translate(0,0,.132);poses.scale(.0125F,-.0125F,.0125F);
        line(board.title(),0,0xffedbd55,poses,buffers);
        line(board.station(),11,0xffabbec5,poses,buffers);
        for(int i=0;i<board.rows().size();i++) line(board.rows().get(i),25+i*13,i==0?0xffe9efde:0xffa9d9ae,poses,buffers);
        poses.popPose();
    }
    private void line(String text,int y,int color,PoseStack poses,MultiBufferSource buffers)
    {
        poses.pushPose();float fit=Math.min(1,216F/Math.max(1,font.width(text)));poses.translate(0,y,0);poses.scale(fit,1,1);
        font.drawInBatch(text,-font.width(text)/2F,0,color,false,poses.last().pose(),buffers,Font.DisplayMode.NORMAL,0,15728880);
        poses.popPose();
    }
    @Override public int getViewDistance() { return 96; }
}
