package com.buddymod;

import com.buddymod.compat.BouncyBlock;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

/**
 * The example feature. Copy it, change it, or delete it: it's yours.
 *
 * <p>How it bounces is different on each Minecraft version, so that part lives in
 * {@link BouncyBlock}, which has one copy per version (src/mc21 and src/mc26). This file
 * only answers the question both versions ask: how fast should you leave?
 */
public class BounceBlock extends BouncyBlock {
    public BounceBlock(Properties properties) {
        super(properties);
    }

    @Override
    protected double bounceVelocity(double incomingY) {
        return BounceMath.bounceVelocity(incomingY);
    }

    /** Landing never hurts: pass a fall distance of zero on to Minecraft. */
    @Override
    public void fallOn(Level level, BlockState state, BlockPos pos, Entity entity, float fallDistance) {
        super.fallOn(level, state, pos, entity, 0.0F);
    }
}
