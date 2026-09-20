package com.projectseele.event;

import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.*;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.*;
import net.minecraft.world.BossEvent;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

@Mod.EventBusSubscriber(modid = ProjectSeele.MODID)
public final class TvCampaignDirector
{
    private static final TicketType<ChunkPos> TICKET = TicketType.create("tv_campaign_r24", Comparator.comparingLong(ChunkPos::toLong), 60);
    private static final Map<ServerLevel, ServerBossEvent> BARS = new WeakHashMap<>();
    private static final Map<ServerLevel, Integer> MISSING = new WeakHashMap<>();
    private record Site(Vec3 hero, Vec3 angel, float yaw) {}
    private static final Map<ServerLevel, Optional<Site>> SITES = new WeakHashMap<>();
    private static Vec3 vector(com.google.gson.JsonArray a) { return new Vec3(a.get(0).getAsDouble(), a.get(1).getAsDouble(), a.get(2).getAsDouble()); }
    private static Site site(ServerLevel level)
    {
        return SITES.computeIfAbsent(level, key -> {
            Path file = level.getServer().getWorldPath(LevelResource.ROOT).resolve("first_battle_site_r10.json");
            if (!Files.isRegularFile(file)) return Optional.empty();
            try
            {
                var json = JsonParser.parseString(Files.readString(file)).getAsJsonObject();
                if (!json.get("dimension").getAsString().equals(level.dimension().location().toString())) return Optional.empty();
                return Optional.of(new Site(vector(json.getAsJsonArray("hero")), vector(json.getAsJsonArray("angel")), json.get("yaw").getAsFloat()));
            }
            catch (Exception error) { ProjectSeele.LOGGER.error("TV campaign site rejected", error); return Optional.empty(); }
        }).orElse(null);
    }
    public static ServerLevel level(ServerPlayer player)
    { for (var level : player.server.getAllLevels()) if (site(level) != null) return level; return null; }

