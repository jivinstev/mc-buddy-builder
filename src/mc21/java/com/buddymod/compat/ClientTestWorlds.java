package com.buddymod.compat;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.Difficulty;
import net.minecraft.world.level.GameRules;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.level.levelgen.presets.WorldPresets;

/** Creating a test world (Minecraft 1.21.1). The 26.2 copy explains what changed. */
public final class ClientTestWorlds {
    private ClientTestWorlds() {}

    public static void createFlat(Minecraft mc, String levelName, Difficulty difficulty) {
        LevelSettings settings = new LevelSettings(levelName, GameType.CREATIVE, false, difficulty,
                true, new GameRules(), WorldDataConfiguration.DEFAULT);
        mc.createWorldOpenFlows().createFreshLevel(levelName, settings, WorldOptions.defaultWithRandomSeed(),
                reg -> reg.registryOrThrow(Registries.WORLD_PRESET).getHolderOrThrow(WorldPresets.FLAT)
                        .value().createWorldDimensions(),
                new TitleScreen());
    }
}
