package com.projectseele.world;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.event.Tokyo3RamielBattleDirector;
import com.projectseele.event.Tokyo3RamielBattleDirector.BattleResult;
import com.projectseele.visual.GeoFrontCommands;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.AttachFace;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/**
 * Seven physical controls inside the imported NERV command module.
 *
 * <p>The console never bypasses the entry-plug passenger or launch-bed
 * interlocks.  A commander may release a synchronized occupied airframe, but
 * cannot launch an empty or unlinked EVA.</p>
 */
public final class NervOperationsConsole
{
    public static final int CONTROL_COUNT = 7;

    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;
    private static final int CONTROL_Y = 15;
    // The imported screen plane is z=58 and the main gallery approaches from
    // positive Z.  Put the operator row in front of that plane, not behind it.
    private static final int CONTROL_Z = 64;
    private static final int LEGACY_CONTROL_Z = 52;
    private static final int FIRST_CONTROL_X = -12;
    private static final int CONTROL_SPACING = 4;
    private static final String LABEL_TAG_PREFIX =
            "projectseele.nerv_control.";
    private static final String[] IDS = {
            "system", "unit00", "unit01", "unit02",
            "armour", "yashima", "abort"
    };
    private static final String[] LABELS = {
            "MAGI\nCHECK", "EVA-00\nRELEASE", "EVA-01\nRELEASE",
            "EVA-02\nRELEASE", "CITY\nARMOUR", "YASHIMA\nSTART",
            "BATTLE\nABORT"
    };
    private static final BlockState[] BASES = {
            Blocks.CYAN_CONCRETE.defaultBlockState(),
            Blocks.ORANGE_CONCRETE.defaultBlockState(),
            Blocks.PURPLE_CONCRETE.defaultBlockState(),
            Blocks.RED_CONCRETE.defaultBlockState(),
            Blocks.YELLOW_CONCRETE.defaultBlockState(),
            Blocks.LIME_CONCRETE.defaultBlockState(),
            Blocks.BLACK_CONCRETE.defaultBlockState()
    };
    private static final ChatFormatting[] LABEL_COLOURS = {
            ChatFormatting.AQUA, ChatFormatting.GOLD,
            ChatFormatting.LIGHT_PURPLE, ChatFormatting.RED,
            ChatFormatting.YELLOW, ChatFormatting.GREEN,
            ChatFormatting.RED
    };

    private static String lastAction = "COMMAND BUS: STANDBY";
    private static long lastActionAt = Long.MIN_VALUE;

    private NervOperationsConsole() {}

    /** Backfills the console into both local-map and clean-room command halls. */
    public static void install(ServerLevel level, BlockPos origin)
    {
        level.getChunkAt(controlPosition(origin, 0));
        removeLegacyRow(level, origin);
        int createdControls = 0;
        int createdLabels = 0;
        BlockState button = Blocks.STONE_BUTTON.defaultBlockState()
                .setValue(ButtonBlock.FACE, AttachFace.FLOOR)
                .setValue(ButtonBlock.FACING, Direction.NORTH);
        for (int index = 0; index < CONTROL_COUNT; index++)
        {
            BlockPos position = controlPosition(origin, index);
            BlockPos base = position.below();
            BlockPos support = base.below();
            if (level.getBlockState(support).isAir())
            {
                level.setBlock(support,
                        Blocks.POLISHED_BLACKSTONE.defaultBlockState(),
                        UPDATE_CLIENTS);
            }
            if (!level.getBlockState(base).equals(BASES[index]))
            {
                level.setBlock(base, BASES[index], UPDATE_CLIENTS);
            }
            if (!level.getBlockState(position).is(Blocks.STONE_BUTTON))
            {
                level.setBlock(position, button, UPDATE_CLIENTS);
                createdControls++;
            }

            String tag = LABEL_TAG_PREFIX + IDS[index];
            List<Display.TextDisplay> matches = labels(level, origin, tag);
            Display.TextDisplay label;
            if (matches.isEmpty())
            {
                label = EntityType.TEXT_DISPLAY.create(level);
                if (label == null)
                {
                    continue;
                }
                label.addTag(tag);
                label.setNoGravity(true);
                label.setInvulnerable(true);
                label.setSilent(true);
                level.addFreshEntity(label);
                createdLabels++;
            }
            else
            {
                label = matches.get(0);
                for (int duplicate = 1; duplicate < matches.size(); duplicate++)
                {
                    matches.get(duplicate).discard();
                }
            }
            updateLabel(label, position, index);
        }
        if (createdControls > 0 || createdLabels > 0)
        {
            ProjectSeele.LOGGER.info(
                    "NERV operations console installed: controls={}/{} labels={}/{} createdControls={} createdLabels={}",
                    countControls(level, origin), CONTROL_COUNT,
                    countLabels(level, origin), CONTROL_COUNT,
                    createdControls, createdLabels);
        }
    }

