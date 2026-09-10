package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.registry.ModItems;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.*;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.phys.*;
import java.util.*;

/** Deterministic dialogue and finite, server-authoritative console requests. */
public final class NervStaffDialogue
{
    private static final Map<String,List<String>> LINES=Map.of(
            "commander",List.of("这里是作战指挥。先确认驾驶员同步和发射通道，再下达出击指令。","全员按岗位待命。我会在这里确认发射与回收。"),
            "scientist",List.of("同步率、供电和插入栓锁定都必须逐项核对。","回收后先固定机体，再恢复 LCL。不要跳过安全联锁。"),
            "operator",List.of("MAGI 监视中。机库、供电和各发射轨道的状态会持续回传。","指挥链路在线。等待作战指令。"),
            "medic",List.of("这里是医疗值班点。驾驶员回收后请先接受检查。"),
            "guard",List.of("请出示通行证。保持门口和运输通道畅通。"),
            "un_guard",List.of("UN 安保值勤。试验区未经许可不得进入。"),
            "un_crew",List.of("车辆、航空器和试验机库按值班表检查。控制设备请交给当班人员。"),
            "technician",List.of("本区设备运行中。我正在记录压力、供电和检修情况。"));
    private static void say(ServerPlayer player,String name,String line)
    {
        player.sendSystemMessage(Component.literal("「"+name+"」 ").withStyle(ChatFormatting.AQUA).append(Component.literal(line).withStyle(ChatFormatting.WHITE)));
        if("r15-staff".equals(System.getProperty("projectseele.regionalBuild","")))ProjectSeele.LOGGER.info("STAFF REVIEW DIALOGUE {} {}",name,line);
    }
    private static MutableComponent option(String text,String command)
    {return Component.literal("["+text+"] ").withStyle(s->s.withColor(ChatFormatting.GOLD).withClickEvent(new ClickEvent(ClickEvent.Action.RUN_COMMAND,command)));}
    private static String stage(String value)
    {
        EvaFleetSavedData.Phase phase;
        try{phase=EvaFleetSavedData.Phase.valueOf(value);}catch(RuntimeException exception){return "等待状态确认";}
        return switch(phase)
        {
            case PARKED->"机库待命";case BRIDGE_RETRACTING->"收回登机桥";case PLUG_INSERTING->"插入栓接入";
            case PLUG_ABORT_RETURNING,PLUG_ABORT_DOCKED->"中止接入并返回";case PLUG_FAULT->"插入栓故障，等待检修";
            case PLUG_LOCKING->"锁定插入栓";case DRAINING->"排出 LCL";case TO_SILO->"运往发射井";
            case SILO_READY->"发射待命";case DEPLOYED->"已出动";case DESCENDING->"回收下降";
            case TO_HANGAR->"返回机库";case FILLING->"恢复 LCL";
        };
    }
    public static void open(ServerPlayer player,NervStaffEntity npc)
    {
        var lines=LINES.getOrDefault(npc.staffRole(),LINES.get("technician"));say(player,npc.getName().getString(),lines.get((int)(player.level().getGameTime()/100+Math.abs(npc.getId()))%lines.size()));
        String prefix="/nerv talk \""+npc.memberId()+"\" ";var menu=option("战况",prefix+"状态");
        if(Set.of("commander","scientist").contains(npc.staffRole()))
        {
            for(int v=0;v<3;v++){String unit=String.format(Locale.ROOT,"%02d",v);menu.append(option("整备 "+unit,prefix+"整备 "+unit)).append(option("发射 "+unit,prefix+"发射 "+unit)).append(option("回收 "+unit,prefix+"回收 "+unit));}
            menu.append(option("取消当前操作",prefix+"停止操作"));
        }
        player.sendSystemMessage(menu);
    }
    public static boolean authorized(ServerPlayer player)
    {
        return player.createCommandSourceStack().hasPermission(2)||player.getInventory().items.stream().anyMatch(s->s.is(ModItems.NERV_EMPLOYEE_CARD.get())||s.is(ModItems.TERMINAL_DOGMA_ACCESS_CARD.get()));
    }
    public static int talk(ServerPlayer player,String target,String text)
    {
        var nearby=player.serverLevel().getEntitiesOfClass(NervStaffEntity.class,player.getBoundingBox().inflate(10),n->n.memberId().equals(target)||n.getStringUUID().equals(target));
        if(nearby.isEmpty()){player.sendSystemMessage(Component.literal("请走到工作人员身边再交谈。"));return 0;}
        var npc=nearby.get(0);if(player.distanceToSqr(npc)>100)return 0;
        if(text.equals("停止操作"))
        {
            if(npc.busy()&&!player.getUUID().equals(npc.requester())&&!player.createCommandSourceStack().hasPermission(2))
            {say(player,npc.getName().getString(),"这项操作由另一名指挥人员下达，请由下令人取消。");return 0;}
            npc.finishTask();say(player,npc.getName().getString(),"收到，停止尚未执行的操作。");return 1;
        }
        if(text.contains("状态")||text.contains("战况"))
        {
            for(int v=0;v<3;v++){var status=EvaLogisticsDirector.status(player.serverLevel(),v);say(player,npc.getName().getString(),String.format(Locale.ROOT,"EVA-%02d：%s，%s。",v,stage(status.phase()),status.loaded()?"机体信号在线":"等待远端信号"));}return 1;
        }
        var command=java.util.regex.Pattern.compile("^(?:请|请帮我|帮我)?(整备|准备|发射|出击|回收)\\s*(?:EVA[-_ ]?)?(00|01|02|零号机?|零號機?|初号机?|初號機?|二号机?|二號機?|贰号机?)$",java.util.regex.Pattern.CASE_INSENSITIVE).matcher(text.trim());
        String op="";
        if(command.matches())op=switch(command.group(1)){case "整备","准备"->"prepare";case "发射","出击"->"launch";default->"recover";};
        else if(text.matches(".*(?:整备|准备|发射|出击|回收).*"))
        {say(player,npc.getName().getString(),"请明确指定一个动作和一台机体，例如「整备 01」。询问、否定和多项指令不会执行。");return 0;}
        if(op.isEmpty()){open(player,npc);return 1;}
        if(!Set.of("commander","scientist").contains(npc.staffRole())||!authorized(player)){say(player,npc.getName().getString(),"这项操作需要指挥权限或 NERV 通行证。");return 0;}
        if(npc.busy()){say(player,npc.getName().getString(),"正在执行上一项操作。请稍候，或先取消。");return 0;}
        String unit=command.group(2);int variant=unit.matches("00|零.*")?0:unit.matches("01|初.*")?1:2;
        if(variant<0){say(player,npc.getName().getString(),"请明确指定 EVA-00、EVA-01 或 EVA-02。");return 0;}
        BlockPos control=NervOperationsConsole.staffControl(player.serverLevel(),op,variant);
        if(control==null||!(player.serverLevel().getBlockState(control).getBlock() instanceof ButtonBlock)){say(player,npc.getName().getString(),"对应实体按键不可用，操作中止。");return 0;}
        BlockPos approach=approach(npc,control);
        if(approach==null){say(player,npc.getName().getString(),"通往按键的路径受阻，请先清理控制台旁的通道。");return 0;}
        EvaLogisticsDirector.loadControlTarget(player.serverLevel(),variant);
        npc.begin(player.getUUID(),op,variant,control,approach);say(player,npc.getName().getString(),"收到。我去操作 EVA-"+String.format(Locale.ROOT,"%02d",variant)+" 的"+(op.equals("prepare")?"整备":op.equals("launch")?"发射":"回收")+"按键。联锁检查仍然有效。");return 1;
    }
    private static BlockPos approach(NervStaffEntity npc,BlockPos button)
    {
        var level=(ServerLevel)npc.level();List<BlockPos> options=new ArrayList<>();var buttonState=level.getBlockState(button);
        var facing=buttonState.getValue(net.minecraft.world.level.block.state.properties.BlockStateProperties.HORIZONTAL_FACING);Vec3 outward=Vec3.atLowerCornerOf(facing.getNormal());
        for(BlockPos p:BlockPos.betweenClosed(button.offset(-3,-3,-3),button.offset(3,0,3)))
        {
            if(!level.hasChunkAt(p)||level.getBlockState(p.below()).getCollisionShape(level,p.below()).isEmpty())continue;
            if(!level.noCollision(npc,new AABB(p.getX()+.2,p.getY()+.01,p.getZ()+.2,p.getX()+.8,p.getY()+1.8,p.getZ()+.8)))continue;
            Vec3 eye=Vec3.atBottomCenterOf(p).add(0,1.5,0);
            if(eye.distanceToSqr(Vec3.atCenterOf(button))>6.25||eye.subtract(Vec3.atCenterOf(button)).dot(outward)<.3)continue;
            var hit=level.clip(new net.minecraft.world.level.ClipContext(eye,Vec3.atCenterOf(button),net.minecraft.world.level.ClipContext.Block.COLLIDER,net.minecraft.world.level.ClipContext.Fluid.NONE,npc));
            if(hit.getType()!=HitResult.Type.MISS&&!hit.getBlockPos().equals(button))continue;options.add(p.immutable());
        }
        options.sort(Comparator.comparingDouble(p->npc.distanceToSqr(Vec3.atBottomCenterOf(p))));
        if("r15-staff".equals(System.getProperty("projectseele.regionalBuild","")))ProjectSeele.LOGGER.info("STAFF PATH REVIEW actor={} pos={} onGround={} candidates={}",npc.memberId(),npc.position(),npc.onGround(),options);
        for(var p:options){var path=npc.getNavigation().createPath(p,0);if(path!=null&&path.canReach())return p;}return null;
    }
    public static void tickTask(NervStaffEntity npc,UUID owner,String operation,int variant,BlockPos control,BlockPos approach,int ticks)
    {
        var level=(ServerLevel)npc.level();var player=level.getServer().getPlayerList().getPlayer(owner);
        if(ticks%40==0&&"r15-staff-controls".equals(System.getProperty("projectseele.regionalBuild","")))ProjectSeele.LOGGER.info("STAFF CONTROL TRACE actor={} pos={} target={} navDone={} onGround={} loaded={}",npc.memberId(),npc.position(),approach,npc.getNavigation().isDone(),npc.onGround(),EvaLogisticsDirector.status(level,variant).loaded());
        if(player==null||player.level()!=level||player.distanceToSqr(npc)>48*48||!authorized(player)||ticks>300)
        {if(player!=null)say(player,npc.getName().getString(),"操作中止：人员离开、权限变化或路径超时。");npc.finishTask();return;}
        if(ticks%20==0&&!EvaLogisticsDirector.status(level,variant).loaded())EvaLogisticsDirector.loadControlTarget(level,variant);
        if(npc.distanceToSqr(Vec3.atBottomCenterOf(approach))>.8)
        {if(ticks%20==0)npc.getNavigation().moveTo(approach.getX()+.5,approach.getY(),approach.getZ()+.5,.9);return;}
        npc.getNavigation().stop();npc.getLookControl().setLookAt(control.getX()+.5,control.getY()+.5,control.getZ()+.5,30,30);
        if(ticks%20!=0)return;
        if(!EvaLogisticsDirector.status(level,variant).loaded()&&ticks<240)return;
        var state=level.getBlockState(control);
        if(!(state.getBlock() instanceof ButtonBlock)||state.getValue(ButtonBlock.POWERED))
        {say(player,npc.getName().getString(),"按键状态已变化，操作未执行。");npc.finishTask();return;}
        npc.pressing();
        // Physical depression and the existing authoritative console dispatcher are
        // separate in the original player interaction hook. Invoke each exactly once.
        state.use(level,player,InteractionHand.MAIN_HAND,new BlockHitResult(Vec3.atCenterOf(control),net.minecraft.core.Direction.UP,control,false));
        boolean handled=NervOperationsConsole.handleUse(player,control);var status=EvaLogisticsDirector.status(level,variant);
        say(player,npc.getName().getString(),handled?"按键已操作。当前状态："+stage(status.phase())+"。":"控制台没有接受这个按键。");
        ProjectSeele.LOGGER.info("STAFF CONSOLE actor={} operation={} unit={} button={} requester={} phase={}",npc.memberId(),operation,variant,control,owner,status.phase());npc.finishTask();
    }
    public static void pilot(ServerPlayer player,TrainingPilotEntity pilot)
    {
        int v=pilot.getAssignedVariant();String line=switch(v){case 0->"明白。等待指令。";case 2->"准备好了。先确认轨道和供电，别把程序弄乱。";default->"我在。出击前请再确认一次同步状态。";};
        String stage=switch(pilot.getTrainingStage()){case TrainingPilotEntity.STAGE_IN_PLUG->"插入栓内，等待连接";case TrainingPilotEntity.STAGE_LINKED->"神经连接已建立";case TrainingPilotEntity.STAGE_STANDBY->"待命";default->"前往登机位置";};
        say(player,String.format(Locale.ROOT,"DUMMY-%02d",v),line+" 当前："+stage+"。");
    }
    private NervStaffDialogue() {}
}
