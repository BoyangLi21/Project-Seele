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
    public static void say(ServerPlayer player,String name,String line)
    {
        player.sendSystemMessage(Component.literal("「"+name+"」 ").withStyle(ChatFormatting.AQUA).append(Component.literal(line).withStyle(ChatFormatting.WHITE)));
        if("r15-staff".equals(System.getProperty("projectseele.regionalBuild","")))ProjectSeele.LOGGER.info("STAFF REVIEW DIALOGUE {} {}",name,line);
    }
    public static void reply(ServerPlayer player,NervStaffEntity npc,String line)
    {
        say(player,npc.getName().getString(),line);
        StaffConversationR24.note(player,npc,line);
    }
    public static void greet(ServerPlayer player,NervStaffEntity npc)
    {
        say(player,npc.getName().getString(),StaffDialogueCatalogR24.line(
                npc.skin(),npc.staffRole(),"greeting",player.tickCount/40+npc.getId()));
    }
    private static MutableComponent option(String text,String command)
    {return Component.literal("["+text+"] ").withStyle(s->s.withColor(ChatFormatting.GOLD).withClickEvent(new ClickEvent(ClickEvent.Action.RUN_COMMAND,command)));}
    public static String stage(String value)
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
    { StaffConversationR24.open(player,npc,false); }
    public static void openChat(ServerPlayer player,NervStaffEntity npc)
    {
        reply(player,npc,StaffDialogueCatalogR24.line(npc.skin(),npc.staffRole(),"greeting",player.tickCount / 100));
        String prefix="/nerv talk \""+npc.memberId()+"\" ";var menu=option("战况",prefix+"状态");
        if(StaffAuthorityR25.commandContact(npc))
        {
            for(int v=0;v<3;v++){String unit=String.format(Locale.ROOT,"%02d",v);menu.append(option("整备 "+unit,prefix+"整备 "+unit)).append(option("发射 "+unit,prefix+"发射 "+unit)).append(option("回收 "+unit,prefix+"回收 "+unit));}
            menu.append(option("整备后发射 01",prefix+"整备后发射 01")).append(option("取消后续操作",prefix+"停止操作"));
        }
        player.sendSystemMessage(menu);
        player.sendSystemMessage(option("道路指引",prefix+"TOPIC:directions").append(option("同步与驾驶",prefix+"TOPIC:sync")).append(option("插入栓",prefix+"TOPIC:plug")).append(option("作战记录",prefix+"TOPIC:campaign")).append(option("值班闲聊",prefix+"TOPIC:duty")));
    }
    public static boolean authorized(ServerPlayer player)
    {
        return player.createCommandSourceStack().hasPermission(2)||java.util.stream.Stream.concat(player.getInventory().items.stream(),player.getInventory().offhand.stream()).anyMatch(s->s.is(ModItems.NERV_EMPLOYEE_CARD.get())||s.is(ModItems.TERMINAL_DOGMA_ACCESS_CARD.get()));
    }
    public static int talk(ServerPlayer player,String target,String text)
    {
        var nearby=player.serverLevel().getEntitiesOfClass(NervStaffEntity.class,player.getBoundingBox().inflate(10),n->n.memberId().equals(target)||n.getStringUUID().equals(target));
        if(nearby.isEmpty()){player.sendSystemMessage(Component.literal("请走到工作人员身边再交谈。"));return 0;}
        var npc=nearby.get(0);if(player.distanceToSqr(npc)>100)return 0;
        return converse(player,npc,text);
    }
    public static int converse(ServerPlayer player,NervStaffEntity npc,String text)
    {
        if(text.startsWith("ROUTE:"))
        {reply(player,npc,NervWayfindingR24.start(player,text.substring(6)));return 1;}
        if(text.startsWith("CAMPAIGN:"))
        {
            if(!StaffAuthorityR25.allows(npc,"campaign") || !authorized(player))
            {reply(player,npc,"请向作战指挥或技术负责人提交作战指令。");return 0;}
            int result=switch(text)
            {
                case "CAMPAIGN:begin" -> com.projectseele.event.TvCampaignDirector.begin(player);
                case "CAMPAIGN:cancel" -> com.projectseele.event.TvCampaignDirector.cancel(player);
                default -> 0;
            };
            reply(player,npc,com.projectseele.event.TvCampaignDirector.briefing(player));return result;
        }
        var intent=StaffIntentR24.parse(text);
        switch(intent.kind())
        {
            case CANCEL -> { return StaffCommandBookR24.cancel(player,npc,intent.unit()); }
            case ACTION ->
            {
                if(intent.subject().startsWith("city_"))
                {
                    if(!authorized(player)||!StaffAuthorityR25.allows(npc,intent.subject()))
                    {reply(player,npc,"城市升降由总指挥席的冬月负责，请联络冬月。");return 0;}
                    if(npc.busy()||StaffCommandBookR24.order(npc)!=null){reply(player,npc,"正在操作控制台，请稍候。");return 0;}
                    return beginNativeAction(player,npc,intent.subject(),-1);
                }
                if(intent.subject().equals("board"))
                {reply(player,npc,StaffPilotOrdersR25.request(player,npc,intent.unit()));return 1;}
                return StaffCommandBookR24.request(player,npc,intent.subject(),intent.unit());
            }
            case INVALID -> { reply(player,npc,intent.subject());return 0; }
            case QUERY ->
            {
                List<String> lines=new ArrayList<>();
                for(int v=0;v<3;v++)if(intent.unit()<0||intent.unit()==v)
                    lines.add(unitName(v)+"："+readinessHint(player.serverLevel(),v,"query"));
                reply(player,npc,String.join("\n",lines));return 1;
            }
            default ->
            {
                if(intent.subject().equals("status"))
                {
                    for(int v=0;v<3;v++)
                    {
                        var status=EvaLogisticsDirector.status(player.serverLevel(),v);
                        reply(player,npc,unitName(v)+"："+stage(status.phase())+"，"+(status.loaded()?"机体信号在线":"等待远端信号")+"。");
                    }
                    var job=StaffCommandBookR24.order(npc);if(job!=null)reply(player,npc,"当前指令："+unitName(job.unit)+" · "+job.message+"。");
                }
                else if(intent.subject().equals("campaign"))
                    reply(player,npc,com.projectseele.event.TvCampaignDirector.briefing(player));
                else if(intent.subject().equals("city"))
                {
                    var origin=IntegratedNervMapBuilder.tokyo3Origin(player.serverLevel());
                    int depth=Tokyo3RetractionDirector.depth(player.serverLevel(),origin);
                    reply(player,npc,"第三新东京市当前下沉深度："+depth+" 米。城市升降由最高指挥席的冬月操作；电话中联络冬月后选择「城市」。");
                }
                else if(intent.subject().equals("directions"))
                    reply(player,npc,npc.staffRole().startsWith("un_")
                        ?"请沿基地的人员标线前往车辆区、航空区或试验机库，避开滑行道和舱门作业范围。总部步行引导仅在地下总部公共通道内可用。"
                        :NervWayfindingR24.describe(player));
                else reply(player,npc,StaffDialogueCatalogR24.line(npc.skin(),npc.staffRole(),intent.subject(),player.tickCount/100));
                return 1;
            }
        }
    }
    public static String unitName(int variant)
    {return switch(variant){case 0->"零号机";case 1->"初号机";default->"二号机";};}
    public static boolean boarded(ServerLevel level,int variant)
    {
        var unit=EvaLogisticsDirector.canonicalUnit(level,variant);if(unit==null)return false;
        if(unit.getPilotEntity()!=null)return true;
        var plug=EntryPlugDirector.canonical(level,variant);
        return plug!=null&&(plug.getFirstPassenger() instanceof ServerPlayer||plug.getFirstPassenger() instanceof TrainingPilotEntity);
    }
    public static String readinessHint(ServerLevel level,int variant,String operation)
    {
        var status=EvaLogisticsDirector.status(level,variant);
        if(!status.loaded())return "等待远端机库信号。";
        return switch(status.phase())
        {
            case "PARKED" -> boarded(level,variant)?"驾驶员已登机，可以提交整备；接入和轨道仍需通过联锁检查。":"请先进入对应机库悬挂的插入栓。驾驶员登机后才能整备。";
            case "SILO_READY" -> "机体已到发射台；发射前仍会复核插入栓与轨道锁定。";
            case "DEPLOYED" -> "机体正在出动。回收前请回到本机的地表回收平台并停稳。";
            case "PLUG_FAULT" -> "插入栓接入出现故障，请在机库检查并中止故障接入流程。";
            default -> "当前正在"+stage(status.phase())+"，请等待这一阶段完成。";
        };
    }
    public static int beginNativeAction(ServerPlayer player,NervStaffEntity npc,String op,int variant)
    {
        if(!StaffAuthorityR25.allows(npc,op)||!authorized(player)||npc.busy())return 0;
        BlockPos control=NervOperationsConsole.staffControl(player.serverLevel(),op,variant);
        if(control==null||!(player.serverLevel().getBlockState(control).getBlock() instanceof ButtonBlock)){reply(player,npc,"对应实体按键不可用，操作中止。");return 0;}
        BlockPos approach=approach(npc,control,op.startsWith("city_"));
        if(approach==null){reply(player,npc,"通往按键的路径受阻，请先清理控制台旁的通道。");return 0;}
        if(op.startsWith("city_"))
        {
            npc.begin(player.getUUID(),op,variant,control,approach);
            reply(player,npc,"收到。我去操作城市"+(op.equals("city_rise")?"升起":"降下")+"按键。执行前仍检查城市运行状态。");return 1;
        }
        EvaLogisticsDirector.loadControlTarget(player.serverLevel(),variant);
        npc.begin(player.getUUID(),op,variant,control,approach);reply(player,npc,"收到。我去操作 EVA-"+String.format(Locale.ROOT,"%02d",variant)+" 的"+(op.equals("prepare")?"整备":op.equals("launch")?"发射":"回收")+"按键。联锁检查仍然有效。");return 1;
    }
    private static BlockPos approach(NervStaffEntity npc,BlockPos button,boolean city)
    {
        var level=(ServerLevel)npc.level();List<BlockPos> options=new ArrayList<>();var buttonState=level.getBlockState(button);
        var facing=buttonState.getValue(net.minecraft.world.level.block.state.properties.BlockStateProperties.HORIZONTAL_FACING);
        var normal=switch(buttonState.getValue(net.minecraft.world.level.block.state.properties.BlockStateProperties.ATTACH_FACE))
        {case FLOOR->net.minecraft.core.Direction.UP;case CEILING->net.minecraft.core.Direction.DOWN;case WALL->facing;};
        Vec3 outward=Vec3.atLowerCornerOf(normal.getNormal());
        Vec3 contact=Vec3.atLowerCornerOf(button).add(buttonState.getShape(level,button).bounds().getCenter());
        for(BlockPos p:BlockPos.betweenClosed(button.offset(-3,-3,-3),button.offset(3,0,3)))
        {
            // City keys sit on a desk. Approach from the posted dais floor,
            // never select the desktop/button as a shorter standing position.
            if(city&&p.getY()!=npc.station().getY())continue;
            if(!level.hasChunkAt(p)||level.getBlockState(p.below()).getCollisionShape(level,p.below()).isEmpty())continue;
            if(!level.noCollision(npc,new AABB(p.getX()+.2,p.getY()+.01,p.getZ()+.2,p.getX()+.8,p.getY()+1.8,p.getZ()+.8)))continue;
            Vec3 eye=Vec3.atBottomCenterOf(p).add(0,1.5,0);
            if(eye.distanceToSqr(contact)>6.25||eye.subtract(contact).dot(outward)<.3)continue;
            var hit=level.clip(new net.minecraft.world.level.ClipContext(eye,contact,net.minecraft.world.level.ClipContext.Block.COLLIDER,net.minecraft.world.level.ClipContext.Fluid.NONE,npc));
            if(hit.getType()!=HitResult.Type.MISS&&!hit.getBlockPos().equals(button))continue;options.add(p.immutable());
        }
        options.sort(Comparator.<BlockPos>comparingDouble(p->Vec3.atBottomCenterOf(p).distanceToSqr(Vec3.atCenterOf(button))).thenComparingDouble(p->npc.distanceToSqr(Vec3.atBottomCenterOf(p))));
        if("r15-staff".equals(System.getProperty("projectseele.regionalBuild","")))ProjectSeele.LOGGER.info("STAFF PATH REVIEW actor={} pos={} onGround={} candidates={}",npc.memberId(),npc.position(),npc.onGround(),options);
        for(var p:options){var path=npc.getNavigation().createPath(p,0);if(path!=null&&path.canReach())return p;}return null;
    }
    public static void tickTask(NervStaffEntity npc,UUID owner,String operation,int variant,BlockPos control,BlockPos approach,int ticks)
    {
        var level=(ServerLevel)npc.level();var player=level.getServer().getPlayerList().getPlayer(owner);
        boolean city=operation.equals("city_rise")||operation.equals("city_lower");
        if(ticks%40==0&&"r15-staff-controls".equals(System.getProperty("projectseele.regionalBuild","")))ProjectSeele.LOGGER.info("STAFF CONTROL TRACE actor={} pos={} target={} navDone={} onGround={} loaded={}",npc.memberId(),npc.position(),approach,npc.getNavigation().isDone(),npc.onGround(),EvaLogisticsDirector.status(level,variant).loaded());
        if(player==null||player.level()!=level||(StaffCommandBookR24.order(npc)==null&&player.distanceToSqr(npc)>48*48&&!(city&&StaffConversationR24.radioAllowed(player)))||!authorized(player)||!StaffAuthorityR25.allows(npc,operation)||ticks>300)
        {
            if(city&&player!=null)reply(player,npc,"城市按键操作已中止：通讯中断、权限改变或路径超时。");
            else StaffCommandBookR24.failed(npc,"按键操作已中止：通讯中断、权限改变或路径超时。");
            npc.finishTask();return;
        }
        if(!city&&ticks%20==0&&!EvaLogisticsDirector.status(level,variant).loaded())EvaLogisticsDirector.loadControlTarget(level,variant);
        if(npc.distanceToSqr(Vec3.atBottomCenterOf(approach))>.16)
        {
            if(npc.getNavigation().isDone()&&npc.distanceToSqr(Vec3.atBottomCenterOf(approach))<1.2)
                npc.getMoveControl().setWantedPosition(approach.getX()+.5,approach.getY(),approach.getZ()+.5,.65);
            else if(ticks%20==0)npc.getNavigation().moveTo(approach.getX()+.5,approach.getY(),approach.getZ()+.5,.9);
            return;
        }
        npc.getNavigation().stop();npc.getLookControl().setLookAt(control.getX()+.5,control.getY()+.5,control.getZ()+.5,30,30);
        float facing=(float)Math.toDegrees(Math.atan2(-(control.getX()+.5-npc.getX()),control.getZ()+.5-npc.getZ()));
        npc.setYRot(net.minecraft.util.Mth.approachDegrees(npc.getYRot(),facing,18));npc.yBodyRot=npc.getYRot();
        if(Math.abs(net.minecraft.util.Mth.wrapDegrees(facing-npc.getYRot()))>12)return;
        if(!city&&!EvaLogisticsDirector.status(level,variant).loaded()&&ticks<240)return;
        if(!npc.beginPressGesture(control))return;
        var state=level.getBlockState(control);
        if(!(state.getBlock() instanceof ButtonBlock)||state.getValue(ButtonBlock.POWERED))
        {StaffCommandBookR24.failed(npc,"按键状态已变化，操作未执行。");npc.finishTask();return;}
        npc.pressing();
        // Physical depression and the existing authoritative console dispatcher are
        // separate in the original player interaction hook. Invoke each exactly once.
        state.use(level,player,InteractionHand.MAIN_HAND,new BlockHitResult(Vec3.atCenterOf(control),net.minecraft.core.Direction.UP,control,false));
        boolean handled=NervOperationsConsole.handleUse(player,control);
        if(city)
        {
            var result=handled?NervOperationsConsole.lastOutcome(level,player,control):null;
            reply(player,npc,result!=null&&result.accepted()?"城市"+(operation.equals("city_rise")?"升起":"降下")+"指令已接受。":"城市控制未接受指令："+(result==null?"控制台无响应。":result.message()));
            ProjectSeele.LOGGER.info("STAFF CITY actor={} operation={} button={} accepted={}",npc.memberId(),operation,control,result!=null&&result.accepted());
            npc.finishTask();return;
        }
        var status=EvaLogisticsDirector.status(level,variant);
        var outcome=handled?NervOperationsConsole.lastOutcome(level,player,control):null;
        boolean accepted=outcome!=null&&outcome.accepted();
        if(StaffCommandBookR24.order(npc)==null||accepted&&!operation.equals("launch"))
            reply(player,npc,accepted?"按键已操作，指令被接受。当前："+stage(status.phase())+"。":"控制台没有接受本次指令。"+readinessHint(level,variant,operation));
        StaffCommandBookR24.pressed(npc,outcome);
        ProjectSeele.LOGGER.info("STAFF CONSOLE actor={} operation={} unit={} button={} requester={} phase={}",npc.memberId(),operation,variant,control,owner,status.phase());npc.finishTask();
    }
    public static void pilot(ServerPlayer player,TrainingPilotEntity pilot)
    {
        int v=pilot.getAssignedVariant();String line=switch(v){case 0->"明白。等待指令。";case 2->"准备好了。先确认轨道和供电，别把程序弄乱。";default->"我在。出击前请再确认一次同步状态。";};
        String stage=switch(pilot.getTrainingStage()){case TrainingPilotEntity.STAGE_IN_PLUG->"插入栓内，等待连接";case TrainingPilotEntity.STAGE_LINKED->"神经连接已建立";case TrainingPilotEntity.STAGE_STANDBY->"待命";default->"前往登机位置";};
        say(player,TrainingPilotEntity.pilotName(v),line+" 当前："+stage+"。");
    }
    private NervStaffDialogue() {}
}