    /** Returns true only for one of the seven exact NERV command buttons. */
    public static boolean handleUse(ServerPlayer player, BlockPos position)
    {
        if (!player.serverLevel().dimension().equals(GeoFrontCommands.GEOFRONT))
        {
            return false;
        }
        BlockPos origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        int action = actionAt(origin, position);
        if (action < 0)
        {
            return false;
        }

        ServerLevel level = player.serverLevel();
        ActionResult result = switch (action)
        {
            case 0 -> prepareSortie(level);
            case 1 -> releaseUnit(level, EvaUnit01Entity.UNIT_00);
            case 2 -> releaseUnit(level, EvaUnit01Entity.UNIT_01);
            case 3 -> releaseUnit(level, EvaUnit01Entity.UNIT_02);
            case 4 -> toggleArmour(level);
            case 5 -> startYashima(level, player);
            case 6 -> abortYashima(level);
            default -> new ActionResult(false, "Unknown MAGI control address.");
        };
        record(level, IDS[action] + ": " + result.message());
        player.displayClientMessage(Component.literal("[NERV] " + result.message())
                .withStyle(result.accepted()
                        ? ChatFormatting.GREEN : ChatFormatting.RED), false);
        ProjectSeele.LOGGER.info(
                "NERV console action: player={} action={} accepted={} position={} result={}",
                player.getGameProfile().getName(), IDS[action],
                result.accepted(), position.toShortString(), result.message());
        NervCommandTelemetry.install(level, origin);
        return true;
    }

    public static ConsoleAudit inspect(ServerLevel level, BlockPos origin)
    {
        level.getChunkAt(controlPosition(origin, 0));
        int controls = countControls(level, origin);
        int bases = 0;
        for (int index = 0; index < CONTROL_COUNT; index++)
        {
            if (level.getBlockState(controlPosition(origin, index).below())
                    .equals(BASES[index]))
            {
                bases++;
            }
        }
        int labels = countLabels(level, origin);
        int supports = 0;
        for (int index = 0; index < CONTROL_COUNT; index++)
        {
            if (!level.getBlockState(controlPosition(origin, index)
                    .below(2)).isAir())
            {
                supports++;
            }
        }
        return new ConsoleAudit(controls == CONTROL_COUNT
                && bases == CONTROL_COUNT && labels == CONTROL_COUNT
                && supports == CONTROL_COUNT,
                controls, bases, labels, supports);
    }

    public static String statusLine(ServerLevel level)
    {
        if (lastActionAt == Long.MIN_VALUE
                || level.getGameTime() - lastActionAt > 600L)
        {
            return "COMMAND BUS: STANDBY";
        }
        return "LAST COMMAND: " + lastAction;
    }

    public static void reset()
    {
        lastAction = "COMMAND BUS: STANDBY";
        lastActionAt = Long.MIN_VALUE;
    }

    private static ActionResult prepareSortie(ServerLevel level)
    {
        IntegratedNervMapBuilder.RuntimeAudit map =
                IntegratedNervMapBuilder.prepareRuntime(level);
        if (!map.valid())
        {
            return new ActionResult(false,
                    "MAGI sortie gate failed; run /seele geofront audit for details.");
        }
        try
        {
            List<EvaUnit01Entity> units =
                    GeoFrontCommands.ensureContinuousSortieUnits(level);
            return new ActionResult(units.size() == 3,
                    units.size() == 3
                            ? "MAGI check complete; EVA-00/01/02 are linked to their physical shafts."
                            : "MAGI check found only " + units.size() + "/3 airframes.");
        }
        catch (IllegalStateException exception)
        {
            return new ActionResult(false, exception.getMessage());
        }
    }

