import torch.nn as nn
import torch

def normalize_img(img):
    if torch.max(img) > 1 or torch.min(img) < 0:
        # img: b x c x h x w
        b, c, h, w = img.shape
        temp_img = img.view(b, c, h*w)
        im_max = torch.max(temp_img, dim=2)[0].view(b, c, 1)
        im_min = torch.min(temp_img, dim=2)[0].view(b, c, 1)

        temp_img = (temp_img - im_min) / (im_max - im_min + 1e-7)
        
        img = temp_img.view(b, c, h, w)
    
    return img

class BasicBlock(nn.Module):
    def __init__(self, in_channel, out_channel):
        super(BasicBlock, self).__init__()
        self.out = nn.Sequential(
            nn.Conv2d(in_channel, out_channel, 3, 1, 1),
            nn.InstanceNorm2d(out_channel),
            nn.GELU()
        )

    def forward(self, x):
        y = self.out(x)

        return y
    
class ChannelAttention(nn.Module):
    def __init__(self, channels, factor):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.channel_map = nn.Sequential(
            nn.Conv2d(channels, channels // factor, 1, 1, 0),
            nn.LeakyReLU(),
            nn.Conv2d(channels // factor, channels, 1, 1, 0),
            nn.Softmax()
        )

    def forward(self, x):
        avg_pool = self.avg_pool(x)
        ch_map = self.channel_map(avg_pool)
        return x * ch_map
       
class Encoder(nn.Module):
    def __init__(self, basic_channel):
        super(Encoder, self).__init__()
        self.e_stage1 = nn.Sequential(
            nn.Conv2d(3, basic_channel, 3, 1, 1),
            BasicBlock(basic_channel, basic_channel)
        )
        self.e_stage2 = nn.Sequential(
            nn.MaxPool2d(kernel_size=2, stride=2),
            BasicBlock(basic_channel, basic_channel * 2)
        )
        self.e_stage3 = nn.Sequential(
            nn.MaxPool2d(kernel_size=2, stride=2),
            BasicBlock(basic_channel * 2, basic_channel * 4)
        )
        self.e_stage4 = nn.Sequential(
            nn.MaxPool2d(kernel_size=2, stride=2),
            BasicBlock(basic_channel * 4, basic_channel * 8)
        )
    
    def forward(self, x):
        x1 = self.e_stage1(x)
        x2 = self.e_stage2(x1)
        x3 = self.e_stage3(x2)
        x4 = self.e_stage4(x3)
        
        return x1, x2, x3, x4
    
class Decoder(nn.Module):
    def __init__(self, basic_channel):
        super(Decoder, self).__init__()
        self.d_stage4 = nn.Sequential(
            BasicBlock(basic_channel * 8, basic_channel * 4),
            nn.UpsamplingBilinear2d(scale_factor=2)
        )
        self.d_stage3 = nn.Sequential(
            BasicBlock(basic_channel * 4, basic_channel * 2),
            nn.UpsamplingBilinear2d(scale_factor=2)
        )
        self.d_stage2 = nn.Sequential(
            BasicBlock(basic_channel * 2, basic_channel),
            nn.UpsamplingBilinear2d(scale_factor=2)
        )
        self.d_stage1 = nn.Sequential(
            BasicBlock(basic_channel, basic_channel // 4)
        )
        self.output = nn.Sequential(
            nn.Conv2d(basic_channel // 4, 3, 1, 1, 0),
            nn.Tanh()
        )
    
    def forward(self, x, x1, x2, x3, x4):
        y3 = self.d_stage4(x4)
        y2 = self.d_stage3(y3 + x3)
        y1 = self.d_stage2(y2 + x2)
        y = self.output(self.d_stage1(y1 + x1))
        
        return y + x

class SimpleNet(nn.Module):
    def __init__(self, basic_channel=64):
        super(SimpleNet, self).__init__()
        self.encoder = Encoder(basic_channel)
        self.decoder = Decoder(basic_channel)
        
    def forward(self, x):
        # encoder-decoder part
        x1, x2, x3, x4 = self.encoder(x)
        y = normalize_img(self.decoder(x, x1, x2, x3, x4))
        
        return y

if __name__ == "__main__":
    model = SimpleNet().cuda()
    x = torch.rand((1,3,512,512)).cuda()
    y = model(x)
    print(y)