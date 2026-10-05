package com.buddymod;

import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.MapColor;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredBlock;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;

/** Everything this mod adds to the game. A new block or item is one more line here. */
public final class ModContent {
    private ModContent() {}

    public static final DeferredRegister.Blocks BLOCKS = DeferredRegister.createBlocks(BuddyMod.MODID);
    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(BuddyMod.MODID);
    public static final DeferredRegister<CreativeModeTab> TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, BuddyMod.MODID);

    /** Step on it and it throws you back up. Landing on it never hurts. */
    public static final DeferredBlock<BounceBlock> BOUNCE_BLOCK = BLOCKS.registerBlock("bounce_block",
            BounceBlock::new,
            BlockBehaviour.Properties.of().mapColor(MapColor.COLOR_LIGHT_GREEN).strength(0.5F)
                    .sound(SoundType.SLIME_BLOCK));

    public static final DeferredItem<BlockItem> BOUNCE_BLOCK_ITEM = ITEMS.registerSimpleBlockItem(BOUNCE_BLOCK);

    /** The mod's own tab in the creative menu, so everything it adds is easy to find. */
    public static final DeferredHolder<CreativeModeTab, CreativeModeTab> TAB = TABS.register("main",
            () -> CreativeModeTab.builder()
                    .title(Component.translatable("itemGroup." + BuddyMod.MODID))
                    .icon(() -> new ItemStack(BOUNCE_BLOCK_ITEM.get()))
                    .displayItems((params, output) -> output.accept(BOUNCE_BLOCK_ITEM.get()))
                    .build());

    public static void register(IEventBus modBus) {
        BLOCKS.register(modBus);
        ITEMS.register(modBus);
        TABS.register(modBus);
    }
}
