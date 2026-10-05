package com.buddymod;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/** Gate A: the bounce rules, checked in milliseconds without starting Minecraft. */
class BounceMathTest {

    @Test
    void aSmallHopStillBouncesProperly() {
        assertEquals(BounceMath.MIN_UP, BounceMath.bounceVelocity(-0.1), 1e-9);
    }

    @Test
    void aBiggerFallBouncesHigher() {
        assertTrue(BounceMath.bounceVelocity(-1.2) > BounceMath.bounceVelocity(-0.9));
    }

    @Test
    void aFallFromTheSkyNeverLaunchesYouOutOfTheWorld() {
        assertEquals(BounceMath.MAX_UP, BounceMath.bounceVelocity(-60.0), 1e-9);
    }

    @Test
    void youAlwaysLeaveGoingUp() {
        for (double v = -0.01; v > -10; v -= 0.37) {
            assertTrue(BounceMath.bounceVelocity(v) > 0, "landing at " + v);
        }
    }
}
