package com.buddymod.compat;

import net.minecraft.client.Minecraft;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

/**
 * "Did this block/item actually get a model, or is it the magenta missing cube?"
 *
 * <p>26.2 changes every piece of this check: {@code ModelManager.getMissingModel()} is gone, block models moved behind a
 * {@code BlockStateModelSet}, and item models are resolved by id rather than by stack.
 */
public final class Models {
    private Models() {}

    public static boolean blockHasRealModel(BlockState state) {
        Minecraft mc = Minecraft.getInstance();
        var missing = mc.getModelManager().getMissingModel();
        return mc.getBlockRenderer().getBlockModel(state) != missing;
    }

    public static boolean itemHasRealModel(ItemStack stack) {
        Minecraft mc = Minecraft.getInstance();
        var missing = mc.getModelManager().getMissingModel();
        return mc.getItemRenderer().getModel(stack, mc.level, mc.player, 0) != missing;
    }

}
