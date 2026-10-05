package com.buddymod.compat;

import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

/**
 * A block that throws you back up when you land on it (Minecraft 26.2 version).
 *
 * <p>26.2 deleted the {@code updateEntityAfterFallOn} hook. Bouncing is now a
 * restitution COEFFICIENT, and NeoForge's {@code getBounceRestitution} is handed the
 * entity, so the block can read the arriving speed and return the coefficient that
 * produces the speed it wants, floor and cap included.
 */
public abstract class BouncyBlock extends Block {
    protected BouncyBlock(Properties properties) {
        super(properties);
    }

    /** Outgoing upward speed, given the (negative) speed the entity landed at. */
    protected abstract double bounceVelocity(double incomingY);

    @Override
    public float getBounceRestitution(Level level, BlockPos pos, BlockState state, Entity entity) {
        double incomingY = entity.getDeltaMovement().y;
        if (incomingY >= 0) return super.getBounceRestitution(level, pos, state, entity);
        return (float) (bounceVelocity(incomingY) / -incomingY);
    }
}
