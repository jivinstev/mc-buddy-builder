package com.buddymod.compat;

import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.network.chat.Component;

import java.io.File;
import java.util.function.Consumer;

/**
 * Taking a frame off the main render target (Minecraft 26.2 dialect).
 *
 * <p>Two changes meet here:
 *
 * <ul>
 *   <li>{@code Minecraft.getMainRenderTarget()} is gone; the target lives on the game renderer
 *       as {@code mc.gameRenderer.mainRenderTarget()}.</li>
 *   <li>{@code Screenshot.takeScreenshot} no longer RETURNS a {@code NativeImage} — 26.x copies
 *       the colour texture into a GPU buffer through a command encoder and hands the decoded
 *       image to a {@code Consumer}. There is no synchronous form, which is why {@code capture}
 *       is callback-shaped on both sides rather than only here.</li>
 * </ul>
 *
 * <p>{@code grab} also gained a {@code downscaleFactor}; 1 is full resolution and is what
 * vanilla's own screenshot key passes.
 *
 * <p>The image is closed by vanilla once the consumer returns — do not stash it.
 */
public final class Screenshots {
    private Screenshots() {}

    /** Write a named PNG under {@code dir/screenshots/}. */
    public static void grab(Minecraft mc, File dir, String name, Consumer<Component> onDone) {
        Screenshot.grab(dir, name, mc.gameRenderer.mainRenderTarget(), 1, onDone);
    }

}
