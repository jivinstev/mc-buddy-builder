package com.buddymod.client.test;

import com.buddymod.BuddyMod;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.PauseScreen;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;

/**
 * Keeps every Gate C client test running when the game window loses focus.
 *
 * <p>Singleplayer pauses its own server the moment the window loses focus. A stolen window
 * does not fail a test cleanly: it fails as unrelated-looking assertions (nothing moved,
 * nothing synced) that read like real bugs. One shared guard covers every client test,
 * including ones written later, so nobody has to remember it.
 *
 * <p>Inert in the shipped mod: it only runs under {@code -D<modid>.boottest=true}, which only
 * the {@code tools/*-client.sh} launchers pass.
 */
@EventBusSubscriber(modid = BuddyMod.MODID, value = {Dist.CLIENT})
public final class ClientTestPauseGuard {
    private static final boolean ENABLED = "true".equals(System.getProperty(BuddyMod.MODID + ".boottest"));
    private static boolean announced;

    private ClientTestPauseGuard() {}

    @SubscribeEvent
    public static void onClientTick(ClientTickEvent.Post event) {
        if (!ENABLED) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.options == null) return;
        if (mc.options.pauseOnLostFocus) {
            mc.options.pauseOnLostFocus = false;
            mc.options.save();
            if (!announced) {
                announced = true;
                System.out.println("CLIENT_TEST_GUARD: pauseOnLostFocus disabled");
            }
        }
        if (mc.screen instanceof PauseScreen) {
            mc.setScreen(null);
        }
        // NeoForge shows a warning screen in front of the title screen when any mod logs a
        // load warning. A person clicks past it; a headless test would wait forever. Matched
        // by class name so this file needs no per-version import.
        if (mc.screen != null && mc.screen.getClass().getSimpleName().equals("LoadingErrorScreen")) {
            System.out.println("CLIENT_TEST_GUARD: dismissed NeoForge's mod-loading warning screen");
            mc.setScreen(new net.minecraft.client.gui.screens.TitleScreen());
        }
    }
}
