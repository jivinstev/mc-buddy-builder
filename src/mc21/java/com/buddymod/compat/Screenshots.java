package com.buddymod.compat;

import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.network.chat.Component;

import java.io.File;
import java.util.function.Consumer;

/**
 * Taking a frame off the main render target (Minecraft 1.21.1 dialect).
 *
 * <p>Both entry points forward to vanilla. They exist because 26.x moved the render target and
 * made the pixel readback asynchronous — see the 26.2 side of this pair.
 */
public final class Screenshots {
    private Screenshots() {}

    /** Write a named PNG under {@code dir/screenshots/}. */
    public static void grab(Minecraft mc, File dir, String name, Consumer<Component> onDone) {
        Screenshot.grab(dir, name, mc.getMainRenderTarget(), onDone);
    }

}
