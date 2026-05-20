//! wgpu オフスクリーン・レンダラー — Qt HWND 不要、RGBA readback

use std::sync::Arc;

use bytemuck::{Pod, Zeroable};
use wgpu::util::DeviceExt;

use super::gpu_init;
use super::particles::{GpuParticle, MAX_PARTICLES};
use super::scene::{GpuNoteInstance, NoteSceneUniform};

const TARGET_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Rgba8Unorm;
pub const SPECTRUM_FLOATS: usize = 128 * 3;

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct SimParams {
    dt: f32,
    gravity: f32,
    drag: f32,
    amount: f32,
}

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct DrawUniforms {
    resolution: [f32; 2],
    aspect: f32,
    _pad: f32,
}

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct EmitUniform {
    resolution: [f32; 2],
    kb_ratio: f32,
    aspect: f32,
    y_lo: f32,
    y_hi: f32,
    x0: f32,
    x1: f32,
    t_ql: f32,
    style: f32,
    frame_seed: f32,
    amount_scale: f32,
}

pub struct WgpuRenderer {
    device: Arc<wgpu::Device>,
    queue: Arc<wgpu::Queue>,
    width: u32,
    height: u32,
    target: wgpu::Texture,
    target_view: wgpu::TextureView,
    readback: wgpu::Buffer,
    bytes_per_row_padded: u32,
    note_pipeline: wgpu::RenderPipeline,
    note_uniform: wgpu::Buffer,
    note_bind: wgpu::BindGroup,
    instance_buffer: wgpu::Buffer,
    quad_vertex: wgpu::Buffer,
    compute_pipeline: wgpu::ComputePipeline,
    particle_buffer: wgpu::Buffer,
    sim_uniform: wgpu::Buffer,
    compute_bind: wgpu::BindGroup,
    particle_pipeline: wgpu::RenderPipeline,
    draw_uniform: wgpu::Buffer,
    draw_bind: wgpu::BindGroup,
    spectrum_storage: wgpu::Buffer,
    note_vel_prev: wgpu::Buffer,
    note_vel_curr: wgpu::Buffer,
    spawn_atomic: wgpu::Buffer,
    emit_uniform: wgpu::Buffer,
    emit_bind: wgpu::BindGroup,
    emit_pipeline: wgpu::ComputePipeline,
    instance_count: u32,
}

