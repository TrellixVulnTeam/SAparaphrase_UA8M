import torch
import torch.nn as nn
import numpy as np
from torch_sparse import spspmm, coalesce, spmm, transpose
import time
import torch.nn as nn

class RNNModel(nn.Module):
	"""Container module with an encoder, a recurrent module, and a decoder."""

	def __init__(self, option):
		super(RNNModel, self).__init__()
		rnn_type = 'LSTM'
		self.option = option
		dropout = option.dropout
		ntoken = option.vocab_size
		ninp = option.emb_size
		nhid = option.hidden_size
		self.nlayers = option.num_layers
		self.drop = nn.Dropout(dropout)
		self.encoder = nn.Embedding(ntoken, ninp)
		self.rnn = nn.LSTM(ninp, nhid, self.nlayers, dropout = dropout ,batch_first=True)
		self.decoder = nn.Linear(nhid, ntoken)
		self.init_weights()
		self.rnn_type = rnn_type
		self.nhid = nhid
		self.ntoken = ntoken
		self.criterion = nn.CrossEntropyLoss()
		self.device = torch.device("cuda" if torch.cuda.is_available() and not self.option.no_cuda else "cpu")

	def init_weights(self):
		initrange = 0.1
		self.encoder.weight.data.uniform_(-initrange, initrange)
		self.decoder.bias.data.zero_()
		self.decoder.weight.data.uniform_(-initrange, initrange)

	def forward(self, input, target):
		'''
		bs,15; bs,15
		'''

		batch_size = input.size(0)
		length = input.size(1)
		target = target.view(-1)

		emb = self.drop(self.encoder(input))
		c0 = torch.zeros(self.nlayers, batch_size, self.nhid).to(self.device)
		h0 = torch.zeros(self.nlayers, batch_size, self.nhid).to(self.device)
		output, hidden = self.rnn(emb, (c0,h0))
		output = self.drop(output).contiguous().view(batch_size*length,-1)
		decoded = self.decoder(output)
		loss = self.criterion(decoded, target)
		v,idx = torch.max(decoded,1)
		acc = torch.mean(torch.eq(idx,target).float())
		return loss,acc, decoded.view(batch_size, length, self.ntoken)

	def init_hidden(self, bsz):
		weight = next(self.parameters())
		if self.rnn_type == 'LSTM':
			return (weight.new_zeros(self.nlayers, bsz, self.nhid),
					weight.new_zeros(self.nlayers, bsz, self.nhid))
		else:
			return weight.new_zeros(self.nlayers, bsz, self.nhid)


def repackage_hidden(h):
    """Wraps hidden states in new Tensors, to detach them from their history."""
    if isinstance(h, torch.Tensor):
        return h.detach()
    else:
        return tuple(repackage_hidden(v) for v in h)

