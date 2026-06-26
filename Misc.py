# unwrap the list (batch_size=1), element may be None or a tensor
mask_item = mask[0] if isinstance(mask, list) else mask
if mask_item is not None:
    if torch.is_tensor(mask_item):
        m = mask_item.squeeze().numpy()
    else:
        m = np.array(mask_item)
    pixel_scores.append(amap.ravel())
    pixel_labels.append((m > 0).ravel().astype(int))
