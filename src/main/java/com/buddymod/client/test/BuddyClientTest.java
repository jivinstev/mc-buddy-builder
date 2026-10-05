package com.buddymod.client.test;

import com.buddymod.BuddyMod;
import com.buddymod.ModContent;
import com.buddymod.compat.ClientTestWorlds;
import com.buddymod.compat.Models;
import com.buddymod.compat.Screenshots;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.AccessibilityOnboardingScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.resources.language.I18n;
import net.minecraft.client.server.IntegratedServer;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Difficulty;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;

/**
 * Gate C: a real Minecraft client, a real world, a real player.
 *
 * <p>These checks are impossible on a server. A block with a broken model shows up as a
 * black-and-purple cube while every server test still passes. A missing name shows the raw
 * key. And the only honest way to know the Bounce Block is fun is to drop a real player on it.
 *
 * <p>Runs only under {@code -D<modid>.boottest=true -D<modid>.testmode=buddy}
 * ({@code ./tools/client-test.sh} sets both). Writes PASS or FAIL to {@code <sigdir>/result}.
 */
@EventBusSubscriber(modid = BuddyMod.MODID, value = {Dist.CLIENT})
public final class BuddyClientTest {
    private static final String P = BuddyMod.MODID + ".";
    private static final String TAG = "BUDDY_TEST";
    private static final boolean ENABLED = "true".equals(System.getProperty(P + "boottest"))
            && "buddy".equalsIgnoreCase(System.getProperty(P + "testmode", ""));
    private static final Path SIG = Path.of(System.getProperty(P + "sigdir", "/tmp/buddymod-client"));

    private enum Phase { WAIT_TITLE, WAIT_INGAME, ASSETS, BUILD, DROP, SHOOT, REPORT, DONE }

    private static Phase phase = Phase.WAIT_TITLE;
    private static int ticks;
    private static boolean issued;
    private static final List<String> RESULTS = new ArrayList<>();
    private static int failures;
    private static volatile BlockPos base;
    private static volatile Boolean stepDone;
    private static volatile String err;
    private static double lowestY = Double.MAX_VALUE;
    private static double highestAfterLanding = Double.NEGATIVE_INFINITY;
    private static volatile float healthAfter = -1;
    private static volatile float maxHealth = -1;

    private BuddyClientTest() {}

    @SubscribeEvent
    public static void onClientTick(ClientTickEvent.Post event) {
        if (!ENABLED || phase == Phase.DONE) return;
        Minecraft mc = Minecraft.getInstance();
        try {
            switch (phase) {
                case WAIT_TITLE -> waitTitle(mc);
                case WAIT_INGAME -> waitIngame(mc);
                case ASSETS -> assets(mc);
                case BUILD -> build(mc);
                case DROP -> drop(mc);
                case SHOOT -> shoot(mc);
                case REPORT -> report(mc, failures == 0, String.join(" | ", RESULTS));
                default -> { }
            }
        } catch (Throwable t) {
            t.printStackTrace();
            report(mc, false, "EXCEPTION in phase " + phase + ": " + t);
        }
    }

    private static void waitTitle(Minecraft mc) {
        if (mc.screen instanceof AccessibilityOnboardingScreen) {
            mc.options.onboardAccessibility = false;
            mc.options.save();
            mc.setScreen(new TitleScreen());
            return;
        }
        if (!(mc.screen instanceof TitleScreen)) {
            // Name what is in the way rather than timing out with "the client died".
            if (++ticks > 1200) {
                report(mc, false, "never reached the title screen; stuck on "
                        + (mc.screen == null ? "no screen" : mc.screen.getClass().getName()));
            }
            return;
        }
        if (++ticks < 60) return;
        String levelName = "buddy-" + Long.toHexString(System.nanoTime());
        System.out.println(TAG + ": creating world '" + levelName + "'");
        // Peaceful: no monsters wandering into the test.
        ClientTestWorlds.createFlat(mc, levelName, Difficulty.PEACEFUL);
        transition(Phase.WAIT_INGAME);
    }

    private static void waitIngame(Minecraft mc) {
        IntegratedServer server = mc.getSingleplayerServer();
        boolean inWorld = server != null && server.isReady() && mc.player != null && mc.level != null;
        if (!inWorld) {
            if (++ticks > 20 * 180) report(mc, false, "world did not load in time");
            return;
        }
        if (++ticks < 60) return;
        transition(Phase.ASSETS);
    }

    /** The block has a real model, a real name, and a slot in the creative menu. */
    private static void assets(Minecraft mc) {
        var block = ModContent.BOUNCE_BLOCK.get();
        var item = ModContent.BOUNCE_BLOCK_ITEM.get();
        boolean blockModel = Models.blockHasRealModel(block.defaultBlockState());
        boolean itemModel = Models.itemHasRealModel(new ItemStack(item));
        boolean named = I18n.exists(block.getDescriptionId());
        // Tab contents are built lazily, so build them first. If this did not work the tab would
        // be EMPTY and the check below would fail; it can never pass by accident.
        CreativeModeTabs.tryRebuildTabContents(mc.level.enabledFeatures(), true, mc.level.registryAccess());
        boolean inTab = ModContent.TAB.get().getDisplayItems().stream().anyMatch(s -> s.getItem() == item);
        boolean ok = blockModel && itemModel && named && inTab;
        if (!ok) failures++;
        RESULTS.add("assets{blockModel=" + blockModel + " itemModel=" + itemModel
                + " named=" + named + " inCreativeTab=" + inTab + "}");
        System.out.println(TAG + ": " + RESULTS.get(RESULTS.size() - 1));
        transition(Phase.BUILD);
    }

