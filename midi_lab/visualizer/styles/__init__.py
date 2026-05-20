# -*- coding: utf-8 -*-
from midi_lab.visualizer.styles.base import RenderContext, RenderStyle
from midi_lab.visualizer.styles.circular import CircularStyle
from midi_lab.visualizer.styles.cyber import CyberLaserStyle
from midi_lab.visualizer.styles.spectrum import SpectrumStyle
from midi_lab.visualizer.styles.waterfall import WaterfallStyle

STYLES: dict[str, RenderStyle] = {
    WaterfallStyle.id: WaterfallStyle(),
    CircularStyle.id: CircularStyle(),
    SpectrumStyle.id: SpectrumStyle(),
    CyberLaserStyle.id: CyberLaserStyle(),
}

STYLE_ORDER = ("waterfall", "circular", "spectrum", "cyber")

__all__ = ["STYLES", "STYLE_ORDER", "RenderContext", "RenderStyle"]