    public static String briefing(ServerPlayer player)
    {
        var level = level(player); if (level == null) return "本世界尚未配置 TV 作战区域。";
        var data = TvCampaignSavedData.get(level); var chapter = TvCampaignCatalog.at(data.chapter);
        String activity = data.active.isEmpty() ? "尚未下达本章指令" : switch (data.phase)
        { case "approach" -> "作战已接受，等待初号机抵达"; case "combat" -> "目标正在交战"; case "cancel" -> "正在解除目标登记"; default -> "记录暂停，请查看提示"; };
        return "TV 1995 · 第 " + chapter.episode() + " 话 / " + chapter.title() + "\n"
                + (chapter.playable() ? "可执行作战" : "后续制作档案 · 尚不可开始") + " · 已归档 " + data.completed.size() + " 章\n"
                + activity + "\n" + chapter.briefing() + "\n" + data.notice;
    }
    public static int begin(ServerPlayer player)
    {
        if (!NervStaffDialogue.authorized(player)) return message(player, "作战下达需要 NERV 通行权限。", false);
        var level = level(player); if (level == null) return message(player, "本世界尚未配置作战区域。", false);
        var data = TvCampaignSavedData.get(level); var chapter = TvCampaignCatalog.at(data.chapter);
        if (!data.active.isEmpty()) return message(player, "已有作战正在执行。" + briefing(player), false);
        if (!chapter.playable()) return message(player, "这一章尚未制作完成，不会越过它启动后面的使徒战。", false);
        var replay = FirstBattleSavedData.get(level);
        if (replay.active != null || replay.missionOwner != null) return message(player, "已有独立迎击或重播占用作战区，请先结束该行动。", false);
        if (chapter.id().equals("sachiel") && !FirstBattleMission.begin(player)) return 0;
        data.owner = player.getUUID(); data.active = chapter.id(); data.phase = "approach"; data.notice = ""; data.angel = null; data.lastPosition = null; data.setDirty();
        NervStaffDialogue.say(player, "葛城美里 · 作战通信", chapter.id().equals("sachiel")
                ? "初号机编入迎击。先到机库登机，整备完成后我来协调发射。不要一个人把所有步骤都扛下来。"
                : "这次的目标与上次不同。先观察它的攻击，再决定接近的方向。撤回路线也要记住。");
        return message(player, "作战已接受。" + chapter.briefing(), true);
    }
    public static int cancel(ServerPlayer player)
    {
        var level = level(player); if (level == null) return 0;
        var data = TvCampaignSavedData.get(level);
        if (data.active.isEmpty()) return message(player, "当前没有 TV 作战。", false);
        if (!player.getUUID().equals(data.owner) && !player.hasPermissions(2)) return message(player, "只能撤销自己的作战指令。", false);
        if (data.active.equals("sachiel")) FirstBattleMission.cancel(player);
        data.phase = "cancel"; data.setDirty();
        return message(player, "作战已撤销，不计通关。机体仍需按正常流程回收。", true);
    }
    private static int message(ServerPlayer player, String text, boolean accepted)
    { player.sendSystemMessage(Component.literal(text)); return accepted ? 1 : 0; }
    public static void firstBattleComplete(ServerLevel level, UUID owner, UUID angel)
    { complete(level, "sachiel", owner, angel); }
    public static void firstBattleBound(ServerLevel level, UUID owner, UUID angel)
    {
        var data = TvCampaignSavedData.get(level);
        if (data.active.equals("sachiel") && owner.equals(data.owner) && data.angel == null)
        { data.angel = angel; data.phase = "combat"; data.setDirty(); }
    }
    private static void complete(ServerLevel level, String chapter, UUID owner, UUID angel)
    {
        var data = TvCampaignSavedData.get(level);
        if (data.phase.equals("cancel") || !data.finish(chapter, owner, angel)) return;
        var player = level.getServer().getPlayerList().getPlayer(owner);
        if (player != null)
        {
            message(player, data.notice, true);
            NervStaffDialogue.say(player, "葛城美里 · 作战通信", "目标已确认消失。先别急着动，检查供电和机体状态，我们准备接你回来。");
        }
        ProjectSeele.LOGGER.info("TV CAMPAIGN completed={} owner={} target={}", chapter, owner, angel);
    }
    @SubscribeEvent public static void death(LivingDeathEvent event)
    {
        if (!(event.getEntity() instanceof ShamshelEntity angel) || !(angel.level() instanceof ServerLevel level)) return;
        var data = TvCampaignSavedData.get(level);
        if (angel.getUUID().equals(data.angel) && angel.getTags().contains("seele_tv_shamshel_r24")) complete(level, "shamshel", data.owner, angel.getUUID());
    }
    private static void load(ServerLevel level, BlockPos pos)
    {
        var chunk = new ChunkPos(pos); level.getChunkSource().addRegionTicket(TICKET, chunk, 2, chunk); level.getChunk(pos);
    }
    private static void pilotContinuity(ServerLevel level,TvCampaignSavedData data)
    {
        if(data.active.isEmpty()||data.owner==null)return;
        var player=level.getServer().getPlayerList().getPlayer(data.owner);
        if(player==null)return; // Logout detach must not overwrite the saved riding intent.
        if(player.level()!=level){data.resumePending=false;data.wasRiding=false;data.setDirty();return;}
        if(data.resumePending)
        {
            if(++data.resumeTicks>200)
            {data.resumePending=false;data.wasRiding=false;data.notice="驾驶连接未恢复，请检查原机体与插入栓后重新登机。";data.setDirty();return;}
            if(data.lastPosition!=null&&data.resumeTicks%10==1)load(level,data.lastPosition);
            var actor=level.getEntity(data.pilotEva);var capsule=level.getEntity(data.pilotPlug);
            if(!(actor instanceof EvaUnit01Entity eva)||!(capsule instanceof EntryPlugCarrierEntity plug))return;
            if(player.isPassenger())
            {data.resumePending=false;data.wasRiding=EvaPilotResolver.controlTarget(player)==eva;data.setDirty();return;}
            if(EvaLogisticsDirector.canonicalUnit(level,1)!=eva||EntryPlugDirector.canonical(level,1)!=plug
                    ||plug.getLinkedEva()!=eva||plug.getVehicle()!=eva||!plug.isLockedToEva()||!plug.isHatchFullySealed()
                    ||eva.getPilotEntity()!=null||plug.isVehicle()||player.distanceToSqr(eva)>128*128||!NervStaffDialogue.authorized(player))
            {data.resumePending=false;data.wasRiding=false;data.setDirty();return;}
            if(player.startRiding(plug,true))
            {
                player.fallDistance=0;plug.syncPilotPositionNow();level.getChunkSource().move(player);
                var packet=new net.minecraft.network.protocol.game.ClientboundSetPassengersPacket(plug);
                level.getChunkSource().broadcastAndSend(plug,packet);player.connection.send(packet);
                data.resumePending=false;data.wasRiding=true;data.setDirty();
                ProjectSeele.LOGGER.info("TV CAMPAIGN restored original riding chain pilot={} eva={} plug={}",data.owner,data.pilotEva,data.pilotPlug);
            }
            return;
        }
        var eva=EvaPilotResolver.controlTarget(player);
        boolean riding=eva!=null&&eva.getUnitVariant()==EvaUnit01Entity.UNIT_01&&!eva.isExperimentalUnit()
                &&player.getVehicle() instanceof EntryPlugCarrierEntity plug&&plug.getLinkedEva()==eva;
        if(riding)
        {
            var plug=(EntryPlugCarrierEntity)player.getVehicle();
            if(!eva.getUUID().equals(data.pilotEva)||!plug.getUUID().equals(data.pilotPlug))
            {data.pilotEva=eva.getUUID();data.pilotPlug=plug.getUUID();data.setDirty();}
        }
        if(data.wasRiding!=riding){data.wasRiding=riding;data.setDirty();}
    }
    @SubscribeEvent public static void protectReconnectingPilot(net.minecraftforge.event.entity.living.LivingAttackEvent event)
    {
        if(!(event.getEntity() instanceof ServerPlayer player)||!event.getSource().is(net.minecraft.tags.DamageTypeTags.IS_FALL))return;
        var data=TvCampaignSavedData.get(player.serverLevel());
        if(data.resumePending&&data.wasRiding&&player.getUUID().equals(data.owner)&&data.resumeTicks<=200)event.setCanceled(true);
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END) return;
        for (var level : event.getServer().getAllLevels())
        {
            Site site = site(level); if (site == null) continue;
            var data = TvCampaignSavedData.get(level);
            pilotContinuity(level,data);
            if(event.getServer().getTickCount()%10!=0)continue;
            var bar = BARS.computeIfAbsent(level, key -> new ServerBossEvent(Component.literal("TV 作战"), BossEvent.BossBarColor.RED, BossEvent.BossBarOverlay.PROGRESS));
            bar.removeAllPlayers();
            if (data.active.isEmpty()) continue;
            if (data.phase.equals("cancel"))
            {
                if (data.angel == null) { data.clear("行动已取消，本章可以重新接受。"); continue; }
                load(level, data.lastPosition == null ? BlockPos.containing(site.angel) : data.lastPosition);
                var entity = level.getEntity(data.angel);
                if (entity != null && entity.getTags().contains("seele_tv_shamshel_r24")) entity.discard();
                if (entity != null || !data.active.equals("shamshel")) { data.clear("行动已取消，本章可以重新接受。"); MISSING.remove(level); }
                else if (MISSING.merge(level, 1, Integer::sum) > 40) { data.clear("目标记录已解除，未计通关。"); MISSING.remove(level); }
                continue;
            }
            if (data.active.equals("sachiel"))
            {
                var first = FirstBattleSavedData.get(level);
                if (data.owner.equals(first.missionOwner))
                {
                    if (first.missionAngel != null && data.angel == null)
                    { data.angel = first.missionAngel; data.phase = "combat"; data.setDirty(); }
                }
                else if (first.active == null) data.clear("独立迎击已结束或被取消，未收到该章节的完成信号。");
                continue;
            }
            var player = event.getServer().getPlayerList().getPlayer(data.owner);
            if (player == null || player.level() != level) continue;
            bar.addPlayer(player);
            if (data.angel == null)
            {
                var eva = EvaPilotResolver.controlTarget(player);
                double distance = (eva == null ? player.position() : eva.position()).distanceTo(site.hero);
                bar.setName(Component.literal("第4使徒迎击 · 前往东北大道 / " + Math.round(distance) + " m")); bar.setProgress(1);
                if (eva == null || eva.getUnitVariant() != EvaUnit01Entity.UNIT_01 || eva.isExperimentalUnit()
                        || eva.isNervLogisticsLocked() || !eva.isPoweredOn() || distance > 90) continue;
                load(level, BlockPos.containing(site.angel));
                if(!level.isPositionEntityTicking(BlockPos.containing(site.angel)))continue;
                if(!level.getEntitiesOfClass(ShamshelEntity.class,new net.minecraft.world.phys.AABB(site.angel,site.angel).inflate(180),
                        q->q.isAlive()&&q.getTags().contains("seele_tv_shamshel_r24")).isEmpty())
                {bar.setName(Component.literal("战区仍有未归档目标，请先检查原目标"));continue;}
                var angel = ModEntities.SHAMSHEL.get().create(level); if (angel == null) continue;
                angel.moveTo(site.angel.x, site.angel.y + 4, site.angel.z, site.yaw + 180, 0);
                angel.yBodyRot = angel.yHeadRot = site.yaw + 180; angel.setPersistenceRequired(); angel.addTag("seele_tv_shamshel_r24"); angel.setTarget(eva);
                if (!level.noCollision(angel, angel.getBoundingBox())) { bar.setName(Component.literal("迎击区域被占用，请清空后继续")); continue; }
                if (!level.addFreshEntity(angel)) continue;
                data.angel = angel.getUUID(); data.lastPosition = angel.blockPosition(); data.phase = "combat"; data.setDirty();
                message(player, "目标确认。光鞭将先蓄势再横扫，注意两侧退路。", true);
            }
            load(level, data.lastPosition == null ? BlockPos.containing(site.angel) : data.lastPosition);
            if (level.getEntity(data.angel) instanceof ShamshelEntity angel)
            {
                MISSING.remove(level);
                if (!angel.blockPosition().equals(data.lastPosition)) { data.lastPosition = angel.blockPosition(); data.setDirty(); }
                var eva = EvaPilotResolver.controlTarget(player); if (eva != null) angel.setTarget(eva);
                float field = angel.getAtField();
                bar.setName(Component.literal("第4使徒 夏姆榭尔 · " + (field > 0 ? "AT 力场 " + Math.round(field) : "核心 " + Math.round(100 * angel.getHealth() / angel.getMaxHealth()) + "%")));
                bar.setProgress(Math.max(0, Math.min(1, field > 0 ? field / 700 : angel.getHealth() / angel.getMaxHealth())));
            }
            else if (MISSING.merge(level, 1, Integer::sum) > 40)
            { data.clear("目标实体已丢失。本章未完成；确认世界状态后可重新接受作战。"); MISSING.remove(level); }
        }
    }
    @SubscribeEvent public static void commands(RegisterCommandsEvent event)
    {
        event.getDispatcher().register(Commands.literal("seele").then(Commands.literal("tv")
                .then(Commands.literal("status").executes(c -> message(c.getSource().getPlayerOrException(), briefing(c.getSource().getPlayerOrException()), true)))
                .then(Commands.literal("begin").executes(c -> begin(c.getSource().getPlayerOrException())))
                .then(Commands.literal("cancel").executes(c -> cancel(c.getSource().getPlayerOrException())))));
    }
    private TvCampaignDirector() {}
}