    /** A 3x3 Bounce Block pad on a stone floor. */
    private static void build(Minecraft mc) {
        IntegratedServer server = mc.getSingleplayerServer();
        if (!issued) {
            issued = true;
            server.execute(() -> {
                try {
                    ServerPlayer p = serverPlayer(server);
                    ServerLevel level = server.overworld();
                    base = p.blockPosition();
                    for (int x = -6; x <= 6; x++) {
                        for (int z = -6; z <= 6; z++) {
                            level.setBlock(base.offset(x, -1, z), Blocks.STONE.defaultBlockState(), 2);
                            for (int y = 0; y <= 40; y++) {
                                level.setBlock(base.offset(x, y, z), Blocks.AIR.defaultBlockState(), 2);
                            }
                        }
                    }
                    for (int x = -1; x <= 1; x++) {
                        for (int z = -1; z <= 1; z++) {
                            level.setBlock(base.offset(x, 0, z), ModContent.BOUNCE_BLOCK.get().defaultBlockState(), 3);
                        }
                    }
                    stepDone = true;
                } catch (Throwable t) {
                    err = "building the pad: " + t;
                }
            });
        }
        if (err != null) { report(mc, false, err); return; }
        if (stepDone != null) transition(Phase.DROP);
        else if (++ticks > 200) report(mc, false, "the pad never got built");
    }

    /**
     * Drop a real SURVIVAL player from 30 blocks onto the pad. Creative players never take fall
     * damage, so a creative drop would prove nothing about "it doesn't hurt".
     */
    private static void drop(Minecraft mc) {
        IntegratedServer server = mc.getSingleplayerServer();
        if (!issued) {
            issued = true;
            server.execute(() -> {
                ServerPlayer p = serverPlayer(server);
                p.setGameMode(GameType.SURVIVAL);
                p.setHealth(p.getMaxHealth());
                p.teleportTo(base.getX() + 0.5, base.getY() + 30, base.getZ() + 0.5);
            });
            return;
        }
        ticks++;
        // The client owns the player's movement, so measure the bounce on the client.
        if (mc.player != null && ticks > 10) {
            double y = mc.player.getY();
            double padTop = base.getY() + 1.0;
            if (y < lowestY) lowestY = y;
            if (lowestY < padTop + 0.3) highestAfterLanding = Math.max(highestAfterLanding, y);
        }
        if (ticks == 160) {
            server.execute(() -> {
                ServerPlayer p = serverPlayer(server);
                healthAfter = p.getHealth();
                maxHealth = p.getMaxHealth();
                p.setGameMode(GameType.CREATIVE);
            });
        }
        if (ticks < 170 || healthAfter < 0) return;
        double bounce = highestAfterLanding - lowestY;
        boolean landed = lowestY < base.getY() + 1.3;
        // From 30 blocks the speed cap gives about 11 blocks; the minimum bounce alone gives about
        // 4. Asking for 6 means a version that ignores the landing speed fails here.
        boolean bounced = landed && bounce > 6.0;
        boolean unhurt = healthAfter >= maxHealth - 0.01;
        if (!(bounced && unhurt)) failures++;
        RESULTS.add(String.format("drop{landed=%s bounceHeight=%.2f health=%.1f/%.1f}",
                landed, Math.max(bounce, 0), healthAfter, maxHealth));
        System.out.println(TAG + ": " + RESULTS.get(RESULTS.size() - 1));
        transition(Phase.SHOOT);
    }

    /** A photo of the pad, so a person can see it is green and not a purple cube. */
    private static void shoot(Minecraft mc) {
        IntegratedServer server = mc.getSingleplayerServer();
        if (!issued) {
            issued = true;
            server.execute(() -> {
                ServerPlayer p = serverPlayer(server);
                p.getAbilities().flying = true;
                p.onUpdateAbilities();
                double cx = base.getX() + 0.5, cy = base.getY() + 3, cz = base.getZ() + 5.5;
                p.teleportTo(cx, cy, cz);
                // Rotation only reaches the client through a teleport packet.
                p.connection.teleport(cx, cy, cz, 180F, 35F);
            });
        }
        if (++ticks == 50) {
            Screenshots.grab(mc, mc.gameDirectory, "bounce_block.png",
                    m -> System.out.println(TAG + ": shot bounce_block.png"));
        }
        if (ticks >= 70) transition(Phase.REPORT);
    }

    private static ServerPlayer serverPlayer(IntegratedServer server) {
        return server.getPlayerList().getPlayers().get(0);
    }

    private static void transition(Phase next) {
        phase = next;
        ticks = 0;
        issued = false;
        stepDone = null;
    }

    private static void report(Minecraft mc, boolean ok, String detail) {
        phase = Phase.DONE;
        String result = (ok ? "PASS" : "FAIL") + " — " + detail;
        System.out.println(TAG + ": RESULT=" + result);
        try {
            Files.createDirectories(SIG);
            Files.writeString(SIG.resolve("result"), result + "\n");
        } catch (IOException e) {
            System.out.println(TAG + ": could not write result: " + e);
        }
        mc.stop();
    }
}
