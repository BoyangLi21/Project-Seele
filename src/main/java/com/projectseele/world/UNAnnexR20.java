package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.NervHangarDoorEntity;
import com.projectseele.entity.NervCarrierPlatformEntity;
import com.projectseele.registry.ModEntities;
import com.projectseele.registry.ModItems;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.*;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.*;
import net.minecraftforge.event.*;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.Files;
import java.util.*;

/** Independent wet-cell controls; commissioning the future UN-01 is separate. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class UNAnnexR20
{
    public static final Vec3 HOME=new Vec3(6282.5,77,-6205.5),DOOR=new Vec3(6282.5,77,-6135.5);
    private static final BlockPos MIN=new BlockPos(6266,77,-6226),MAX=new BlockPos(6298,120,-6137);
    private static final BlockPos[] BUTTONS={new BlockPos(6234,78,-6141),new BlockPos(6238,78,-6141),new BlockPos(6246,78,-6141)};
    private static final AABB PIT=new AABB(MIN,MAX.offset(1,1,1)),SWEEP=new AABB(6248,77,-6137,6318,142,-6134);
    private static final TicketType<ChunkPos> TICKET=TicketType.create("seele_un01_annex",Comparator.comparingLong(ChunkPos::toLong),100);
    private static final Map<ServerLevel,UUID> HOISTS=new WeakHashMap<>();
    private static final int LAYER=33*90,TOTAL=LAYER*44;
    public static final class State extends SavedData
    {
        public MilitaryR07Director.Phase phase=MilitaryR07Director.Phase.WET;public int cursor;
        static State load(CompoundTag t){State s=new State();try{s.phase=MilitaryR07Director.Phase.valueOf(t.getString("Phase"));}catch(Exception ignored){}s.cursor=t.getInt("Cursor");return s;}
        @Override public CompoundTag save(CompoundTag t){t.putString("Phase",phase.name());t.putInt("Cursor",cursor);return t;}
    }
    public static State state(ServerLevel l){return l.getDataStorage().computeIfAbsent(State::load,State::new,"projectseele_un01_annex_r20");}
    public static boolean installed(ServerLevel l){return Files.isRegularFile(l.getServer().getWorldPath(LevelResource.ROOT).resolve("un01_annex_r20.json"));}
    private static boolean card(Player p)
    {
        if(p==null||p.isCreative())return true;
        for(int i=0;i<p.getInventory().getContainerSize();i++){var s=p.getInventory().getItem(i);if(s.is(ModItems.NERV_EMPLOYEE_CARD.get())||s.is(ModItems.TERMINAL_DOGMA_ACCESS_CARD.get()))return true;}return false;
    }
    private static boolean occupied(ServerLevel l){return !l.getEntities((net.minecraft.world.entity.Entity)null,SWEEP,e->e.isAlive()&&!e.isSpectator()&&!(e instanceof NervHangarDoorEntity)&&!(e instanceof NervCarrierPlatformEntity)).isEmpty();}
    public static String request(ServerLevel l,String action,Player p)
    {
        if(!installed(l))return "此存档未安装 UN-01 试验舱";if(!card(p))return "需要工作人员身份卡";State s=state(l);
        switch(action)
        {
            case "drain" -> {if(s.phase!=MilitaryR07Director.Phase.WET&&s.phase!=MilitaryR07Director.Phase.FILLING)return "当前无需排液";s.phase=MilitaryR07Director.Phase.DRAINING;s.cursor=0;}
            case "door" ->
            {
                if(s.phase==MilitaryR07Director.Phase.DRY){s.phase=MilitaryR07Director.Phase.OPENING;s.cursor=0;}
                else if(s.phase==MilitaryR07Director.Phase.OPEN){if(occupied(l))return "舱门区域有人员或载具";s.phase=MilitaryR07Director.Phase.CLOSING;}
                else return "请等待排液或舱门动作完成";
            }
            case "fill" -> {if(s.phase!=MilitaryR07Director.Phase.DRY)return "请先关闭舱门";if(!l.getEntitiesOfClass(Player.class,PIT,q->!q.isSpectator()).isEmpty())return "请先离开 LCL 试验区";s.phase=MilitaryR07Director.Phase.FILLING;s.cursor=0;}
            default -> {return status(s);}
        }
        s.setDirty();return status(s);
    }
    public static String status(State s)
    {
        String label=switch(s.phase){case WET->"LCL 保管";case DRAINING->"排液中";case DRY->"干燥，舱门关闭";case OPENING->"舱门开启中";case OPEN->"允许进出";case CLOSING->"舱门关闭中";case FILLING->"注液中";};return "EVA-UN-01 试验舱 · "+label;
    }
    private static void tickets(ServerLevel l,boolean enabled)
    {
        for(int x=6224>>4;x<=6340>>4;x++)for(int z=-6288>>4;z<=-6135>>4;z++){var p=new ChunkPos(x,z);if(enabled)l.getChunkSource().addRegionTicket(TICKET,p,2,p);else l.getChunkSource().removeRegionTicket(TICKET,p,2,p);}
    }
    private static void seal(ServerLevel l,boolean closed)
    {
        for(BlockPos p:BlockPos.betweenClosed(6266,77,-6136,6298,141,-6136)){var s=l.getBlockState(p);if(s.isAir()||s.is(Blocks.BARRIER))l.setBlock(p,(closed?Blocks.BARRIER:Blocks.AIR).defaultBlockState(),2);}
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e)
    {
        if(e.phase!=TickEvent.Phase.END)return;var l=e.getServer().getLevel(FacilitySchemaV2.DIMENSION);if(l==null||!installed(l))return;var s=state(l);boolean active=s.phase==MilitaryR07Director.Phase.DRAINING||s.phase==MilitaryR07Director.Phase.FILLING||s.phase==MilitaryR07Director.Phase.OPENING||s.phase==MilitaryR07Director.Phase.CLOSING;
        if(active){tickets(l,true);l.resetEmptyTime();}if(!l.hasChunkAt(BUTTONS[0]))return;
        boolean open=s.phase==MilitaryR07Director.Phase.OPEN||s.phase==MilitaryR07Director.Phase.OPENING;NervHangarDoorEntity.reconcile(l,3,DOOR,open);
        if(s.phase==MilitaryR07Director.Phase.DRAINING||s.phase==MilitaryR07Director.Phase.FILLING)
        {
            var liquid=com.projectseele.registry.ModBlocks.LCL_BLOCK.get();
            for(int i=0;i<512&&s.cursor<TOTAL;i++,s.cursor++)
            {
                int layer=s.cursor/LAYER,within=s.cursor%LAYER;var p=new BlockPos(MIN.getX()+within%33,s.phase==MilitaryR07Director.Phase.DRAINING?MAX.getY()-layer:MIN.getY()+layer,MIN.getZ()+within/33);var old=l.getBlockState(p);
                if(s.phase==MilitaryR07Director.Phase.DRAINING&&old.is(liquid))l.setBlock(p,Blocks.AIR.defaultBlockState(),18);
                else if(s.phase==MilitaryR07Director.Phase.FILLING&&old.isAir())l.setBlock(p,liquid.defaultBlockState(),18);
            }
            if(s.cursor==TOTAL){s.phase=s.phase==MilitaryR07Director.Phase.DRAINING?MilitaryR07Director.Phase.DRY:MilitaryR07Director.Phase.WET;tickets(l,false);}s.setDirty();
        }
        else if(s.phase==MilitaryR07Director.Phase.OPENING||s.phase==MilitaryR07Director.Phase.CLOSING)
        {
            var doors=l.getEntitiesOfClass(NervHangarDoorEntity.class,new AABB(DOOR,DOOR).inflate(3),d->d.getVariant()==3);
            if(!doors.isEmpty())
            {
                float t=doors.get(0).getOpenProgress(1);
                if(s.phase==MilitaryR07Director.Phase.OPENING&&t>=.99){seal(l,false);s.phase=MilitaryR07Director.Phase.OPEN;tickets(l,false);s.setDirty();}
                else if(s.phase==MilitaryR07Director.Phase.CLOSING){if(occupied(l)){s.phase=MilitaryR07Director.Phase.OPENING;s.setDirty();}else{seal(l,true);if(t<=.001){s.phase=MilitaryR07Director.Phase.DRY;tickets(l,false);s.setDirty();}}}
            }
        }
        // Reuse the already reviewed mechanical hoist, with real supporting
        // beams; no placeholder airframe is created while model work is paused.
        if(l.getGameTime()%20==0)
        {
            NervCarrierPlatformEntity crane=HOISTS.containsKey(l)&&l.getEntity(HOISTS.get(l)) instanceof NervCarrierPlatformEntity c?c:null;
            if(crane==null){crane=ModEntities.NERV_CARRIER_PLATFORM.get().create(l);if(crane!=null){crane.configurePlugCrane(1,-18);crane.moveControlled(6282.5,150,-6217.5);l.addFreshEntity(crane);HOISTS.put(l,crane.getUUID());}}
        }
    }
    @SubscribeEvent public static void interact(PlayerInteractEvent.RightClickBlock e)
    {
        if(!(e.getLevel() instanceof ServerLevel l)||!installed(l))return;
        for(int i=0;i<BUTTONS.length;i++)if(e.getPos().equals(BUTTONS[i])){e.setCanceled(true);e.setCancellationResult(net.minecraft.world.InteractionResult.SUCCESS);if(e.getHand()==net.minecraft.world.InteractionHand.MAIN_HAND)e.getEntity().displayClientMessage(Component.literal(request(l,new String[]{"drain","door","fill"}[i],e.getEntity())),true);return;}
    }
    @SubscribeEvent public static void commands(RegisterCommandsEvent e)
    {
        var branch=net.minecraft.commands.Commands.literal("un01");
        for(String a:new String[]{"status","drain","door","fill"})branch.then(net.minecraft.commands.Commands.literal(a).executes(c->{var l=c.getSource().getServer().getLevel(FacilitySchemaV2.DIMENSION);String text=l==null?"地下维度未加载":request(l,a,c.getSource().getPlayerOrException());c.getSource().sendSuccess(()->Component.literal(text),false);return 1;}));
        e.getDispatcher().register(net.minecraft.commands.Commands.literal("seele").requires(s->s.hasPermission(2)).then(net.minecraft.commands.Commands.literal("military").then(branch)));
    }
    private UNAnnexR20(){}
}
