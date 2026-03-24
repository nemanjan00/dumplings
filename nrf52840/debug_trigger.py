#!/usr/bin/env python3
"""Debug script to check TIO4 trigger with full HuskyGlitcher init."""
import time
from findus.HuskyGlitcher import HuskyGlitcher

glitcher = HuskyGlitcher()
glitcher.init()
glitcher.rising_edge_trigger()
glitcher.set_hpglitch()

scope = glitcher.scope

print(f"clkgen_freq: {scope.clock.clkgen_freq}")
print(f"adc_freq: {scope.clock.adc_freq}")
print(f"adc_mul: {scope.clock.adc_mul}")
print(f"tio4: {scope.io.tio4}")
print(f"trigger: {scope.trigger.triggers}")
print(f"basic_mode: {scope.adc.basic_mode}")
print(f"glitch enabled: {scope.glitch.enabled}")
print(f"glitch trigger_src: {scope.glitch.trigger_src}")
print(f"glitch output: {scope.glitch.output}")
print(f"glitch clk_src: {scope.glitch.clk_src}")
print(f"target_pwr: {scope.io.target_pwr}")

# Test 1: power cycle with arm
print("\n--- Test: power off, arm, power on ---")
scope.io.target_pwr = False
time.sleep(0.3)
print(f"tio_states after OFF: {scope.io.tio_states}")

glitcher.arm(1000, 100)
print("Armed. Waiting 50ms for scope to be ready...")
time.sleep(0.05)

scope.io.target_pwr = True
print(f"tio_states after ON: {scope.io.tio_states}")

print("Calling scope.capture()...")
ret = scope.capture()
if ret:
    print("TIMEOUT - no trigger seen!")
else:
    print("SUCCESS - trigger fired!")

scope.dis()
