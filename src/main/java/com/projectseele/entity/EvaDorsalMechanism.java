package com.projectseele.entity;

import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.nbt.CompoundTag;
import java.util.Map;
import java.util.WeakHashMap;

/** The socket is driven by the physical plug director, including reverse and recovery travel. */
public final class EvaDorsalMechanism
{
    private static final EntityDataAccessor<Float> OPEN = SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> BOW = SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.FLOAT);
    private static final Map<EvaUnit01Entity, View> VIEWS = new WeakHashMap<>();
    public static boolean bootstrap() { return true; }
    private static final class View
    {
        final EvaPoseSignalClock open = new EvaPoseSignalClock(), bow = new EvaPoseSignalClock();
        float lastOpen = -1, lastBow = -1;
    }
    public static void define(SynchedEntityData data) { data.define(OPEN, 0F); data.define(BOW, 0F); }
    public static void set(EvaUnit01Entity eva, float open, float bow)
    {
        if (eva.level().isClientSide) return;
        eva.getEntityData().set(OPEN, Math.max(0, Math.min(1, open)));
        eva.getEntityData().set(BOW, Math.max(0, Math.min(1, bow)));
    }
    public static float smooth(float x) { x = Math.max(0, Math.min(1, x)); return x*x*x*(x*(x*6-15)+10); }
    public static void prepare(EvaUnit01Entity eva, int ticks)
    { set(eva, smooth((ticks-12)/22F), smooth(ticks/22F)); }
    public static void seal(EvaUnit01Entity eva, int ticks)
    { set(eva, 1-smooth(ticks/26F), 1-smooth((ticks-30)/26F)); }
    public static float open(EvaUnit01Entity eva) { return sample(eva, true); }
    public static float bow(EvaUnit01Entity eva) { return sample(eva, false); }
    public static boolean eyesEnabled(EvaUnit01Entity eva)
    { return eva.isPoweredOn() && open(eva) < .001F && bow(eva) < .001F; }
    private static float sample(EvaUnit01Entity eva, boolean opening)
    {
        float value = eva.getEntityData().get(opening ? OPEN : BOW);
        if (!eva.level().isClientSide) return value;
        View view = VIEWS.computeIfAbsent(eva, e -> new View());
        if (opening && value != view.lastOpen) { view.open.accept(value, false, false); view.lastOpen=value; }
        if (!opening && value != view.lastBow) { view.bow.accept(value, false, false); view.lastBow=value; }
        return (opening ? view.open : view.bow).sample(FirstBattleSignals.clientFrameTime());
    }
    public static void save(EvaUnit01Entity eva, CompoundTag tag)
    { tag.putFloat("DorsalOpen", eva.getEntityData().get(OPEN)); tag.putFloat("DorsalBow", eva.getEntityData().get(BOW)); }
    public static void load(EvaUnit01Entity eva, CompoundTag tag)
    { set(eva, tag.getFloat("DorsalOpen"), tag.getFloat("DorsalBow")); }
    private EvaDorsalMechanism() {}
}
