package com.buddymod.compat;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.Difficulty;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.level.levelgen.presets.WorldPresets;

/**
 * Creating a test world (Minecraft 26.2).
 *
 * <p>26.x changed three things here: {@code LevelSettings} lost its {@code GameRules}
 * argument and folded difficulty and hardcore into {@code DifficultySettings};
 * {@code createFreshLevel} takes a {@code HolderLookup.Provider}; and the lookup is
 * {@code lookupOrThrow(..).getOrThrow(..)}. The remaining boolean is allowCommands, not
 * hardcore: swapping them compiles and makes a hardcore world where every command fails.
 */
public final class ClientTestWorlds {
    private ClientTestWorlds() {}

    public static void createFlat(Minecraft mc, String levelName, Difficulty difficulty) {
        LevelSettings settings = new LevelSettings(levelName, GameType.CREATIVE,
                new LevelSettings.DifficultySettings(difficulty, false, false),
                true, WorldDataConfiguration.DEFAULT);
        mc.createWorldOpenFlows().createFreshLevel(levelName, settings, WorldOptions.defaultWithRandomSeed(),
                reg -> reg.lookupOrThrow(Registries.WORLD_PRESET).getOrThrow(WorldPresets.FLAT)
                        .value().createWorldDimensions(),
                new TitleScreen());
    }
}
