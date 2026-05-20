# -*- coding: utf-8 -*-
"""GLSL 3.3 — グロー・パーティクル・ブルーム。"""

PASS_VS = """
#version 330 core
in vec2 in_pos;
in vec4 in_color;
out vec4 v_color;
void main() {
    gl_Position = vec4(in_pos, 0.0, 1.0);
    v_color = in_color;
}
"""

PASS_FS = """
#version 330 core
in vec4 v_color;
out vec4 fragColor;
void main() {
    float a = clamp(v_color.a, 0.0, 1.0);
    vec3 rgb = v_color.rgb * (0.85 + a * 0.55);
    rgb = pow(rgb, vec3(0.92));
    fragColor = vec4(rgb, a);
}
"""

PARTICLE_VS = """
#version 330 core
in vec2 in_pos;
in float in_size;
in vec4 in_color;
uniform vec2 u_resolution;
out vec4 v_color;
void main() {
    vec2 ndc = vec2(in_pos.x / u_resolution.x * 2.0 - 1.0,
                    1.0 - in_pos.y / u_resolution.y * 2.0);
    gl_Position = vec4(ndc, 0.0, 1.0);
    v_color = in_color;
    gl_PointSize = max(3.0, in_size * 2.2);
}
"""

PARTICLE_FS = """
#version 330 core
in vec4 v_color;
out vec4 fragColor;
void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float d = length(uv);
    float core = smoothstep(0.45, 0.0, d);
    float halo = smoothstep(0.5, 0.1, d) * 0.7;
    float a = (core + halo) * v_color.a;
    vec3 col = v_color.rgb * (1.0 + core * 2.0 + halo);
    fragColor = vec4(col, a);
}
"""

BLUR_FS = """
#version 330 core
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D u_tex;
uniform vec2 u_dir;
uniform vec2 u_texel;
void main() {
    vec4 sum = texture(u_tex, v_uv) * 0.227027;
    sum += texture(u_tex, v_uv + u_dir * u_texel) * 0.316216;
    sum += texture(u_tex, v_uv - u_dir * u_texel) * 0.316216;
    sum += texture(u_tex, v_uv + u_dir * u_texel * 2.0) * 0.070270;
    sum += texture(u_tex, v_uv - u_dir * u_texel * 2.0) * 0.070270;
    fragColor = sum;
}
"""

COMPOSITE_FS = """
#version 330 core
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D u_scene;
uniform sampler2D u_bloom;
uniform float u_bloom_strength;
void main() {
    vec3 scene = texture(u_scene, v_uv).rgb;
    vec3 bloom = texture(u_bloom, v_uv).rgb;
    vec3 col = scene + bloom * u_bloom_strength;
    fragColor = vec4(col, 1.0);
}
"""

SCREEN_VS = """
#version 330 core
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

LINE_FS = """
#version 330 core
in vec4 v_color;
out vec4 fragColor;
void main() {
    fragColor = vec4(v_color.rgb * 2.0, v_color.a);
}
"""