impl WgpuRenderer {
    pub fn new(width: u32, height: u32) -> Result<Self, String> {
        let width = width.max(64);
        let height = height.max(64);

        let adapter = gpu_init::request_adapter()?;
        let (device, queue) = gpu_init::open_device(&adapter)?;

        let device = Arc::new(device);
        let queue = Arc::new(queue);

        let note_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("note"),
            source: wgpu::ShaderSource::Wgsl(include_str!("shaders/note.wgsl").into()),
        });

        let note_uniform = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("note_scene_uniform"),
            contents: bytemuck::bytes_of(&NoteSceneUniform {
                aspect: width as f32 / height as f32,
                t_ql: 0.0,
                window_ql: 8.0,
                kb_ratio: 0.14,
                x0: 0.0,
                x1: 8.0,
                duration_ql: 8.0,
                sustain_extend: 0.0,
                y_lo: 21.0,
                y_hi: 108.0,
                style: 0.0,
                track_colors: 1.0,
                style_prev: 0.0,
                style_blend: 0.0,
            }),
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
        });

        let spectrum_storage = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("spectrum_storage"),
            size: (SPECTRUM_FLOATS * std::mem::size_of::<f32>()) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let note_bind_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("note_bind"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::VERTEX_FRAGMENT,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::VERTEX,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
            ],
        });

        let note_bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("note_bind"),
            layout: &note_bind_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: note_uniform.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: spectrum_storage.as_entire_binding(),
                },
            ],
        });

        // TriangleStrip: BL → BR → TL → TR
        let quad_vertex = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("quad"),
            contents: bytemuck::cast_slice(&[
                [-1.0f32, -1.0],
                [1.0, -1.0],
                [-1.0, 1.0],
                [1.0, 1.0],
            ]),
            usage: wgpu::BufferUsages::VERTEX,
        });

        let instance_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("instances"),
            size: (std::mem::size_of::<GpuNoteInstance>() * 65536) as u64,
            usage: wgpu::BufferUsages::VERTEX | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let note_pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("note_pl"),
            bind_group_layouts: &[&note_bind_layout],
            push_constant_ranges: &[],
        });

        let note_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("note_pipeline"),
            layout: Some(&note_pipeline_layout),
            vertex: wgpu::VertexState {
                module: &note_shader,
                entry_point: Some("vs_main"),
                buffers: &[
                    wgpu::VertexBufferLayout {
                        array_stride: 8,
                        step_mode: wgpu::VertexStepMode::Vertex,
                        attributes: &[wgpu::VertexAttribute {
                            format: wgpu::VertexFormat::Float32x2,
                            offset: 0,
                            shader_location: 0,
                        }],
                    },
                    wgpu::VertexBufferLayout {
                        array_stride: std::mem::size_of::<GpuNoteInstance>() as u64,
                        step_mode: wgpu::VertexStepMode::Instance,
                        attributes: &[
                            wgpu::VertexAttribute {
                                format: wgpu::VertexFormat::Float32x4,
                                offset: 0,
                                shader_location: 1,
                            },
                            wgpu::VertexAttribute {
                                format: wgpu::VertexFormat::Float32x4,
                                offset: 16,
                                shader_location: 2,
                            },
                        ],
                    },
                ],
                compilation_options: Default::default(),
            },
            fragment: Some(wgpu::FragmentState {
                module: &note_shader,
                entry_point: Some("fs_main"),
                targets: &[Some(wgpu::ColorTargetState {
                    format: TARGET_FORMAT,
                    blend: Some(wgpu::BlendState {
                        color: wgpu::BlendComponent {
                            src_factor: wgpu::BlendFactor::SrcAlpha,
                            dst_factor: wgpu::BlendFactor::One,
                            operation: wgpu::BlendOperation::Add,
                        },
                        alpha: wgpu::BlendComponent::OVER,
                    }),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
                compilation_options: Default::default(),
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleStrip,
                ..Default::default()
            },
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
            cache: None,
        });

        let compute_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("particle_compute"),
            source: wgpu::ShaderSource::Wgsl(include_str!("shaders/particle_compute.wgsl").into()),
        });
        let emit_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("particle_emit"),
            source: wgpu::ShaderSource::Wgsl(include_str!("shaders/particle_emit.wgsl").into()),
        });
        let draw_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("particle_draw"),
            source: wgpu::ShaderSource::Wgsl(include_str!("shaders/particle_draw.wgsl").into()),
        });

        let particle_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("particles"),
            size: (std::mem::size_of::<GpuParticle>() * MAX_PARTICLES) as u64,
            usage: wgpu::BufferUsages::STORAGE
                | wgpu::BufferUsages::VERTEX
                | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let sim_uniform = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("sim"),
            contents: bytemuck::bytes_of(&SimParams {
                dt: 1.0 / 60.0,
                gravity: 220.0,
                drag: 1.8,
                amount: 1.0,
            }),
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
        });

        let compute_bind_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("compute"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: false },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
            ],
        });

        let compute_bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("compute_bind"),
            layout: &compute_bind_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: particle_buffer.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: sim_uniform.as_entire_binding(),
                },
            ],
        });

        let compute_pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("compute"),
            layout: Some(
                &device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                    bind_group_layouts: &[&compute_bind_layout],
                    ..Default::default()
                }),
            ),
            module: &compute_shader,
            entry_point: Some("physics_main"),
            compilation_options: Default::default(),
            cache: None,
        });

        let zeros128: [f32; 128] = [0.0; 128];
        let note_vel_prev = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("note_vel_prev"),
            contents: bytemuck::cast_slice(&zeros128),
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
        });
        let note_vel_curr = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("note_vel_curr"),
            contents: bytemuck::cast_slice(&zeros128),
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
        });

        let spawn_atomic = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("spawn_atomic"),
            contents: &0u32.to_le_bytes(),
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
        });

        let emit_uniform = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("emit_uniform"),
            contents: bytemuck::bytes_of(&EmitUniform {
                resolution: [width as f32, height as f32],
                kb_ratio: 0.14,
                aspect: width as f32 / height as f32,
                y_lo: 21.0,
                y_hi: 108.0,
                x0: 0.0,
                x1: 8.0,
                t_ql: 0.0,
                style: 0.0,
                frame_seed: 0.0,
                amount_scale: 1.0,
            }),
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
        });

        let emit_bind_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("emit_bind"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: false },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 2,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 3,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: false },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 4,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
            ],
        });

        let emit_bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("emit_bind"),
            layout: &emit_bind_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: particle_buffer.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: note_vel_curr.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: note_vel_prev.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 3,
                    resource: spawn_atomic.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 4,
                    resource: emit_uniform.as_entire_binding(),
                },
            ],
        });

        let emit_pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("emit"),
            layout: Some(
                &device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                    bind_group_layouts: &[&emit_bind_layout],
                    ..Default::default()
                }),
            ),
            module: &emit_shader,
            entry_point: Some("emit_main"),
            compilation_options: Default::default(),
            cache: None,
        });

        let draw_uniform = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("draw_u"),
            contents: bytemuck::bytes_of(&DrawUniforms {
                resolution: [width as f32, height as f32],
                aspect: width as f32 / height as f32,
                _pad: 0.0,
            }),
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
        });

        let draw_bind_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("draw"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::VERTEX,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::VERTEX,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
            ],
        });

        let draw_bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("draw_bind"),
            layout: &draw_bind_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: particle_buffer.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: draw_uniform.as_entire_binding(),
                },
            ],
        });

        let particle_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("particles"),
            layout: Some(
                &device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                    bind_group_layouts: &[&draw_bind_layout],
                    ..Default::default()
                }),
            ),
            vertex: wgpu::VertexState {
                module: &draw_shader,
                entry_point: Some("vs_main"),
                buffers: &[],
                compilation_options: Default::default(),
            },
            fragment: Some(wgpu::FragmentState {
                module: &draw_shader,
                entry_point: Some("fs_main"),
                targets: &[Some(wgpu::ColorTargetState {
                    format: TARGET_FORMAT,
                    blend: Some(wgpu::BlendState::ALPHA_BLENDING),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
                compilation_options: Default::default(),
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleStrip,
                ..Default::default()
            },
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
            cache: None,
        });

        let (target, target_view, readback, bytes_per_row_padded) =
            Self::create_target(&device, width, height)?;

        Ok(Self {
            device,
            queue,
            width,
            height,
            target,
            target_view,
            readback,
            bytes_per_row_padded,
            note_pipeline,
            note_uniform,
            note_bind,
            instance_buffer,
            quad_vertex,
            compute_pipeline,
            particle_buffer,
            sim_uniform,
            compute_bind,
            particle_pipeline,
            draw_uniform,
            draw_bind,
            spectrum_storage,
            note_vel_prev,
            note_vel_curr,
            spawn_atomic,
            emit_uniform,
            emit_bind,
            emit_pipeline,
            instance_count: 0,
        })
    }

    /// 曲読み込み・スタイル変更時のみ呼ぶ（毎フレームでは呼ばない）
    pub fn upload_instances(&mut self, instances: &[GpuNoteInstance]) {
        self.instance_count = instances.len().min(65536) as u32;
        if self.instance_count > 0 {
            self.queue.write_buffer(
                &self.instance_buffer,
                0,
                bytemuck::cast_slice(instances),
            );
        }
    }

    fn create_target(
        device: &wgpu::Device,
        width: u32,
        height: u32,
    ) -> Result<(wgpu::Texture, wgpu::TextureView, wgpu::Buffer, u32), String> {
        let target = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("color_target"),
            size: wgpu::Extent3d {
                width,
                height,
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: TARGET_FORMAT,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
            view_formats: &[],
        });
        let target_view = target.create_view(&wgpu::TextureViewDescriptor::default());

        let unpadded = width * 4;
        let align = wgpu::COPY_BYTES_PER_ROW_ALIGNMENT;
        let bytes_per_row_padded = (unpadded + align - 1) / align * align;
        let readback_size = (bytes_per_row_padded * height) as u64;

        let readback = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("readback"),
            size: readback_size,
            usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
            mapped_at_creation: false,
        });

        Ok((target, target_view, readback, bytes_per_row_padded))
    }

    pub fn resize(&mut self, width: u32, height: u32) {
        if width < 64 || height < 64 {
            return;
        }
        if width == self.width && height == self.height {
            return;
        }
        self.width = width;
        self.height = height;
        if let Ok((t, v, b, p)) = Self::create_target(&self.device, width, height) {
            self.target = t;
            self.target_view = v;
            self.readback = b;
            self.bytes_per_row_padded = p;
        }
        let aspect = width as f32 / height as f32;
        self.queue.write_buffer(
            &self.note_uniform,
            0,
            bytemuck::bytes_of(&NoteSceneUniform {
                aspect,
                style_prev: 0.0,
                style_blend: 0.0,
                ..Default::default()
            }),
        );
        self.queue.write_buffer(
            &self.draw_uniform,
            0,
            bytemuck::bytes_of(&DrawUniforms {
                resolution: [width as f32, height as f32],
                aspect,
                _pad: 0.0,
            }),
        );
    }

    pub fn render(
        &mut self,
        scene: &NoteSceneUniform,
        spectrum: &[f32; SPECTRUM_FLOATS],
        note_vel_curr: &[f32; 128],
        note_vel_prev: &[f32; 128],
        frame_seed: f32,
        emit_amount_scale: f32,
    ) -> Result<Vec<u8>, String> {
        let view = &self.target_view;

        self.queue
            .write_buffer(&self.note_uniform, 0, bytemuck::bytes_of(scene));
        self.queue.write_buffer(
            &self.spectrum_storage,
            0,
            bytemuck::cast_slice(spectrum.as_slice()),
        );
        self.queue
            .write_buffer(&self.note_vel_curr, 0, bytemuck::cast_slice(note_vel_curr));
        self.queue
            .write_buffer(&self.note_vel_prev, 0, bytemuck::cast_slice(note_vel_prev));

        let kb = scene.kb_ratio;
        let aspect = scene.aspect;
        self.queue.write_buffer(
            &self.emit_uniform,
            0,
            bytemuck::bytes_of(&EmitUniform {
                resolution: [self.width as f32, self.height as f32],
                kb_ratio: kb,
                aspect,
                y_lo: scene.y_lo,
                y_hi: scene.y_hi,
                x0: scene.x0,
                x1: scene.x1,
                t_ql: scene.t_ql,
                style: scene.style,
                frame_seed,
                amount_scale: emit_amount_scale,
            }),
        );

        self.queue.write_buffer(&self.spawn_atomic, 0, &0u32.to_le_bytes());

        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("frame"),
            });

        {
            let mut cpass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("emit"),
                ..Default::default()
            });
            cpass.set_pipeline(&self.emit_pipeline);
            cpass.set_bind_group(0, &self.emit_bind, &[]);
            cpass.dispatch_workgroups(1, 1, 1);
        }

        {
            let mut cpass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("particles_sim"),
                ..Default::default()
            });
            cpass.set_pipeline(&self.compute_pipeline);
            cpass.set_bind_group(0, &self.compute_bind, &[]);
            let groups = ((MAX_PARTICLES as u32) + 255) / 256;
            cpass.dispatch_workgroups(groups.max(1), 1, 1);
        }

        {
            let mut rpass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("main"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color {
                            r: 0.04,
                            g: 0.05,
                            b: 0.07,
                            a: 1.0,
                        }),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });

            if self.instance_count > 0 {
                rpass.set_pipeline(&self.note_pipeline);
                rpass.set_bind_group(0, &self.note_bind, &[]);
                rpass.set_vertex_buffer(0, self.quad_vertex.slice(..));
                rpass.set_vertex_buffer(1, self.instance_buffer.slice(..));
                rpass.draw(0..4, 0..self.instance_count);
            }

            rpass.set_pipeline(&self.particle_pipeline);
            rpass.set_bind_group(0, &self.draw_bind, &[]);
            rpass.draw(0..4, 0..MAX_PARTICLES as u32);
        }

        encoder.copy_texture_to_buffer(
            wgpu::ImageCopyTexture {
                texture: &self.target,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            wgpu::ImageCopyBuffer {
                buffer: &self.readback,
                layout: wgpu::ImageDataLayout {
                    offset: 0,
                    bytes_per_row: Some(self.bytes_per_row_padded),
                    rows_per_image: Some(self.height),
                },
            },
            wgpu::Extent3d {
                width: self.width,
                height: self.height,
                depth_or_array_layers: 1,
            },
        );

        self.queue.submit(Some(encoder.finish()));
        self.readback_rgba()
    }

    fn readback_rgba(&self) -> Result<Vec<u8>, String> {
        let unpadded = self.width * 4;
        let padded = self.bytes_per_row_padded;
        let slice = self.readback.slice(..);
        let (tx, rx) = std::sync::mpsc::channel();
        slice.map_async(wgpu::MapMode::Read, move |r| {
            let _ = tx.send(r);
        });
        self.device.poll(wgpu::Maintain::Wait);
        rx.recv()
            .map_err(|_| "readback channel closed".to_string())?
            .map_err(|e| format!("buffer map failed: {e:?}"))?;

        let mapped = slice.get_mapped_range();
        let mut rgba = vec![0u8; (self.width * self.height * 4) as usize];
        for y in 0..self.height {
            let src = (y * padded) as usize;
            let dst = (y * unpadded) as usize;
            rgba[dst..dst + unpadded as usize]
                .copy_from_slice(&mapped[src..src + unpadded as usize]);
        }
        drop(mapped);
        self.readback.unmap();
        Ok(rgba)
    }
}
