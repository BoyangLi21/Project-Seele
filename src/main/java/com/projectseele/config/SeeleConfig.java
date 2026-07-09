package com.projectseele.config;

import net.minecraftforge.common.ForgeConfigSpec;

/**
 * All balance numbers live here so tuning never needs a rebuild. Defaults
 * mirror the Phase-1 table in CLAUDE.md; change them in
 * config/projectseele-common.toml (numbers) or -client.toml (visual toggles).
 */
public final class SeeleConfig
{
    public static final ForgeConfigSpec COMMON_SPEC;
    public static final ForgeConfigSpec CLIENT_SPEC;

    // ----- common: Ramiel -----
    public static final ForgeConfigSpec.DoubleValue RAMIEL_MAX_HEALTH;
    public static final ForgeConfigSpec.DoubleValue RAMIEL_ARMOR;
    public static final ForgeConfigSpec.DoubleValue RAMIEL_AT_FIELD_MULTIPLIER;
    public static final ForgeConfigSpec.DoubleValue BEAM_DAMAGE;
    public static final ForgeConfigSpec.DoubleValue BEAM_EXPLOSION_RADIUS;
    public static final ForgeConfigSpec.IntValue BEAM_CHARGE_TICKS;
    public static final ForgeConfigSpec.IntValue BEAM_CHARGE_TICKS_ENRAGED;
    public static final ForgeConfigSpec.IntValue BEAM_COOLDOWN_TICKS;
    public static final ForgeConfigSpec.DoubleValue BEAM_RANGE;
    public static final ForgeConfigSpec.DoubleValue DRILL_DAMAGE;
    public static final ForgeConfigSpec.IntValue DRILL_COOLDOWN_TICKS;
    public static final ForgeConfigSpec.BooleanValue ALARM_ENABLED;

    // ----- common: positron rifle -----
    public static final ForgeConfigSpec.DoubleValue RIFLE_DAMAGE;
    public static final ForgeConfigSpec.IntValue RIFLE_COOLDOWN_TICKS;
    public static final ForgeConfigSpec.DoubleValue RIFLE_RANGE;

    // ----- common: EVA Unit-01 -----
    public static final ForgeConfigSpec.DoubleValue EVA_MAX_HEALTH;

    // ----- common: positron sniper cannon (EVA weapon) -----
    public static final ForgeConfigSpec.IntValue CANNON_CHARGE_TICKS;
    public static final ForgeConfigSpec.DoubleValue CANNON_RANGE;
    public static final ForgeConfigSpec.IntValue CANNON_COOLDOWN_TICKS;
    public static final ForgeConfigSpec.DoubleValue CANNON_MOB_DAMAGE;
    public static final ForgeConfigSpec.DoubleValue CANNON_CORE_DAMAGE;
    public static final ForgeConfigSpec.DoubleValue CANNON_EXPLOSION_RADIUS;

    // ----- client -----
    public static final ForgeConfigSpec.BooleanValue ALARM_VIGNETTE;
    public static final ForgeConfigSpec.DoubleValue FX_INTENSITY;
    public static final ForgeConfigSpec.DoubleValue COCKPIT_ARM_SCALE;
    public static final ForgeConfigSpec.DoubleValue COCKPIT_ARM_Y;
    public static final ForgeConfigSpec.DoubleValue COCKPIT_ARM_Z;

