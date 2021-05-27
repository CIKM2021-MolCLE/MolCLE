import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn.conv import GATConv
from torch_geometric.nn.glob import global_mean_pool, global_add_pool, global_max_pool


def get_readout_layers(readout):
    readout_func_dict = {
        "mean": global_mean_pool,
        "sum": global_add_pool,
        "max": global_max_pool
    }
    readout_func_dict = {k.lower(): v for k, v in readout_func_dict.items()}
    ret_readout = []
    for k, v in readout_func_dict.items():
        if k in readout.lower():
            ret_readout.append(v)
    return ret_readout


# GAT
class GATNet(nn.Module):
    def __init__(self, input_dim, output_dim, model_args):
        super(GATNet, self).__init__()
        self.latent_dim = model_args.latent_dim
        self.mlp_hidden = model_args.mlp_hidden
        self.emb_normlize = model_args.emb_normlize
        self.device = model_args.device
        self.num_gnn_layers = model_args.num_gat_layer
        self.num_mlp_layers = len(self.mlp_hidden) + 1
        self.dense_dim = model_args.gat_hidden * model_args.gat_heads
        self.readout_layers = get_readout_layers(model_args.readout)

        self.gnn_layers = nn.ModuleList()
        self.gnn_layers.append(GATConv(input_dim, model_args.gat_hidden, heads=model_args.gat_heads,
                                       dropout=model_args.gat_dropout, concat=model_args.gat_concate))
        for i in range(1, self.num_gnn_layers):
            self.gnn_layers.append(GATConv(self.dense_dim, model_args.gat_hidden, heads=model_args.gat_heads,
                                           dropout=model_args.gat_dropout, concat=model_args.gat_concate))
        self.gnn_non_linear = nn.ReLU()

        self.mlps = nn.ModuleList()
        if self.num_mlp_layers > 1:
            self.mlps.append(nn.Linear(self.dense_dim * len(self.readout_layers),
                                       model_args.mlp_hidden[0]))
            for i in range(1, self.num_mlp_layers-1):
                self.mlps.append(nn.Linear(self.mlp_hidden[i-1], self.mlp_hidden[1]))
            self.mlps.append(nn.Linear(self.mlp_hidden[-1], output_dim))
        else:
            self.mlps.append(nn.Linear(self.dense_dim * len(self.readout_layers),
                                       output_dim))
        self.dropout = nn.Dropout(model_args.dropout)
        self.Softmax = nn.Softmax(dim=-1)
        self.mlp_non_linear = nn.ELU()

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        for i in range(self.num_gnn_layers):
            x = self.gnn_layers[i](x, edge_index)
            if self.emb_normlize:
                x = F.normalize(x, p=2, dim=-1)
            x = self.gnn_non_linear(x)
        emb = x
        pooled = []
        for readout in self.readout_layers:
            pooled.append(readout(emb, batch))
        x = torch.cat(pooled, dim=-1)

        for i in range(self.num_mlp_layers - 1):
            x = self.mlps[i](x)
            x = self.mlp_non_linear(x)
            x = self.dropout(x)

        logits = self.mlps[-1](x)
        probs = self.Softmax(logits)
        return logits, probs, emb


# GAT node classification
class GATNet_NC(nn.Module):
    def __init__(self, input_dim, output_dim, model_args):
        super(GATNet_NC, self).__init__()
        self.latent_dim = model_args.latent_dim
        self.mlp_hidden = model_args.mlp_hidden
        self.emb_normlize = model_args.emb_normlize
        self.device = model_args.device
        self.num_gnn_layers = model_args.num_gat_layer
        self.num_mlp_layers = len(self.mlp_hidden) + 1
        self.dense_dim = model_args.gat_hidden * model_args.gat_heads
        self.readout_layers = get_readout_layers(model_args.readout)

        self.gnn_layers = nn.ModuleList()
        self.gnn_layers.append(GATConv(input_dim, model_args.gat_hidden, heads=model_args.gat_heads,
                                       dropout=model_args.gat_dropout, concat=model_args.gat_concate))
        for i in range(1, self.num_gnn_layers):
            self.gnn_layers.append(GATConv(self.dense_dim, model_args.gat_hidden, heads=model_args.gat_heads,
                                           dropout=model_args.gat_dropout, concat=model_args.gat_concate))
        self.gnn_non_linear = nn.ReLU()
        self.Softmax = nn.Softmax(dim=-1)

    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        for i in range(self.num_gnn_layers-1):
            x = self.gnn_layers[i](x, edge_index)
            if self.emb_normlize:
                x = F.normalize(x, p=2, dim=-1)
            x = self.gnn_non_linear(x)

        logits = self.gnn_layers[-1](x, edge_index)
        probs = self.Softmax(logits)
        return logits, probs


if __name__ == "__main__":
    from Configures import model_args
    model = GATNet(7, 2, model_args)
    pass