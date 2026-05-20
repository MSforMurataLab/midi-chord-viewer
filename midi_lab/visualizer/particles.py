# -*- coding: utf-8 -*-
"""スタイル連動パーティクル。"""
from __future__ import annotations

import random
from dataclasses import dataclass

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPainter


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: QColor
    kind: int = 0  # 0=spark 1=ring 2=bar 3=laser


class ParticleSystem:
    def __init__(self, max_count: int = 400) -> None:
        self._particles: list[Particle] = []
        self._max = max_count
        self.amount_scale = 1.0

    def clear(self) -> None:
        self._particles.clear()

    def spawn_hit(
        self,
        x: float,
        y: float,
        velocity: int,
        style_kind: int,
        color: QColor,
    ) -> None:
        n = max(3, int(8 * self.amount_scale * (velocity / 127.0)))
        for _ in range(n):
            if len(self._particles) >= self._max:
                break
            ang = random.uniform(0, 6.283)
            spd = random.uniform(1.5, 5.5) * (velocity / 90.0)
            life = random.uniform(0.25, 0.7)
            self._particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=spd * random.uniform(0.3, 1.0) * (1 if style_kind == 3 else 0.7),
                    vy=spd * random.uniform(-1.2, -0.2) if style_kind != 2 else spd * random.uniform(-0.5, 0.5),
                    life=life,
                    max_life=life,
                    size=random.uniform(2.0, 5.5),
                    color=color,
                    kind=style_kind,
                )
            )

    def update(self, dt: float) -> None:
        alive: list[Particle] = []
        for p in self._particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx
            p.y += p.vy
            p.vy += 12.0 * dt
            alive.append(p)
        self._particles = alive

    def paint(self, painter: QPainter) -> None:
        for p in self._particles:
            a = max(0, min(255, int(255 * (p.life / p.max_life))))
            c = QColor(p.color)
            c.setAlpha(a)
            painter.setBrush(c)
            painter.setPen(c)
            if p.kind == 1:
                r = p.size * (1.0 + (1 - p.life / p.max_life))
                painter.drawEllipse(QPointF(p.x, p.y), r, r)
            else:
                painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
