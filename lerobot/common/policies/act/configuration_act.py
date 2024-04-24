from dataclasses import dataclass, field


@dataclass
class ActionChunkingTransformerConfig:
    """Configuration class for the Action Chunking Transformers policy.

    Defaults are configured for training on bimanual Aloha tasks like "insertion" or "transfer".

    The parameters you will most likely need to change are the ones which depend on the environment / sensors.
    Those are: `state_dim`, `action_dim` and `camera_names`.

    Args:
        state_dim: Dimensionality of the observation state space (excluding images).
        action_dim: Dimensionality of the action space.
        n_obs_steps: Number of environment steps worth of observations to pass to the policy (takes the
            current step and additional steps going back).
        camera_names: The (unique) set of names for the cameras.
        chunk_size: The size of the action prediction "chunks" in units of environment steps.
        n_action_steps: The number of action steps to run in the environment for one invocation of the policy.
            This should be no greater than the chunk size. For example, if the chunk size size 100, you may
            set this to 50. This would mean that the model predicts 100 steps worth of actions, runs 50 in the
            environment, and throws the other 50 out.
        input_shapes: A dictionary defining the shapes of the input data for the policy.
            The key represents the input data name, and the value is a list indicating the dimensions
            of the corresponding data. For example, "observation.images.top" refers to an input from the
            "top" camera with dimensions [3, 96, 96], indicating it has three color channels and 96x96 resolution.
            Importantly, shapes doesnt include batch dimension or temporal dimension.
        output_shapes: A dictionary defining the shapes of the output data for the policy.
            The key represents the output data name, and the value is a list indicating the dimensions
            of the corresponding data. For example, "action" refers to an output shape of [14], indicating
            14-dimensional actions. Importantly, shapes doesnt include batch dimension or temporal dimension.
        normalize_input_modes: A dictionary specifying the normalization mode to be applied to various inputs.
            The key represents the input data name, and the value specifies the type of normalization to apply.
            Common normalization methods include "mean_std" (mean and standard deviation) or "min_max" (to normalize
            between -1 and 1).
        unnormalize_output_modes: A dictionary specifying the method to unnormalize outputs.
            This parameter maps output data types to their unnormalization modes, allowing the results to be
            transformed back from a normalized state to a standard state. It is typically used when output
            data needs to be interpreted in its original scale or units. For example, for "action", the
            unnormalization mode might be "mean_std" or "min_max".
        vision_backbone: Name of the torchvision resnet backbone to use for encoding images.
        use_pretrained_backbone: Whether the backbone should be initialized with pretrained weights from
            torchvision.
        replace_final_stride_with_dilation: Whether to replace the ResNet's final 2x2 stride with a dilated
            convolution.
        pre_norm: Whether to use "pre-norm" in the transformer blocks.
        d_model: The transformer blocks' main hidden dimension.
        n_heads: The number of heads to use in the transformer blocks' multi-head attention.
        dim_feedforward: The dimension to expand the transformer's hidden dimension to in the feed-forward
            layers.
        feedforward_activation: The activation to use in the transformer block's feed-forward layers.
        n_encoder_layers: The number of transformer layers to use for the transformer encoder.
        n_decoder_layers: The number of transformer layers to use for the transformer decoder.
        use_vae: Whether to use a variational objective during training. This introduces another transformer
            which is used as the VAE's encoder (not to be confused with the transformer encoder - see
            documentation in the policy class).
        latent_dim: The VAE's latent dimension.
        n_vae_encoder_layers: The number of transformer layers to use for the VAE's encoder.
        use_temporal_aggregation: Whether to blend the actions of multiple policy invocations for any given
            environment step.
        dropout: Dropout to use in the transformer layers (see code for details).
        kl_weight: The weight to use for the KL-divergence component of the loss if the variational objective
            is enabled. Loss is then calculated as: `reconstruction_loss + kl_weight * kld_loss`.
    """

    # Environment.
    # TODO(rcadene, alexander-soar): remove these as they are defined in input_shapes, output_shapes
    state_dim: int = 14
    action_dim: int = 14

    # Inputs / output structure.
    n_obs_steps: int = 1
    camera_names: tuple[str] = ("top",)
    chunk_size: int = 100
    n_action_steps: int = 100

    input_shapes: dict[str, str] = field(
        default_factory=lambda: {
            "observation.images.top": [3, 480, 640],
            "observation.state": [14],
        }
    )
    output_shapes: dict[str, str] = field(
        default_factory=lambda: {
            "action": [14],
        }
    )

    # Normalization / Unnormalization
    normalize_input_modes: dict[str, str] = field(
        default_factory=lambda: {
            "observation.image": "mean_std",
            "observation.state": "mean_std",
        }
    )
    unnormalize_output_modes: dict[str, str] = field(
        default_factory=lambda: {
            "action": "mean_std",
        }
    )

    # Architecture.
    # Vision backbone.
    vision_backbone: str = "resnet18"
    use_pretrained_backbone: bool = True
    replace_final_stride_with_dilation: int = False
    # Transformer layers.
    pre_norm: bool = False
    d_model: int = 512
    n_heads: int = 8
    dim_feedforward: int = 3200
    feedforward_activation: str = "relu"
    n_encoder_layers: int = 4
    n_decoder_layers: int = 1
    # VAE.
    use_vae: bool = True
    latent_dim: int = 32
    n_vae_encoder_layers: int = 4

    # Inference.
    use_temporal_aggregation: bool = False

    # Training and loss computation.
    dropout: float = 0.1
    kl_weight: float = 10.0

    # ---
    # TODO(alexander-soare): Remove these from the policy config.
    batch_size: int = 8
    lr: float = 1e-5
    lr_backbone: float = 1e-5
    weight_decay: float = 1e-4
    grad_clip_norm: float = 10
    utd: int = 1

    def __post_init__(self):
        """Input validation (not exhaustive)."""
        if not self.vision_backbone.startswith("resnet"):
            raise ValueError(
                f"`vision_backbone` must be one of the ResNet variants. Got {self.vision_backbone}."
            )
        if self.use_temporal_aggregation:
            raise NotImplementedError("Temporal aggregation is not yet implemented.")
        if self.n_action_steps > self.chunk_size:
            raise ValueError(
                f"The chunk size is the upper bound for the number of action steps per model invocation. Got "
                f"{self.n_action_steps} for `n_action_steps` and {self.chunk_size} for `chunk_size`."
            )
        if self.n_obs_steps != 1:
            raise ValueError(
                f"Multiple observation steps not handled yet. Got `nobs_steps={self.n_obs_steps}`"
            )
        if self.camera_names != ["top"]:
            raise ValueError(f"For now, `camera_names` can only be ['top']. Got {self.camera_names}.")
        if len(set(self.camera_names)) != len(self.camera_names):
            raise ValueError(f"`camera_names` should not have any repeated entries. Got {self.camera_names}.")