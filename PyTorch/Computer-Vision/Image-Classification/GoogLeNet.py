'''
"Going deeper with convolutions" (Szegedy et al., 2014):
https://arxiv.org/pdf/1409.4842.pdf
'''
from torch.nn import Module, Sequential, Conv2d, BatchNorm2d, ReLU, MaxPool2d, AdaptiveAvgPool2d, Dropout, Flatten, Linear
from torch.nn.init import kaiming_normal_, normal_, constant_


def ConvBlock(self, in_channels, out_channels, **kwargs):
    return Sequential(Conv2d(in_channels, out_channels, **kwargs),
                      BatchNorm2d(out_channels),
                      ReLU())


class InceptionModule(Module): 
    def __init__(self, in_channels, ch1x1, ch3x3red, ch3x3, ch5x5red, ch5x5, pool_proj):
        super().__init__()

        self.block1 = ConvBlock(in_channels, ch1x1, kernel_size=1)
        self.block2 = Sequential(ConvBlock(in_channels, ch3x3red, kernel_size=1),
                                 ConvBlock(ch3x3red, ch3x3, kernel_size=3, padding=1))
        self.block3 = Sequential(ConvBlock(in_channels, ch5x5red, kernel_size=1),
                                 ConvBlock(ch5x5red, ch5x5, kernel_size=3, padding=1))
        self.block4 = Sequential(MaxPool2d(kernel_size=3, stride=1, padding=1, ceil_mode=True),
                                 ConvBlock(in_channels, pool_proj, kernel_size=1))

    def forward(self, x):
        block1, block2, block3, block4 = self.block1(x), self.block2(x), self.block3(x), self.block4(x)
        return torch.cat([block1, block2, block3, block4], dim=1)


class GoogLeNet(Module):
    def __init__(self, in_channels=3, num_classes=1000):
        super().__init__()
        
        # Feature Extractor
        self.conv1    = ConvBlock(3, 64, kernel_size=7, stride=2, padding=3)
        self.maxpool1 = MaxPool2d(3, stride=2, ceil_mode=True)
        self.conv2    = ConvBlock(64, 64, kernel_size=1)
        self.conv3    = ConvBlock(64, 192, kernel_size=3, padding=1),
        self.maxpool3 = MaxPool2d(3, stride=2, ceil_mode=True)
        
        self.inception3a = InceptionModule(192, 64, 96, 128, 16, 32, 32)
        self.inception3b = InceptionModule(256, 128, 128, 192, 32, 96, 64)
        self.maxpool3    = MaxPool2d(3, stride=2, ceil_mode=True)

        self.inception4a = InceptionModule(480, 192, 96, 208, 16, 48, 64)
        self.inception4b = InceptionModule(512, 160, 112, 224, 24, 64, 64)
        self.inception4c = InceptionModule(512, 128, 128, 256, 24, 64, 64)
        self.inception4d = InceptionModule(512, 112, 144, 288, 32, 64, 64)
        self.inception4e = InceptionModule(528, 256, 160, 320, 32, 128, 128)
        self.maxpool4    = MaxPool2d(2, stride=2, ceil_mode=True)

        self.inception5a = InceptionModule(832, 256, 160, 320, 32, 128, 128)
        self.inception5b = InceptionModule(832, 384, 192, 384, 48, 128, 128)
        self.avgpool     = AdaptiveAvgPool2d(1)
        
        # Auxiliary Classifier 1    
        self.aux1 = Sequential(AdaptiveAvgPool2d(4),
                               ConvBlock(512, 128, kernel_size=1), Flatten(),
                               Linear(2048, 1024), ReLU(), Dropout(0.7),
                               Linear(1024, num_classes))
        
        # Auxiliary Classifier 2
        self.aux2 = Sequential(AdaptiveAvgPool2d(4),
                               ConvBlock(528, 128, kernel_size=1), Flatten(),
                               Linear(2048, 1024), ReLU(), Dropout(0.7),
                               Linear(1024, num_classes))
        
        # Classifier
        self.fc = Sequential(Flatten(), Dropout(0.4), Linear(1024, num_classes))

        # Weight Initialization
        for module in self.modules():
            if isinstance(module, Conv2d):
                kaiming_normal_(module.weight, mode='fan_out', nonlinearity='relu')
                constant_(module.bias, 0)
            elif isinstance(module, BatchNorm2d):
                constant_(module.weight, 1)
                constant_(module.bias, 0)
            elif isinstance(module, Linear):
                normal_(module.weight, std=0.01)
                constant_(module.bias, 0)
                    
    def forward(self, x):
        ext = self.conv1(x)
        ext = self.maxpool1(ext)
        ext = self.conv2(ext)
        ext = self.conv3(ext)
        ext = self.maxpool2(ext)
        
        ext = self.inception3a(ext)
        ext = self.inception3b(ext)
        ext = self.maxpool3(ext)
        
        ext = self.inception4a(ext)
        aux1 = self.aux1(ext)
        ext = self.inception4b(ext)
        ext = self.inception4c(ext)
        ext = self.inception4d(ext)
        aux2 = self.aux2(ext)
        ext = self.inception4e(ext)
        ext = self.maxpool4(ext)
        
        ext = self.inception5a(ext)
        ext = self.inception5b(ext)
        ext = self.avgpool(ext)
        
        cls = self.fc(ext)
        return cls, aux2, aux1 # aux losses are weighted by 0.3
