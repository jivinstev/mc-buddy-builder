package com.buddymod.compat;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.phys.Vec3;

/**
 * A block that throws you back up when you land on it (Minecraft 1.21.1 version).
 *
 * <p>1.21.1 bounces with a HOOK: {@code updateEntityAfterFallOn} hands the block the
 * entity and lets it set the outgoing speed. 26.2 replaced the hook with a coefficient;
 * see the mc26 copy of this file. Subclasses answer the one question both versions share.
 */
public abstract class BouncyBlock extends Block {
    protected BouncyBlock(Properties properties) {
        super(properties);
    }

    /** Outgoing upward speed, given the (negative) speed the entity landed at. */
    protected abstract double bounceVelocity(double incomingY);

    @Override
    public void updateEntityAfterFallOn(BlockGetter level, Entity entity) {
        Vec3 motion = entity.getDeltaMovement();
        if (motion.y >= 0) {
            super.updateEntityAfterFallOn(level, entity);
            return;
        }
        entity.setDeltaMovement(motion.x, bounceVelocity(motion.y), motion.z);
        entity.resetFallDistance();
        // No `hurtMarked = true` here. On the server it sends the server's copy of the speed to
        // the client, and for a PLAYER the server's copy is near zero (the client moves the
        // player). Measured: it cut a 30-block drop's bounce from ~11 blocks to the 4-block
        // floor on this version only. Vanilla's slime block doesn't set it either.
    }
}
