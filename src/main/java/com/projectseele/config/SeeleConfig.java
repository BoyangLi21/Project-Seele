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
    public static final ForgeConfigSpec.DoubleValue EVA_RIFLE_DAMAGE;
    public static final ForgeConfigSpec.DoubleValue EVA_RIFLE_RANGE;
    public static final ForgeConfigSpec.IntValue EVA_RIFLE_INTERVAL_TICKS;

    // ----- common: positron sniper cannon (EVA weapon) -----
    public static final ForgeConfigSpec.IntValue CANNON_CHARGE_TICKS;
    public static final ForgeConfigSpec.DoubleValue CANNON_RANGE;
    public static final ForgeConfigSpec.IntValue CANNON_COOLDOWN_TICKS;
    public static final ForgeConfigSpec.DoubleValue CANNON_MOB_DAMAGE;
    public static final ForgeConfigSpec.DoubleValue CANNON_CORE_DAMAGE;
    public static final ForgeConfigSpec.DoubleValue CANNON_EXPLOSION_RADIUS;
    public static final ForgeConfigSpec.DoubleValue CANNON_BLAST_DAMAGE;
    public static final ForgeConfigSpec.IntValue CANNON_TERRAIN_RADIUS;
    public static final ForgeConfigSpec.IntValue CANNON_CRATER_DEPTH;

    // ----- common: strategic explosions -----
    public static final ForgeConfigSpec.IntValue N2_ARM_TICKS;
    public static final ForgeConfigSpec.IntValue STRATEGIC_BLOCKS_PER_TICK;
    // ----- common: LCL -----
    public static final ForgeConfigSpec.DoubleValue LCL_HEAL_AMOUNT;
    public static final ForgeConfigSpec.IntValue LCL_HEAL_INTERVAL_TICKS;
    public static final ForgeConfigSpec.BooleanValue LCL_ITEMS_PERSIST;

    // ----- common: EVA power -----
    public static final ForgeConfigSpec.IntValue EVA_POWER_CAPACITY_TICKS;
    public static final ForgeConfigSpec.IntValue UMBILICAL_RANGE;
    public static final ForgeConfigSpec.DoubleValue UMBILICAL_REPAIR_PER_SECOND;

    // ----- common: EVA pilot synchronization -----
    public static final ForgeConfigSpec.DoubleValue EVA_SYNC_INITIAL;
    public static final ForgeConfigSpec.DoubleValue EVA_SYNC_MAX;
    public static final ForgeConfigSpec.DoubleValue EVA_SYNC_DRIVE_GAIN_PER_MINUTE;
    public static final ForgeConfigSpec.DoubleValue EVA_SYNC_ANGEL_KILL_GAIN;
    public static final ForgeConfigSpec.DoubleValue EVA_SYNC_MAX_MOBILITY_BONUS;
    public static final ForgeConfigSpec.DoubleValue EVA_SYNC_MAX_ATTACK_SPEED_BONUS;
    public static final ForgeConfigSpec.DoubleValue EVA_SYNC_FEEDBACK_THRESHOLD;
    public static final ForgeConfigSpec.DoubleValue EVA_SYNC_MAX_FEEDBACK_FRACTION;

    // ----- common: EVA Unit-01 berserk -----
    public static final ForgeConfigSpec.IntValue EVA_BERSERK_DURATION_TICKS;
    public static final ForgeConfigSpec.IntValue EVA_BERSERK_RECOVERY_TICKS;
    public static final ForgeConfigSpec.DoubleValue EVA_BERSERK_HEALTH_THRESHOLD;
    public static final ForgeConfigSpec.DoubleValue EVA_BERSERK_SYNC_THRESHOLD;
    public static final ForgeConfigSpec.DoubleValue EVA_BERSERK_DAMAGE_MULTIPLIER;
    public static final ForgeConfigSpec.IntValue EVA_BERSERK_TARGET_RANGE;

    // ----- common: EVA armament logistics -----
    public static final ForgeConfigSpec.BooleanValue EVA_ARMAMENT_RACK_ENFORCES_LOADOUT;

    // ----- client -----
    public static final ForgeConfigSpec.BooleanValue ALARM_VIGNETTE;
    public static final ForgeConfigSpec.DoubleValue FX_INTENSITY;

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

        common.push("eva_pallet_smg");
        EVA_RIFLE_DAMAGE = common
                .comment("Damage per EVA pallet-SMG pulse. Angel A.T. Fields still block it completely.")
                .defineInRange("damage", 22.0D, 0.0D, 10000.0D);
        EVA_RIFLE_RANGE = common
                .comment("Pallet-SMG hitscan range in blocks.")
                .defineInRange("range", 192.0D, 16.0D, 1024.0D);
        EVA_RIFLE_INTERVAL_TICKS = common
                .comment("Minimum ticks between automatic pallet-SMG pulses.")
                .defineInRange("intervalTicks", 3, 1, 40);
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
                .comment("Immediate living-target blast radius at the cannon impact point.")
                .defineInRange("explosionRadius", 36.0D, 0.0D, 96.0D);
        CANNON_BLAST_DAMAGE = common
                .comment("Maximum immediate blast damage at ground zero (separate from the core ray).")
                .defineInRange("blastDamage", 160.0D, 0.0D, 100000.0D);
        CANNON_TERRAIN_RADIUS = common
                .comment("Radius of the staged mountain-carving crater. N2 uses exactly three times this radius.")
                .defineInRange("terrainRadius", 64, 8, 192);
        CANNON_CRATER_DEPTH = common
                .comment("Depth of the staged cannon crater. N2 uses exactly three times this depth.")
                .defineInRange("craterDepth", 32, 4, 128);
        common.pop();

        common.push("strategic_explosions");
        N2_ARM_TICKS = common
                .comment("Continuous use-key hold required to arm the EVA-carried N2 self-destruct.")
                .defineInRange("n2ArmTicks", 100, 20, 400);
        STRATEGIC_BLOCKS_PER_TICK = common
                .comment("Global terrain-edit budget for staged cannon/N2 craters. Lower values reduce tick spikes.")
                .defineInRange("blocksPerTick", 2048, 128, 20000);
        common.pop();

        common.push("lcl");
        LCL_HEAL_AMOUNT = common
                .comment("Health restored to players on each LCL recovery pulse. Set to zero to disable healing.")
                .defineInRange("healAmount", 1.0D, 0.0D, 20.0D);
        LCL_HEAL_INTERVAL_TICKS = common
                .comment("Ticks between LCL recovery pulses. Default 40 ticks is one health point every two seconds.")
                .defineInRange("healIntervalTicks", 40, 1, 1200);
        LCL_ITEMS_PERSIST = common
                .comment("Prevent dropped items submerged in LCL from expiring while they remain in the fluid.")
                .define("itemsPersist", true);
        common.pop();

        common.push("eva_power");
        EVA_POWER_CAPACITY_TICKS = common
                .comment("Internal EVA battery capacity after disconnecting from external power. 6000 ticks is five minutes.")
                .defineInRange("capacityTicks", 6000, 200, 72000);
        UMBILICAL_RANGE = common
                .comment("Maximum block distance from an EVA to a loaded umbilical power pylon.")
                .defineInRange("umbilicalRange", 32, 4, 128);
        UMBILICAL_REPAIR_PER_SECOND = common
                .comment("Hull health restored each second while connected to an umbilical pylon.")
                .defineInRange("repairPerSecond", 1.0D, 0.0D, 20.0D);
        common.pop();

        common.push("eva_synchronization");
        EVA_SYNC_INITIAL = common
                .comment("Initial pilot synchronization percentage and the no-bonus response baseline.")
                .defineInRange("initial", 40.0D, 0.0D, 100.0D);
        EVA_SYNC_MAX = common
                .comment("Maximum persistent pilot synchronization percentage.")
                .defineInRange("maximum", 100.0D, 1.0D, 100.0D);
        EVA_SYNC_DRIVE_GAIN_PER_MINUTE = common
                .comment("Synchronization gained for each active minute in an entry plug.")
                .defineInRange("driveGainPerMinute", 0.25D, 0.0D, 10.0D);
        EVA_SYNC_ANGEL_KILL_GAIN = common
                .comment("Synchronization gained when the pilot deals the killing blow to an Angel.")
                .defineInRange("angelKillGain", 2.5D, 0.0D, 25.0D);
        EVA_SYNC_MAX_MOBILITY_BONUS = common
                .comment("Fractional EVA movement-speed bonus at maximum synchronization. 0.25 is +25 percent.")
                .defineInRange("maxMobilityBonus", 0.25D, 0.0D, 1.0D);
        EVA_SYNC_MAX_ATTACK_SPEED_BONUS = common
                .comment("Fractional melee and pallet-rifle response bonus at maximum synchronization.")
                .defineInRange("maxAttackSpeedBonus", 0.25D, 0.0D, 1.0D);
        EVA_SYNC_FEEDBACK_THRESHOLD = common
                .comment("Synchronization percentage above which real hull damage feeds back into the pilot.")
                .defineInRange("feedbackThreshold", 60.0D, 0.0D, 100.0D);
        EVA_SYNC_MAX_FEEDBACK_FRACTION = common
                .comment("Fraction of actual hull damage transferred to the pilot at maximum synchronization.")
                .defineInRange("maxFeedbackFraction", 0.35D, 0.0D, 1.0D);
        common.pop();

        common.push("eva_berserk");
        EVA_BERSERK_DURATION_TICKS = common
                .comment("Autonomous Unit-01 berserk duration. 900 ticks is 45 seconds.")
                .defineInRange("durationTicks", 900, 20, 7200);
        EVA_BERSERK_RECOVERY_TICKS = common
                .comment("Forced shutdown after berserk. 6000 ticks is five minutes.")
                .defineInRange("recoveryTicks", 6000, 20, 72000);
        EVA_BERSERK_HEALTH_THRESHOLD = common
                .comment("Hull fraction below which a depleted Unit-01 may enter berserk.")
                .defineInRange("healthThreshold", 0.15D, 0.01D, 1.0D);
        EVA_BERSERK_SYNC_THRESHOLD = common
                .comment("Persistent pilot synchronization required to trigger berserk.")
                .defineInRange("syncThreshold", 60.0D, 0.0D, 100.0D);
        EVA_BERSERK_DAMAGE_MULTIPLIER = common
                .comment("Autonomous claw damage multiplier during berserk.")
                .defineInRange("damageMultiplier", 2.5D, 0.1D, 20.0D);
        EVA_BERSERK_TARGET_RANGE = common
                .comment("Maximum Angel acquisition range for berserk Unit-01.")
                .defineInRange("targetRange", 128, 16, 512);
        common.pop();

        common.push("eva_armament");
        EVA_ARMAMENT_RACK_ENFORCES_LOADOUT = common
                .comment("Require an EVA to use only the armament physically loaded from a NERV rack.",
                        "Disabled by default so existing visual-test worlds keep the complete R-key weapon wheel.")
                .define("requireRackLoadout", false);
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
        client.pop();
        CLIENT_SPEC = client.build();
    }

    private SeeleConfig() {}
}
