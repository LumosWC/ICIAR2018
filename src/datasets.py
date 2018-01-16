import os
import glob
import torch
import numpy as np
from PIL import Image
from torch.utils.data import Dataset
from torchvision.transforms import transforms
from .patch_extractor import PatchExtractor

LABELS = ['Normal', 'Benign', 'InSitu', 'Invasive']
IMAGE_SIZE = (2048, 1536)
PATCH_SIZE = 512


class PatchWiseDataset(Dataset):
    def __init__(self, path, stride=PATCH_SIZE, rotate=False, flip=False):
        super().__init__()

        wp = int((IMAGE_SIZE[0] - PATCH_SIZE) / stride + 1)
        hp = int((IMAGE_SIZE[1] - PATCH_SIZE) / stride + 1)
        labels = {name: index for index in range(len(LABELS)) for name in glob.glob(path + '/' + LABELS[index] + '/*.tif')}

        self.path = path
        self.stride = stride
        self.labels = labels
        self.names = list(sorted(labels.keys()))
        self.shape = (len(labels), wp, hp, (4 if rotate else 1), (2 if flip else 1))  # (files, x_patches, y_patches, rotations, flip)

    def __getitem__(self, index):
        im, xpatch, ypatch, rotation, flip = np.unravel_index(index, self.shape)

        with Image.open(self.names[im]) as img:
            extractor = PatchExtractor(img=img, patch_size=PATCH_SIZE, stride=self.stride)
            patch = extractor.extract_patch((xpatch, ypatch))

            if rotation != 0:
                patch = patch.rotate(rotation * 90)

            if flip != 0:
                patch = patch.transpose(Image.FLIP_LEFT_RIGHT)

            label = self.labels[self.names[im]]

            return transforms.ToTensor()(patch), label

    def __len__(self):
        return np.prod(self.shape)


class ImageWiseDataset(Dataset):
    def __init__(self, path, stride=PATCH_SIZE, flip=False):
        super().__init__()

        labels = {name: index for index in range(len(LABELS)) for name in glob.glob(path + '/' + LABELS[index] + '/*.tif')}

        self.path = path
        self.stride = stride
        self.labels = labels
        self.names = list(sorted(labels.keys()))
        self.shape = (len(labels), (2 if flip else 1), (2 if flip else 1))  # (files, x_patches, y_patches, h_flip, v_flip)

    def __getitem__(self, index):
        im, h_flip, v_flip = np.unravel_index(index, self.shape)

        with Image.open(self.names[im]) as img:

            if h_flip != 0:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)

            if v_flip != 0:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

            extractor = PatchExtractor(img=img, patch_size=PATCH_SIZE, stride=self.stride)
            patches = extractor.extract_patches()

            label = self.labels[self.names[im]]

            b = torch.zeros((len(patches), 3, PATCH_SIZE, PATCH_SIZE))
            for i in range(len(patches)):
                b[i] = transforms.ToTensor()(patches[i])

            return b, label

    def __len__(self):
        return np.prod(self.shape)


class TestDataset(Dataset):
    def __init__(self, path, stride=PATCH_SIZE):
        super().__init__()

        if os.path.isdir(path):
            names = [name for name in glob.glob(path + '/*.tif')]
        else:
            names = [path]

        self.path = path
        self.stride = stride
        self.names = list(sorted(names))

    def __getitem__(self, index):
        file = self.names[index]
        with Image.open(file) as img:
            extractor = PatchExtractor(img=img, patch_size=PATCH_SIZE, stride=self.stride)
            patches = extractor.extract_patches()

            b = torch.zeros((len(patches), 3, PATCH_SIZE, PATCH_SIZE))
            for i in range(len(patches)):
                b[i] = transforms.ToTensor()(patches[i])

            return b, file

    def __len__(self):
        return len(self.names)
