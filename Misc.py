from torch.utils.data.dataloader import default_collate

def collate_fn(batch):
    """Handle None masks — keeps them as a list instead of trying to stack."""
    images = default_collate([b["image"] for b in batch])
    labels = default_collate([b["label"] for b in batch])
    paths  = [b["image_path"] for b in batch]
    masks  = [b["mask"] for b in batch]  # list, may contain None
    return {"image": images, "label": labels, "image_path": paths, "mask": masks}


def get_dataloaders(root, transform_train, transform_test,
                    mask_transform=None, batch_size=32, num_workers=4):
    train_ds = AutoVIDataset(root, "train", transform=transform_train)
    test_ds  = AutoVIDataset(root, "test",  transform=transform_test,
                             mask_transform=mask_transform)

    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True, drop_last=False,
        collate_fn=collate_fn,
    )
    test_loader = DataLoader(
        test_ds, batch_size=1, shuffle=False,
        num_workers=num_workers, pin_memory=True,
        collate_fn=collate_fn,
    )
    return train_loader, test_loader
