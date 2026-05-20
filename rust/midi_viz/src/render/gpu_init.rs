//! wgpu アダプタ検出 — Windows / ノート PC / WARP フォールバック対応

use wgpu::{Adapter, Backends, DeviceType, Instance, InstanceDescriptor, PowerPreference, RequestAdapterOptions};

fn adapter_rank(adapter: &Adapter) -> u32 {
    let info = adapter.get_info();
    let type_rank = match info.device_type {
        DeviceType::DiscreteGpu => 500,
        DeviceType::IntegratedGpu => 400,
        DeviceType::VirtualGpu => 300,
        DeviceType::Cpu => 200,
        DeviceType::Other => 100,
    };
    type_rank
}

fn try_open_device(adapter: &Adapter) -> bool {
    let limits = [
        adapter.limits(),
        wgpu::Limits::downlevel_defaults(),
        wgpu::Limits::downlevel_webgl2_defaults(),
    ];
    for limits in limits {
        if pollster::block_on(adapter.request_device(
            &wgpu::DeviceDescriptor {
                label: Some("midi_viz_probe"),
                required_features: wgpu::Features::empty(),
                required_limits: limits,
                memory_hints: wgpu::MemoryHints::default(),
            },
            None,
        ))
        .is_ok()
        {
            return true;
        }
    }
    false
}

fn pick_from_enumerate(instance: &Instance, backends: Backends) -> Option<Adapter> {
    let mut adapters = instance.enumerate_adapters(backends);
    if adapters.is_empty() {
        return None;
    }
    adapters.sort_by_key(|a| std::cmp::Reverse(adapter_rank(a)));
    for adapter in adapters {
        if try_open_device(&adapter) {
            log::info!(
                "midi_viz: using adapter '{}' ({:?})",
                adapter.get_info().name,
                adapter.get_info().backend
            );
            return Some(adapter);
        }
    }
    None
}

fn pick_from_request(instance: &Instance) -> Option<Adapter> {
    const PREFS: [(PowerPreference, bool); 4] = [
        (PowerPreference::HighPerformance, true),
        (PowerPreference::LowPower, true),
        (PowerPreference::None, true),
        (PowerPreference::HighPerformance, false),
    ];
    for (power, force_fallback) in PREFS {
        let adapter = pollster::block_on(instance.request_adapter(&RequestAdapterOptions {
            power_preference: power,
            compatible_surface: None,
            force_fallback_adapter: force_fallback,
        }));
        if let Some(adapter) = adapter {
            if try_open_device(&adapter) {
                log::info!(
                    "midi_viz: request_adapter -> '{}' ({:?})",
                    adapter.get_info().name,
                    adapter.get_info().backend
                );
                return Some(adapter);
            }
        }
    }
    None
}

fn try_backends(backends: Backends, errors: &mut Vec<String>) -> Option<Adapter> {
    let instance = Instance::new(InstanceDescriptor {
        backends,
        ..Default::default()
    });
    if let Some(adapter) = pick_from_enumerate(&instance, backends) {
        return Some(adapter);
    }
    if let Some(adapter) = pick_from_request(&instance) {
        return Some(adapter);
    }
    errors.push(format!("{backends:?}: no adapter"));
    None
}

/// 利用可能な GPU / WARP / ソフトウェアアダプタを探す。
pub fn request_adapter() -> Result<Adapter, String> {
    let mut errors = Vec::new();

    #[cfg(target_os = "windows")]
    let backend_sets: &[Backends] = &[
        Backends::DX12,
        Backends::VULKAN,
        Backends::GL,
        Backends::DX12 | Backends::VULKAN,
        Backends::DX12 | Backends::GL,
        Backends::all(),
    ];

    #[cfg(not(target_os = "windows"))]
    let backend_sets: &[Backends] = &[Backends::VULKAN | Backends::GL, Backends::all()];

    for &backends in backend_sets {
        if let Some(adapter) = try_backends(backends, &mut errors) {
            return Ok(adapter);
        }
    }

    Err(format!(
        "wgpu アダプタが見つかりません。GPU ドライバを更新するか、\
         Windows のグラフィックス設定で高性能 GPU を選んでください。詳細: {}",
        errors.join("; ")
    ))
}

pub fn open_device(
    adapter: &Adapter,
) -> Result<(wgpu::Device, wgpu::Queue), String> {
    let limits = [
        adapter.limits(),
        wgpu::Limits::downlevel_defaults(),
        wgpu::Limits::downlevel_webgl2_defaults(),
    ];
    let mut last = String::new();
    for limits in limits {
        match pollster::block_on(adapter.request_device(
            &wgpu::DeviceDescriptor {
                label: Some("midi_viz"),
                required_features: wgpu::Features::empty(),
                required_limits: limits,
                memory_hints: wgpu::MemoryHints::default(),
            },
            None,
        )) {
            Ok(pair) => return Ok(pair),
            Err(e) => last = e.to_string(),
        }
    }
    Err(format!("wgpu request_device failed: {last}"))
}
