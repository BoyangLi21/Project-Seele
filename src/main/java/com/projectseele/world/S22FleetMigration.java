package com.projectseele.world;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import com.projectseele.ProjectSeele;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;

/** One-shot normalization of copied EVA runtime state in the coastal save. */
public final class S22FleetMigration
{
    private static boolean terminalDogmaChecked;

    private S22FleetMigration() {}

    public static void tick(MinecraftServer server)
    {
        if (!FacilityWorldPolicy.isS22Coastal(server)
                || FacilityWorldPolicy.isS22MigrationFrozen(server)
                || server.getTickCount() < 100
                || server.getTickCount() % 100 != 0)
        {
            return;
        }
        Path receipt = server.getWorldPath(LevelResource.ROOT).resolve(
                FacilityWorldPolicy.S22_FLEET_PARKED_RECEIPT);
        ServerLevel level = server.getLevel(FacilitySchemaV2.DIMENSION);
        if (level == null)
        {
            return;
        }

        if (!terminalDogmaChecked)
        {
            TerminalDogmaBuilder.repairRuntimeSpecimen(
                    level, IntegratedNervMapBuilder.GEOFRONT_ORIGIN);
            terminalDogmaChecked = true;
        }
        if (Files.isRegularFile(receipt))
        {
            return;
        }

        try
        {
            for (int variant = 0; variant < 3; variant++)
            {
                EvaLogisticsDirector.forceReset(level, variant);
            }
            Files.writeString(receipt,
                    "{\n"
                            + "  \"revision\": 1,\n"
                            + "  \"result\": \"all three EVA units normalized to PARKED\"\n"
                            + "}\n",
                    StandardCharsets.US_ASCII);
            ProjectSeele.LOGGER.info(
                    "S22 coastal fleet migration complete: all EVA units parked");
        }
        catch (IOException | RuntimeException exception)
        {
            ProjectSeele.LOGGER.error(
                    "S22 coastal fleet migration failed; receipt was not written",
                    exception);
        }
    }
}
