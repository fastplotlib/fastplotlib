"""
Convolutional Neural Network Model Weights
==========================================

Example showing how you can explore the model weights of a simple Convolutional Neural Network (CNN)
during training.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = false

import fastplotlib as fpl
import numpy as np
import torch
import zmq

import torch.nn as nn
import torch.nn.functional as F
import torch.utils.data

from torchvision import datasets, transforms

from torch.optim.lr_scheduler import StepLR
import tqdm

# set up zmq connection to notebook
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://127.0.0.1:5555")

# check if GPU with cuda is available
if torch.cuda.is_available():
    device = torch.device("cuda")
# if not, use CPU
else:
    device = torch.device("cpu")
print(f"Device: {device}")

# define a simple CNN architecture
class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=5)
        self.conv2 = nn.Conv2d(32, 32, kernel_size=5)
        self.conv3 = nn.Conv2d(32,64, kernel_size=5)
        self.fc1 = nn.Linear(3*3*64, 256)
        self.fc2 = nn.Linear(256, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(F.max_pool2d(self.conv2(x), 2))
        x = F.dropout(x, p=0.5, training=self.training)
        x = F.relu(F.max_pool2d(self.conv3(x),2))
        x = F.dropout(x, p=0.5, training=self.training)
        x = x.view(-1,3*3*64 )
        x = F.relu(self.fc1(x))
        x = F.dropout(x, training=self.training)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)

# create model and put to device
model = CNN().to(device)
print(f"Model Architecture:\n {model}")

# load the dataset
# transform to apply to the images
transform=transforms.Compose([
        transforms.ToTensor(), # convert to tensor
        transforms.Normalize((0.1307,), (0.3081,)) # normalize with specified mean and sd
        ])

data = datasets.MNIST('./data', train=True, download=True,
                   transform=transform)

train_loader = torch.utils.data.DataLoader(data, batch_size=32, num_workers=1, shuffle=True)

# sample visual of inputs
#fig_data = fpl.Figure(shape=(1,5), size=(900,300))

# Print the first few images in a row
# for j, (image, label) in enumerate(train_loader):
#     for i in range(5):
#         fig_data[0, i].add_image(np.asarray(image[i].squeeze()), cmap="gray")
#         fig_data[0, i].set_title(f"Label: {label[i].item()}")
#         fig_data[0, i].axes.visible = False
#         fig_data[0, i].toolbar  = False
#
#     break  # Exit the loop after printing 5 samples
#
# fig_data.show()


# send the initial weights via zmq to notebook
weights = model.state_dict()["conv1.weight"].squeeze()
socket.send(np.asarray(weights.cpu()).ravel().astype(np.float64))


# train the model
def train(model, device, train_loader, optimizer, epoch):
    global socket

    # make sure model is in train mode
    model.train()

    correct = 0
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()

        predicted = torch.max(output.data, 1)[1]
        correct += (predicted == target).sum()
        if batch_idx % 1000 == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}\t Accuracy:{:.3f}%'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.item(), float(correct*100) / float(32 * (batch_idx + 1))))


# define optimizer
optimizer = torch.optim.Adam(model.parameters() ,lr=0.001)
# define scheduler for learning rate
scheduler = StepLR(optimizer, step_size=1)

# train the model
# for epoch in tqdm.tqdm(range(0, 5)):

# epoch 0
train(model, device, train_loader, optimizer, 0)
scheduler.step()

# send current model weights
weights = model.state_dict()["conv1.weight"].squeeze()
socket.send(np.asarray(weights.cpu()).ravel().astype(np.float64))

# epoch 1
train(model, device, train_loader, optimizer, 1)
scheduler.step()

# send current model weights
weights = model.state_dict()["conv1.weight"].squeeze()
socket.send(np.asarray(weights.cpu()).ravel().astype(np.float64))

# epoch 2
train(model, device, train_loader, optimizer, 2)
scheduler.step()

# send current model weights
weights = model.state_dict()["conv1.weight"].squeeze()
socket.send(np.asarray(weights.cpu()).ravel().astype(np.float64))

#socket.close()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
