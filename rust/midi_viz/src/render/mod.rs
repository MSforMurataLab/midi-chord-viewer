pub mod gpu_init;
pub mod layout;
pub mod particles;
pub mod renderer;
pub mod scene;
pub mod spectrum_anim;

pub use particles::ParticlePool;
pub use renderer::{WgpuRenderer, SPECTRUM_FLOATS};
pub use scene::{
    pack_frame, GpuNoteInstance, NoteSceneUniform, SceneParams, VisualStyle,
};
pub use spectrum_anim::SpectrumAnimator;
