package com.buddymod.compat;

import net.minecraft.client.Minecraft;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

/**
 * See the 1.21.1 twin for why this is a pair.
 *
 * <p>26.2 routes both halves differently. Block models live in a {@code BlockStateModelSet}
 * that carries its own {@code missingModel()}, so the comparison still works and is in fact
 * more direct than going through the block renderer. Items no longer resolve a model from a
 * <em>stack</em> at all — {@code ModelManager.getItemModel(Identifier)} is keyed by the item's
 * client-item definition id, and it logs "Missing item model for location {}" and returns the
 * missing model when the mod ships no {@code assets/&lt;ns&gt;/items/&lt;id&gt;.json}.
 */
public final class Models {
    private Models() {}

    public static boolean blockHasRealModel(BlockState state) {
        var set = Minecraft.getInstance().getModelManager().getBlockStateModelSet();
        return set.get(state) != set.missingModel();
    }

    public static boolean itemHasRealModel(ItemStack stack) {
        var manager = Minecraft.getInstance().getModelManager();
        var id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        var missing = manager.getItemModel(net.minecraft.resources.Identifier.withDefaultNamespace("missing"));
        return manager.getItemModel(id) != missing;
    }

}
