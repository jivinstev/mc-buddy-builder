package com.buddymod;

import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;

/**
 * Gate B: a real Minecraft server, with real physics. A cow is dropped onto a Bounce
 * Block from high up. It must land, fly back up, and not lose any health.
 *
 * <p>The cow keeps its AI on purpose: a mob with AI switched off does not move at all,
 * and the test would report "it never bounced" about a block that works.
 */
@GameTestHolder(BuddyMod.MODID)
@PrefixGameTestTemplate(false)
public class BounceGameTest {

    @GameTest(template = "empty_test", timeoutTicks = 200)
    public static void aCowDroppedOnTheBlockBouncesAndIsNotHurt(GameTestHelper helper) {
        BlockPos pad = new BlockPos(4, 1, 4);
        helper.setBlock(pad, ModContent.BOUNCE_BLOCK.get());
        LivingEntity cow = helper.spawn(EntityType.COW, new BlockPos(4, 12, 4));
        float startHealth = cow.getHealth();
        double padTop = helper.absolutePos(pad).getY() + 1.0;
        double[] lowest = {Double.MAX_VALUE};
        double[] highestAfterLanding = {Double.NEGATIVE_INFINITY};

        helper.succeedWhen(() -> {
            double y = cow.getY();
            if (y < lowest[0]) lowest[0] = y;
            boolean landed = lowest[0] < padTop + 0.2;
            if (landed) highestAfterLanding[0] = Math.max(highestAfterLanding[0], y);
            helper.assertTrue(landed, "the cow has not reached the block yet");
            // 3.5 blocks: the minimum bounce alone reaches about 3, so passing needs the cow's
            // real landing speed to have been used.
            helper.assertTrue(highestAfterLanding[0] > lowest[0] + 3.5,
                    "the cow bounced only " + String.format("%.2f", highestAfterLanding[0] - lowest[0])
                            + " blocks after a 10-block drop");
            helper.assertTrue(cow.isAlive() && cow.getHealth() >= startHealth,
                    "landing on a Bounce Block must not hurt (health " + cow.getHealth() + ")");
        });
    }
}
