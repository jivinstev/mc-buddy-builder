package com.buddymod;

/**
 * How hard the Bounce Block throws you back up. Plain maths with no Minecraft in it, so
 * it is tested in milliseconds (Gate A) and the block itself just carries out the answer.
 *
 * <p>Speeds are in blocks per tick. Falling is negative, going up is positive.
 */
public final class BounceMath {
    private BounceMath() {}

    /** Most of your landing speed comes back. */
    public static final double KEEP = 0.85;
    /** Even a tiny hop off the block bounces you properly. */
    public static final double MIN_UP = 0.7;
    /** A fall from the sky never fires you out of the world. */
    public static final double MAX_UP = 1.6;

    /** The upward speed to leave with, given the (negative) speed you landed at. */
    public static double bounceVelocity(double incomingY) {
        double up = -incomingY * KEEP;
        return Math.max(MIN_UP, Math.min(MAX_UP, up));
    }
}
