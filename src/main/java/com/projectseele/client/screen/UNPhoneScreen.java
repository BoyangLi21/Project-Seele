package com.projectseele.client.screen;

import com.projectseele.network.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.*;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public final class UNPhoneScreen extends Screen
{
    private ClientboundUNStatusPacket view;
    private int serial,age,x,y,w,h,savedScale=-1;private boolean restoring;
    private EditBox targetX,targetZ;
    private UNPhoneScreen(ClientboundUNStatusPacket view){super(Component.literal("联合国战略运输通信"));this.view=view;}
    public static void receive(ClientboundUNStatusPacket packet)
    {
        var mc=Minecraft.getInstance();
        if(mc.screen instanceof UNPhoneScreen screen)
        {screen.view=new ClientboundUNStatusPacket(false,packet.unit00(),packet.unit01(),packet.reply().isEmpty()?screen.view.reply():packet.reply());}
        else if(packet.open())mc.setScreen(new UNPhoneScreen(packet));
        else if(!packet.reply().isEmpty()&&mc.player!=null)mc.player.sendSystemMessage(Component.literal(packet.reply()));
    }
    private void button(String label,int xx,int yy,int width,Runnable action)
    {addRenderableWidget(Button.builder(Component.literal(label),b->action.run()).bounds(xx,yy,width,20).build());}
    @Override protected void init()
    {
        if(height<302&&savedScale<0&&minecraft.options.guiScale().get()!=2)
        {savedScale=minecraft.options.guiScale().get();minecraft.options.guiScale().set(2);minecraft.resizeDisplay();return;}
        w=Math.min(470,width-12);h=Math.min(302,height-12);x=(width-w)/2;y=(height-h)/2;
        button("EVA-UN-00",x+10,y+27,120,()->{serial=0;});button("EVA-UN-01",x+136,y+27,120,()->{serial=1;});button("关闭",x+w-58,y+6,48,this::onClose);
        targetX=new EditBox(font,x+26,y+79,92,20,Component.literal("投放 X"));targetZ=new EditBox(font,x+143,y+79,92,20,Component.literal("投放 Z"));
        targetX.setMaxLength(10);targetZ.setMaxLength(10);targetX.setValue(Integer.toString(minecraft.player.getBlockX()));targetZ.setValue(Integer.toString(minecraft.player.getBlockZ()));addRenderableWidget(targetX);addRenderableWidget(targetZ);
        int size=(w-30)/2;
        button("投放到指定 X / Z",x+10,y+105,size,()->send("deliver"));
        button("使用我当前位置",x+20+size,y+105,size,()->{targetX.setValue(Integer.toString(minecraft.player.getBlockX()));targetZ.setValue(Integer.toString(minecraft.player.getBlockZ()));});
        button("运输机回收至基地",x+10,y+130,size,()->send("recover"));button("取消运输 / 安全返回",x+20+size,y+130,size,()->send("cancel"));
        int third=(w-40)/3;
        button("机库排液",x+10,y+155,third,()->send("drain"));button("机库舱门",x+20+third,y+155,third,()->send("door"));button("机库注液",x+30+third*2,y+155,third,()->send("fill"));
        button("接入驾驶舱",x+10,y+180,size,()->send("board"));button("刷新状态",x+20+size,y+180,size,()->send("status"));
    }
    private void send(String action)
    {
        try{SeeleNetwork.CHANNEL.sendToServer(new ServerboundUNCommandPacket(action,serial,action.equals("deliver")?Integer.parseInt(targetX.getValue().strip()):0,action.equals("deliver")?Integer.parseInt(targetZ.getValue().strip()):0));}
        catch(NumberFormatException error){view=new ClientboundUNStatusPacket(false,view.unit00(),view.unit01(),"请输入有效的整数 X、Z 坐标。高度由地表净空检查确定。");}
    }
    @Override public void tick(){super.tick();if(++age%20==0)send("status");}
    @Override public boolean isPauseScreen(){return false;}
    @Override public void removed()
    {
        if(savedScale>=0&&!restoring){restoring=true;minecraft.options.guiScale().set(savedScale);minecraft.resizeDisplay();}
        super.removed();
    }
    @Override public void render(GuiGraphics g,int mx,int my,float partial)
    {
        renderBackground(g);g.fill(x,y,x+w,y+h,0xF0142430);g.fill(x,y,x+w,y+3,0xFF59AFE2);
        g.drawString(font,title,x+10,y+10,0xFFE1F4FF,false);
        String status=serial==0?view.unit00():view.unit01();g.drawWordWrap(font,Component.literal(status),x+10,y+52,w-20,0xFFC2D8E5);
        g.drawString(font,"X",x+10,y+85,0xFFFFFFFF,false);g.drawString(font,"Z",x+127,y+85,0xFFFFFFFF,false);
        g.drawWordWrap(font,Component.literal(view.reply()),x+10,y+209,w-20,0xFFF0D696);
        super.render(g,mx,my,partial);
    }
}