    static
    {
        ForgeConfigSpec.Builder common = new ForgeConfigSpec.Builder();

        common.push("ramiel");
        RAMIEL_MAX_HEALTH = common
                .comment("Ramiel max health.")
                .defineInRange("maxHealth", 350.0D, 1.0D, 10000.0D);
        RAMIEL_ARMOR = common
                .comment("Ramiel armor points.")
                .defineInRange("armor", 6.0D, 0.0D, 30.0D);
        RAMIEL_AT_FIELD_MULTIPLIER = common
                .comment("Ramiel A.T. Field durability as a multiple of its real health.",
                        "Only EVA melee can damage this pool while the core is sealed.")
                .defineInRange("atFieldHealthMultiplier", 5.0D, 0.0D, 20.0D);
        BEAM_DAMAGE = common
                .comment("Positron beam damage per hit. Nuke-grade: two hits cripple an EVA.")
                .defineInRange("beamDamage", 120.0D, 0.0D, 1000.0D);
        BEAM_EXPLOSION_RADIUS = common
                .comment("Explosion radius at the beam impact point.")
                .defineInRange("beamExplosionRadius", 28.0D, 1.0D, 48.0D);
        BEAM_CHARGE_TICKS = common
                .comment("Beam charge-up time in ticks (phase one).")
                .defineInRange("beamChargeTicks", 50, 5, 400);
        BEAM_CHARGE_TICKS_ENRAGED = common
                .comment("Beam charge-up time in ticks while below 40% health.")
                .defineInRange("beamChargeTicksEnraged", 30, 5, 400);
        BEAM_COOLDOWN_TICKS = common
                .comment("Cooldown between beam shots in ticks.")
                .defineInRange("beamCooldownTicks", 90, 10, 2000);
        BEAM_RANGE = common
                .comment("Beam sniping range in blocks.")
                .defineInRange("beamRange", 64.0D, 8.0D, 256.0D);
        DRILL_DAMAGE = common
                .comment("Drill damage per hit (one hit every 10 ticks inside the column).")
                .defineInRange("drillDamage", 4.0D, 0.0D, 1000.0D);
        DRILL_COOLDOWN_TICKS = common
                .comment("Cooldown between drill descents in ticks.")
                .defineInRange("drillCooldownTicks", 300, 20, 6000);
        ALARM_ENABLED = common
                .comment("Whether Angels acquiring a player target raises the server-wide alarm.")
                .define("alarmEnabled", true);
        common.pop();

        common.push("positron_rifle");
        RIFLE_DAMAGE = common
                .comment("Positron rifle damage per shot.")
                .defineInRange("damage", 16.0D, 0.0D, 1000.0D);
        RIFLE_COOLDOWN_TICKS = common
                .comment("Positron rifle cooldown in ticks.")
                .defineInRange("cooldownTicks", 25, 1, 1200);
        RIFLE_RANGE = common
                .comment("Positron rifle hitscan range in blocks.")
                .defineInRange("range", 96.0D, 8.0D, 256.0D);
        common.pop();

        common.push("eva_unit01");
        EVA_MAX_HEALTH = common
                .comment("EVA Unit-01 max health. Tuned to survive two nuke beams and die to the third.")
                .defineInRange("maxHealth", 300.0D, 1.0D, 10000.0D);
        common.pop();

        common.push("positron_cannon");
        CANNON_CHARGE_TICKS = common
                .comment("Hold-to-charge time in ticks before the sniper cannon can fire.")
                .defineInRange("chargeTicks", 60, 5, 400);
        CANNON_RANGE = common
                .comment("Sniper cannon hitscan range in blocks.")
                .defineInRange("range", 512.0D, 32.0D, 1024.0D);
        CANNON_COOLDOWN_TICKS = common
                .comment("Cooldown after a shot in ticks.")
                .defineInRange("cooldownTicks", 200, 1, 6000);
        CANNON_MOB_DAMAGE = common
                .comment("Damage against ordinary targets.")
                .defineInRange("mobDamage", 40.0D, 0.0D, 1000.0D);
        CANNON_CORE_DAMAGE = common
                .comment("Damage when striking an exposed Angel core. Default kills Ramiel in two core",
                        "hits with margin left for its armor reduction.")
                .defineInRange("coreDamage", 210.0D, 0.0D, 100000.0D);
        CANNON_EXPLOSION_RADIUS = common
                .comment("Explosion radius at the cannon impact point.")
                .defineInRange("explosionRadius", 18.0D, 0.0D, 32.0D);
        common.pop();

        COMMON_SPEC = common.build();

        ForgeConfigSpec.Builder client = new ForgeConfigSpec.Builder();
        client.push("screen_effects");
        ALARM_VIGNETTE = client
                .comment("Show the pulsing red vignette while the Angel alarm is active.")
                .define("alarmVignette", true);
        FX_INTENSITY = client
                .comment("Global brightness/opacity multiplier for beam and explosion effects (0 disables cross explosions).")
                .defineInRange("fxIntensity", 1.0D, 0.0D, 1.0D);
        COCKPIT_ARM_SCALE = client
                .comment("First-person real-bone EVA arm-rig scale.")
                .defineInRange("cockpitRigScale", 0.10D, 0.02D, 0.30D);
        COCKPIT_ARM_Y = client
                .comment("First-person real-bone EVA arm-rig vertical offset.")
                .defineInRange("cockpitRigY", -2.65D, -4.0D, 4.0D);
        COCKPIT_ARM_Z = client
                .comment("First-person real-bone EVA arm-rig depth offset.")
                .defineInRange("cockpitRigZ", -1.65D, -4.0D, 2.0D);
        client.pop();
        CLIENT_SPEC = client.build();
    }

    private SeeleConfig() {}
}
