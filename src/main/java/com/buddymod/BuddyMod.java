package com.buddymod;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;

/**
 * The mod's front door. Minecraft calls this constructor once when the game starts.
 *
 * <p>Register content on the MOD bus (here). Gameplay events (commands, ticks, players)
 * go on {@code NeoForge.EVENT_BUS}. The wrong bus compiles and silently does nothing.
 */
@Mod(BuddyMod.MODID)
public class BuddyMod {
    public static final String MODID = "buddymod";

    public BuddyMod(IEventBus modBus, ModContainer container) {
        ModContent.register(modBus);
    }
}