    private static ActionResult releaseUnit(ServerLevel level, int variant)
    {
        EvaUnit01Entity unit = evaUnits(level).stream()
                .filter(candidate -> candidate.getUnitVariant() == variant)
                .sorted(Comparator
                        .comparing((EvaUnit01Entity candidate) ->
                                candidate.getLaunchPhase()
                                        != EvaUnit01Entity.LAUNCH_LOCKED)
                        .thenComparingDouble(candidate -> candidate.distanceToSqr(
                                IntegratedNervMapBuilder.lowerLiftBed(variant)
                                        .getCenter())))
                .findFirst().orElse(null);
        if (unit == null)
        {
            return new ActionResult(false,
                    String.format(Locale.ROOT,
                            "EVA-%02d is not linked to the command network.", variant));
        }
        if (!unit.releaseLaunchFromCommand())
        {
            return new ActionResult(false,
                    String.format(Locale.ROOT,
                            "EVA-%02d release inhibited: insert a pilot and complete launch lock.",
                            variant));
        }
        return new ActionResult(true,
                String.format(Locale.ROOT,
                        "EVA-%02d catapult release authorized.", variant));
    }

    private static ActionResult toggleArmour(ServerLevel level)
    {
        Tokyo3RetractionDirector.Status status =
                Tokyo3RetractionDirector.status(level,
                        IntegratedNervMapBuilder.TOKYO3_ORIGIN);
        Tokyo3RetractionDirector.RequestResult result =
                Tokyo3RetractionDirector.request(level,
                        IntegratedNervMapBuilder.TOKYO3_ORIGIN,
                        status.targetDepth() == 0);
        return new ActionResult(result.accepted(), result.message());
    }

    private static ActionResult startYashima(ServerLevel level,
                                             ServerPlayer commander)
    {
        IntegratedNervMapBuilder.RuntimeAudit map =
                IntegratedNervMapBuilder.prepareRuntime(level);
        if (!map.valid())
        {
            return new ActionResult(false,
                    "Operation Yashima inhibited: live sortie route failed its gate.");
        }
        BattleResult result = Tokyo3RamielBattleDirector.start(level,
                IntegratedNervMapBuilder.TOKYO3_ORIGIN, commander);
        return new ActionResult(result.accepted(), result.message());
    }

    private static ActionResult abortYashima(ServerLevel level)
    {
        BattleResult result = Tokyo3RamielBattleDirector.abort(level,
                IntegratedNervMapBuilder.TOKYO3_ORIGIN);
        return new ActionResult(result.accepted(), result.message());
    }

    private static List<EvaUnit01Entity> evaUnits(ServerLevel level)
    {
        BlockPos centre = IntegratedNervMapBuilder.TOKYO3_ORIGIN;
        AABB map = new AABB(centre.getX() - 320.0D,
                level.getMinBuildHeight(), centre.getZ() - 320.0D,
                centre.getX() + 320.0D, level.getMaxBuildHeight(),
                centre.getZ() + 320.0D);
        return level.getEntitiesOfClass(EvaUnit01Entity.class, map,
                Entity::isAlive);
    }

    private static void record(ServerLevel level, String action)
    {
        lastAction = action.length() > 92
                ? action.substring(0, 92) : action;
        lastActionAt = level.getGameTime();
    }

    private static int actionAt(BlockPos origin, BlockPos position)
    {
        for (int index = 0; index < CONTROL_COUNT; index++)
        {
            if (controlPosition(origin, index).equals(position))
            {
                return index;
            }
        }
        return -1;
    }

