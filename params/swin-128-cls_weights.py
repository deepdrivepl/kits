import numpy as np
from monai.networks.nets import SwinUNETR
from monai.losses import DiceCELoss
# from torch.nn import CrossEntropyLoss
import torch.optim
from torch import clamp

from monai.transforms import (
    Compose,
    LoadImaged,
    NormalizeIntensityd,
    # ScaleIntensityd,
    RandCropByPosNegLabeld,
    RandAffined,
    RandFlipd,
    RandGaussianNoised,
    RandGaussianSmoothd,
    RandScaleIntensityd,
    SpatialPadd,
    Spacingd,
    Orientationd,
    Lambdad
)


PARAMS = dict(
    epochs=100,
    exp_name="swin-128-cls_weights",
    acc_batch_size=4,
    patch_size=(128, 128, 128),
    num_samples=2,
    optimizer=torch.optim.RAdam,
    optimizer_params=dict(lr=1e-4, weight_decay=0),
    scheduler=torch.optim.lr_scheduler.OneCycleLR,
    scheduler_params=dict(
        max_lr=3e-4, div_factor=10, final_div_factor=100, pct_start=0.1
    ),
    accelerator="gpu",
    devices=2,
    precision=16,
    seed=2023,
    ckpt_monitor="val/Dice",
    log_every_n_batch=2,
    log_val_imgs=2,
    train_dataloader=dict(
        batch_size=2,
        shuffle=True,
        num_workers=10,
        pin_memory=True,
        prefetch_factor=2,
        persistent_workers=True,
    ),
    val_dataloader=dict(
        batch_size=1,
        num_workers=5,
        pin_memory=True,
        persistent_workers=True,
    ),
    # validation
    sw_batch_size=2,
    threshold=0.5,
    overlap=0.5
)


model_params = dict(
    img_size=PARAMS['patch_size'],
    in_channels=1,
    out_channels=4,
    feature_size=24
)

model = SwinUNETR(**model_params)


CLASS_WEIGHTS = (0.252, 39.577, 136.913, 1659.814)

def loss_function(outputs, labels):
    loss_fn = DiceCELoss(to_onehot_y=True, softmax=True, include_background=False,
                         ce_weight=torch.tensor(CLASS_WEIGHTS, device=outputs.device))
    loss = loss_fn(outputs, labels)

    return loss


def get_train_transforms():
    return Compose(
        [
            LoadImaged(
                keys=["image", "label"],
                image_only=True,
                ensure_channel_first=True,
            ),
            Orientationd(
                keys=["image", "label"],
                axcodes="RAS",
            ),
            Spacingd(
                keys=["image", "label"],
                pixdim=(1.0, 1.0, 1.0),
                mode=("bilinear", "nearest"),
            ),
            Lambdad(
                keys="image",
                func=lambda x: clamp(x, -200, 300),
            ),
            NormalizeIntensityd(
                keys="image",
                nonzero=True,
            ),
            # ScaleIntensityd(keys="image"),
            SpatialPadd(
                keys=("image", "label"),
                spatial_size=PARAMS["patch_size"],
            ),
            RandCropByPosNegLabeld(
                keys=("image", "label"),
                label_key="label",
                spatial_size=PARAMS["patch_size"],
                num_samples=PARAMS["num_samples"],
                image_key="image",
                allow_smaller=True,
                pos=5
            ),
            RandAffined(
                keys=("image", "label"),
                prob=0.75,
                rotate_range=(np.pi / 6, np.pi / 6),
                translate_range=(0.0625, 0.0625),
                scale_range=(0.1, 0.1),
            ),
            RandFlipd(
                keys=("image", "label"),
                spatial_axis=(0, 1, 2),
                prob=0.5,
            ),
            RandGaussianNoised(
                keys="image",
                prob=0.15,
                mean=0.0,
                std=0.1,
            ),
            RandGaussianSmoothd(
                keys="image",
                prob=0.15,
                sigma_x=(0.5, 1.15),
                sigma_y=(0.5, 1.15),
            ),
            RandScaleIntensityd(
                keys="image",
                factors=0.3,
                prob=0.1,
            ),
        ]
    )


def get_val_transforms():
    return Compose(
        [
            LoadImaged(
                keys=["image", "label"],
                image_only=True,
                ensure_channel_first=True,
            ),
            Orientationd(
                keys=["image", "label"],
                axcodes="RAS",
            ),
            Spacingd(
                keys=["image", "label"],
                pixdim=(1.0, 1.0, 1.0),
                mode=("bilinear", "nearest"),
            ),
            Lambdad(
                keys="image",
                func=lambda x: clamp(x, -200, 300),
            ),
            NormalizeIntensityd(
                keys="image",
                nonzero=True,
            ),
            # ScaleIntensityd(keys="image"),
        ]
    )
