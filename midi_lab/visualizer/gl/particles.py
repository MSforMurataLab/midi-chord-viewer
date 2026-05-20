# -*- coding: utf-8 -*-
"""GPU 向け大規模パーティクルプール — 鍵盤ヒットで上方向に飛散。"""
from __future__ import annotations

import random

import numpy as np

MAX_PARTICLES = 16384
PARTICLE_DTYPE = np.dtype(
    [
        ("px", "f4"),
        ("py", "f4"),
        ("vx", "f4"),
        ("vy", "f4"),
        ("life", "f4"),
        ("max_life", "f4"),
        ("size", "f4"),
        ("r", "f4"),
        ("g", "f4"),
        ("b", "f4"),
        ("a", "f4"),
    ]
)


class GPUParticleSystem:
    def __init__(self) -> None:
        self._data = np.zeros(MAX_PARTICLES, dtype=PARTICLE_DTYPE)
        self._count = 0
        self.amount_scale = 1.0

    def clear(self) -> None:
        self._count = 0

    def spawn_hit(
        self,
        x: float,
        y: float,
        velocity: int,
        *,
        r: float,
        g: float,
        b: float,
        style_kind: int = 0,
    ) -> None:
        vel_f = max(0.05, velocity / 127.0)
        n_spawn = max(8, int(32 * self.amount_scale * vel_f))
        for _ in range(n_spawn):
            if self._count >= MAX_PARTICLES:
                self._data = np.roll(self._data, -1, axis=0)
                self._count = MAX_PARTICLES - 1
            i = self._count
            self._count += 1
            spread = random.uniform(-0.55, 0.55)
            spd = random.uniform(120.0, 420.0) * vel_f
            life = random.uniform(0.4, 1.2)
            p = self._data[i]
            p["px"] = x + random.uniform(-6.0, 6.0)
            p["py"] = y
            if style_kind == 2:
                p["vx"] = spd * spread * 0.4
                p["vy"] = -spd * random.uniform(0.5, 1.0)
            elif style_kind == 3:
                p["vx"] = spd * spread
                p["vy"] = -spd * random.uniform(0.3, 0.7)
            else:
                p["vx"] = spd * spread * 0.65
                p["vy"] = -spd * random.uniform(0.75, 1.15)
            p["life"] = life
            p["max_life"] = life
            p["size"] = random.uniform(4.0, 16.0) * (0.5 + vel_f)
            p["r"] = r
            p["g"] = g
            p["b"] = b
            p["a"] = 1.0

    def update(self, dt: float) -> None:
        alive = 0
        for i in range(self._count):
            p = self._data[i]
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["px"] += p["vx"] * dt
            p["py"] += p["vy"] * dt
            p["vy"] += 220.0 * dt
            p["vx"] *= 1.0 - 1.8 * dt
            if alive != i:
                self._data[alive] = p
            alive += 1
        self._count = alive

    def active_array(self) -> np.ndarray:
        return self._data[: self._count]

    def __len__(self) -> int:
        return self._count