    private static void removeLegacyRow(ServerLevel level, BlockPos origin)
    {
        for (int index = 0; index < CONTROL_COUNT; index++)
        {
            int x = FIRST_CONTROL_X + index * CONTROL_SPACING;
            BlockPos legacy = origin.offset(x, CONTROL_Y,
                    LEGACY_CONTROL_Z);
            if (level.getBlockState(legacy).is(Blocks.STONE_BUTTON))
            {
                level.setBlock(legacy, Blocks.AIR.defaultBlockState(),
                        UPDATE_CLIENTS);
            }
            BlockState oldBase = level.getBlockState(legacy.below());
            for (BlockState state : BASES)
            {
                if (oldBase.equals(state))
                {
                    level.setBlock(legacy.below(),
                            Blocks.AIR.defaultBlockState(), UPDATE_CLIENTS);
                    break;
                }
            }
        }
    }

    public static BlockPos controlPosition(BlockPos origin, int index)
    {
        if (index < 0 || index >= CONTROL_COUNT)
        {
            throw new IllegalArgumentException(
                    "NERV control index must be within 0.."
                            + (CONTROL_COUNT - 1));
        }
        return origin.offset(FIRST_CONTROL_X + index * CONTROL_SPACING,
                CONTROL_Y, CONTROL_Z);
    }

    private static int countControls(ServerLevel level, BlockPos origin)
    {
        int count = 0;
        for (int index = 0; index < CONTROL_COUNT; index++)
        {
            if (level.getBlockState(controlPosition(origin, index))
                    .is(Blocks.STONE_BUTTON))
            {
                count++;
            }
        }
        return count;
    }

    private static int countLabels(ServerLevel level, BlockPos origin)
    {
        int count = 0;
        for (String id : IDS)
        {
            if (!labels(level, origin, LABEL_TAG_PREFIX + id).isEmpty())
            {
                count++;
            }
        }
        return count;
    }

    private static List<Display.TextDisplay> labels(ServerLevel level,
                                                    BlockPos origin,
                                                    String tag)
    {
        AABB bounds = AABB.ofSize(
                Vec3.atCenterOf(origin.offset(0, CONTROL_Y + 1, CONTROL_Z)),
                80.0D, 32.0D, 40.0D);
        List<Display.TextDisplay> result = new ArrayList<>(
                level.getEntitiesOfClass(Display.TextDisplay.class, bounds,
                        display -> display.getTags().contains(tag)));
        result.sort(Comparator.comparingInt(Entity::getId));
        return result;
    }

    private static void updateLabel(Display.TextDisplay label,
                                    BlockPos button, int index)
    {
        Component text = Component.literal(LABELS[index])
                .withStyle(LABEL_COLOURS[index], ChatFormatting.BOLD);
        CompoundTag tag = label.saveWithoutId(new CompoundTag());
        tag.putString("text", Component.Serializer.toJson(text));
        tag.putInt("line_width", 120);
        tag.putInt("background", 0xB0101418);
        tag.putByte("text_opacity", (byte) -1);
        tag.putBoolean("shadow", true);
        tag.putBoolean("see_through", false);
        tag.putBoolean("default_background", false);
        tag.putString("alignment", "center");
        tag.putString("billboard", "vertical");
        tag.putFloat("view_range", 3.0F);
        tag.putFloat("width", 3.5F);
        tag.putFloat("height", 1.4F);
        tag.putInt("glow_color_override", 0xFFFF8000);
        CompoundTag brightness = new CompoundTag();
        brightness.putInt("block", 15);
        brightness.putInt("sky", 15);
        tag.put("brightness", brightness);
        label.load(tag);
        label.setPos(button.getX() + 0.5D, button.getY() + 1.35D,
                button.getZ() + 0.5D);
        label.setYRot(180.0F);
        label.setXRot(0.0F);
    }

    private record ActionResult(boolean accepted, String message) {}

    public record ConsoleAudit(boolean valid, int controls,
                               int bases, int labels, int supports)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s controls=%d/%d bases=%d/%d labels=%d/%d supports=%d/%d",
                    this.valid, this.controls, CONTROL_COUNT,
                    this.bases, CONTROL_COUNT, this.labels, CONTROL_COUNT,
                    this.supports, CONTROL_COUNT);
        }
    }
}
