import torch
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
from PIL import Image
import numpy as np
import h5py
import os


class NYUDataset(Dataset):
    def __init__(self, root, type):
        self.raw_size = (480, 640)
        self.output_size = (257, 353)
        
        self.classes, self.class_to_idx = self.find_classes(root)
        self.imgs = self.make_dataset(root, self.class_to_idx)
        assert len(self.imgs) > 0, "Found 0 images in subfolders of: " + root + "\n"
        print("Found {} images in {} folder.".format(len(self.imgs), type))
        if type == 'train':
            self.transform = self.train_transform
        else:
            self.transform = self.test_transform
            
    def find_classes(self, dir):
        classes = [d for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]
        classes.sort()
        class_to_idx = {classes[i]: i for i in range(len(classes))}
        return classes, class_to_idx


    def make_dataset(self, dir, class_to_idx):
        images = []
        dir = os.path.expanduser(dir)
        for target in sorted(os.listdir(dir)):
            d = os.path.join(dir, target)
            if not os.path.isdir(d):
                continue
            for root, _, fnames in sorted(os.walk(d)):
                for fname in sorted(fnames):
                    if fname.endswith('.h5'):
                        path = os.path.join(root, fname)
                        item = (path, class_to_idx[target])
                        images.append(item)
        return images

    def train_transform(self, rgb, depth):
        """
        Train data augmentation. For details see the DORN paper.
        """
        s = np.random.uniform(1.0, 1.5)  # random scaling factor

        # data augmentations
        transform = T.Compose([
            T.Resize((288, 384)),  # for computational efficiency
            T.RandomRotation(5),
            T.Resize(round(288 * s)),
            T.RandomCrop((257, 353)),
            T.RandomHorizontalFlip()
        ])
        color_jitter = T.ColorJitter(0.4, 0.4, 0.4) # only for RGB
        to_tensor = T.ToTensor()

        rgb = transform(rgb)
        rgb = color_jitter(rgb)
        rgb = to_tensor(rgb)

        depth = transform(depth)
        depth = to_tensor(depth)
        depth /= s # preserves world-space geometry of the scene

        return rgb, depth

    def test_transform(self, rgb, depth):
        """
        Test data augmentation. For details see the DORN paper.
        """
        # data augmentations
        transform = T.Compose([
            T.Resize((288, 384)),
            T.CenterCrop((257, 353)),
            T.ToTensor()
        ])

        rgb = transform(rgb)
        depth = transform(depth)

        return rgb, depth
    
    def __getitem__(self, index):
        path, target = self.imgs[index]
        
        h5f = h5py.File(path, "r")
        rgb = Image.fromarray(np.array(h5f['rgb']).transpose((1, 2, 0)), 'RGB')
        depth = Image.fromarray(np.array(h5f['depth']), 'F')
        
        rgb, depth = self.transform(rgb, depth)
        return rgb, depth

    def __len__(self):
        return len(self.imgs)
    

def get_dataloaders(dataset, data_path, bs, bs_test):
    if dataset == 'nyu':
        train_set = NYUDataset(os.path.join(data_path, 'train'), type='train')
        test_set = NYUDataset(os.path.join(data_path, 'val'), type='val')
    else:
        print('Not implemented for dataset', dataset)
        raise NotImplementedError

    train_loader = DataLoader(train_set, batch_size=bs, shuffle=True, num_workers=10, pin_memory=True)
    test_loader = DataLoader(test_set, batch_size=bs_test, shuffle=False, num_workers=10, pin_memory=True)
    return train_loader, test_loader