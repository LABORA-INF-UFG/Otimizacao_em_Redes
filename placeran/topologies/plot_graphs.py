import networkx as nx
import json
import matplotlib.pyplot as plt
import pydot
from networkx.drawing.nx_pydot import graphviz_layout
from matplotlib.pyplot import figure, text
import argparse

NODES = ''
LINKS = ''
mod = 'dot'
x_ = 60
y_ = 20

colors = {0:'#ff3300', 1:'#ff9900', 2:'#339933', 3:'#0099ff', 4:'#9966ff'}

def read_nodes_links(nodes, links):
    with open(links) as json_file:
        data_l = json.load(json_file)
    links = [((l['fromNode'], l['toNode']), l['delay'], l['capacity']) for l in data_l['links']]

    with open(nodes) as json_file:
        data_n = json.load(json_file)
    nodes = [(n['nodeNumber'], n['cpu']) for n in data_n['nodes']]

    return nodes, links


def colors_rc(nodes):
    cores = [n[1] for n in nodes]
    cl = {}
    core_labels = list(dict.fromkeys(cores))
    core_labels.sort()
    for item in range(len(core_labels)):
        cl[core_labels[item]] = colors[item]
    for item in range(len(cores)):
        cores[item] = cl[cores[item]]
    return cl, cores


def plot_graph(nodes, links, mod=mod, x_=x_, y_=y_):

    nodes, links = read_nodes_links(nodes, links)
    
    
    G = nx.Graph()

    G.add_nodes_from([n[0] for n in nodes])
    
    
    core_labels, core_colors = colors_rc(nodes)

    for i, d, c  in links:
        G.add_edge(i[0], i[1], weight='[' + str(d) + 'ms, ' + str(c) + 'Gb/s]')



    fig, ax = plt.subplots()
    fig.set_size_inches(x_, y_)

    pos = graphviz_layout(G, prog=mod)

    edge_labels = nx.get_edge_attributes(G, "weight")
    
    nodes = nx.draw_networkx_nodes(G, pos, node_size=6000, node_color=core_colors, edgecolors='#000000')
    
    edges = nx.draw_networkx_edges(
    G,
    pos,
    #node_size=node_sizes,
    #arrowstyle="->",
    arrowsize=10,
    edge_color='#1a1a1a',
    style="dashed",
    #edge_cmap=cmap,
    width=4,
    )
    
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_color='#ff5050', font_size=50)
    
    plist = []
    for item in core_labels:
        pl, = (ax.plot([], [], "o",label="RC=" + str(item), color=str(core_labels[item])))
        plist.append(pl)
    ax.legend(handles=plist, fontsize=64, loc='lower right', markerscale=10)
    
    for node, (x, y) in pos.items():
        text(x, y, node, fontsize=50, ha='center', va='center', color='#ffffff')

    #fig.savefig("graph.pdf", bbox_inches='tight')
    
    #plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--nodes", help="Inserir o arquivo json contendo os nós da rede", required=True)
    parser.add_argument("-l", "--links", help="Inserir o arquivo json contendo os links da rede", required=True)

    parser.add_argument("-m", "--mod", help="inserir o modelo do grafo: dot, circo, neato, twopi, fdp, sfdp")

    parser.add_argument("-x", "--x_", help="Inserir o valor de x para o tamanho da figura")
    parser.add_argument("-y", "--y_", help="Inserir o valor de y para o tamanho da figura")

    args = parser.parse_args()

    if args.nodes:
        NODES = args.nodes
    if args.links:
        LINKS = args.links
    if args.mod:
        mod = args.mod
    if args.x_:
        x_ = args.x_
    if args.y_:
        y_ = args.y_

    plot_graph(NODES, LINKS, mod, x_, y_)
