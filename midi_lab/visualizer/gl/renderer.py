# -*- coding: utf-8 -*-
"""ModernGL ビジュアライザ — ブルーム・加算合成・疑似グロー。"""
from __future__ import annotations

import moderngl
import numpy as np

from midi_lab.visualizer.engine import VisualizerEngine
from midi_lab.visualizer.gl import shaders
from midi_lab.visualizer.gl.geometry import build_scene_meshes

_QUAD = np.array(
    [-1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, 1.0],
    dtype="f4",
)


class GpuRenderer:
    def __init__(self, ctx: moderngl.Context, width: int = 1280, height: int = 720) -> None:
        self.ctx = ctx
        self.width = max(64, width)
        self.height = max(64, height)
        self._pass_prog = ctx.program(
            vertex_shader=shaders.PASS_VS,
            fragment_shader=shaders.PASS_FS,
        )
        self._particle_prog = ctx.program(
            vertex_shader=shaders.PARTICLE_VS,
            fragment_shader=shaders.PARTICLE_FS,
        )
        self._blur_prog = ctx.program(
            vertex_shader=shaders.SCREEN_VS,
            fragment_shader=shaders.BLUR_FS,
        )
        self._composite_prog = ctx.program(
            vertex_shader=shaders.SCREEN_VS,
            fragment_shader=shaders.COMPOSITE_FS,
        )
        self._screen_vbo = ctx.buffer(_QUAD.tobytes())
        self._screen_vao_blur = ctx.vertex_array(
            self._blur_prog, [(self._screen_vbo, "2f", "in_pos")]
        )
        self._screen_vao_comp = ctx.vertex_array(
            self._composite_prog, [(self._screen_vbo, "2f", "in_pos")]
        )
        self._note_vbo = ctx.buffer(reserve=8 * 1024 * 64)
        self._note_vao = ctx.vertex_array(
            self._pass_prog,
            [(self._note_vbo, "2f 4f", "in_pos", "in_color")],
        )
        self._particle_vbo = ctx.buffer(reserve=16384 * 28)
        self._particle_vao = ctx.vertex_array(
            self._particle_prog,
            [(self._particle_vbo, "2f 1f 4f", "in_pos", "in_size", "in_color")],
        )
        self._fbo_scene = None
        self._fbo_bloom_a = None
        self._fbo_bloom_b = None
        self._resize_fbos()
        self.bloom_strength = 1.35

    def _resize_fbos(self) -> None:
        w, h = self.width, self.height
        for f in (self._fbo_scene, self._fbo_bloom_a, self._fbo_bloom_b):
            if f is not None:
                f.release()
        tex_kw = dict(components=4, dtype="f1")
        self._fbo_scene = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((w, h), **tex_kw)]
        )
        self._fbo_bloom_a = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((w, h), **tex_kw)]
        )
        self._fbo_bloom_b = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((w, h), **tex_kw)]
        )

    def resize(self, width: int, height: int) -> None:
        self.width = max(64, width)
        self.height = max(64, height)
        self._resize_fbos()

    def _output_fbo(self, target: moderngl.Framebuffer | None) -> moderngl.Framebuffer:
        if target is not None:
            return target
        try:
            return self.ctx.detect_framebuffer()
        except Exception:
            return self.ctx.screen

    def _upload_draw(self, verts: np.ndarray, *, additive: bool = False) -> None:
        if verts.size == 0:
            return
        n = len(verts)
        packed = np.zeros((n, 6), dtype="f4")
        packed[:, 0] = verts["x"]
        packed[:, 1] = verts["y"]
        packed[:, 2:6] = np.stack([verts["r"], verts["g"], verts["b"], verts["a"]], axis=1)
        self._note_vbo.write(packed.tobytes())
        if additive:
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE
        else:
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self._note_vao.render(moderngl.TRIANGLES, vertices=n)

    def render(
        self,
        engine: VisualizerEngine,
        target: moderngl.Framebuffer | None = None,
    ) -> None:
        w, h = self.width, self.height
        self.ctx.viewport = (0, 0, w, h)

        scene = build_scene_meshes(
            engine.timeline,
            t_ql=engine.t_ql,
            window_ql=engine.window_ql,
            style_id=engine.style_id,
            track_colors=engine.track_colors,
            sustain_extend=engine.sustain_extend_ql,
            dt=1.0 / 60.0,
            viewport_w=w,
            viewport_h=h,
        )
        bloom = self.bloom_strength
        if scene.use_glow:
            bloom = max(bloom, 2.35 if engine.style_id == "cyber" else 2.0)

        self._fbo_scene.use()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.clear(0.04, 0.05, 0.07, 1.0)

        self._upload_draw(scene.lines)
        self._upload_draw(scene.keyboard)

        if scene.glow.size:
            self._upload_draw(scene.glow, additive=True)

        use_add = scene.use_additive
        self._upload_draw(scene.notes, additive=use_add)

        if use_add:
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self._draw_particles(engine, w, h)
        self.ctx.disable(moderngl.BLEND)

        self._bloom_pass(w, h)

        out = self._output_fbo(target)
        out.viewport = (0, 0, w, h)
        out.use()
        self.ctx.clear(0.04, 0.05, 0.07, 1.0)
        self._composite_prog["u_scene"].value = 0
        self._composite_prog["u_bloom"].value = 1
        self._composite_prog["u_bloom_strength"].value = bloom
        self._fbo_scene.color_attachments[0].use(location=0)
        self._fbo_bloom_b.color_attachments[0].use(location=1)
        self._screen_vao_comp.render(moderngl.TRIANGLES)

    def _draw_particles(self, engine: VisualizerEngine, w: int, h: int) -> None:
        parts = engine.particles.active_array()
        if len(parts) == 0:
            return
        n = len(parts)
        packed = np.zeros((n, 7), dtype="f4")
        t = parts["life"] / np.maximum(parts["max_life"], 0.001)
        packed[:, 0:2] = np.stack([parts["px"], parts["py"]], axis=1)
        packed[:, 2] = parts["size"] * (0.5 + 0.5 * t)
        packed[:, 3:7] = np.stack(
            [parts["r"], parts["g"], parts["b"], parts["a"] * t * 0.85], axis=1
        )
        self._particle_vbo.write(packed.tobytes())
        self._particle_prog["u_resolution"].value = (float(w), float(h))
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE
        self._particle_vao.render(moderngl.POINTS, vertices=n)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    def _bloom_pass(self, w: int, h: int) -> None:
        tex = self._fbo_scene.color_attachments[0]
        self._fbo_bloom_a.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        self._blur_prog["u_tex"].value = 0
        tex.use(location=0)
        self._blur_prog["u_dir"].value = (1.0, 0.0)
        self._blur_prog["u_texel"].value = (1.0 / max(w, 1), 1.0 / max(h, 1))
        self._screen_vao_blur.render(moderngl.TRIANGLES)

        self._fbo_bloom_b.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        self._fbo_bloom_a.color_attachments[0].use(location=0)
        self._blur_prog["u_dir"].value = (0.0, 1.0)
        self._screen_vao_blur.render(moderngl.TRIANGLES)

    def release(self) -> None:
        for f in (self._fbo_scene, self._fbo_bloom_a, self._fbo_bloom_b):
            if f is not None:
                f.release()
