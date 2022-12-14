from pickle import FALSE
import time
import json
from docplex.mp.model import Model
from docplex.util.environment import get_environment
import argparse

LINKS = 'topologies/5_CRs/T2_5_links.json'
NODES = 'topologies/5_CRs/T2_5_CRs.json'
PATHS = 'topologies/5_CRs/T2_5_paths.json'

hierarchical = True
heuristic_file = None
callback = False

class Path:
    def __init__(self, id, source, target, seq, p1, p2, p3, delay_p1, delay_p2, delay_p3):
        self.id = id
        self.source = source
        self.target = target
        self.seq = seq
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.delay_p1 = delay_p1
        self.delay_p2 = delay_p2
        self.delay_p3 = delay_p3

    def __str__(self):
        return "ID: {}\tSEQ: {}\t P1: {}\t P2: {}\t P3: {}\t dP1: {}\t dP2: {}\t dP3: {}".format(self.id, self.seq, self.p1, self.p2, self.p3, self.delay_p1, self.delay_p2, self.delay_p3)


class CR:
    def __init__(self, id, cpu, num_BS):
        self.id = id
        self.cpu = cpu
        self.num_BS = num_BS

    def __str__(self):
        return "ID: {}\tCPU: {}".format(self.id, self.cpu)


class DRC:
    def __init__(self, id, cpu_CU, cpu_DU, cpu_RU, ram_CU, ram_DU, ram_RU, Fs_CU, Fs_DU, Fs_RU, delay_BH, delay_MH,
                 delay_FH, bw_BH, bw_MH, bw_FH):
        self.id = id

        self.cpu_CU = cpu_CU
        self.ram_CU = ram_CU
        self.Fs_CU = Fs_CU

        self.cpu_DU = cpu_DU
        self.ram_DU = ram_DU
        self.Fs_DU = Fs_DU

        self.cpu_RU = cpu_RU
        self.ram_RU = ram_RU
        self.Fs_RU = Fs_RU

        self.delay_BH = delay_BH
        self.delay_MH = delay_MH
        self.delay_FH = delay_FH

        self.bw_BH = bw_BH
        self.bw_MH = bw_MH
        self.bw_FH = bw_FH


class FS:
    def __init__(self, id, f_cpu, f_ram):
        self.id = id
        self.f_cpu = f_cpu
        self.f_ram = f_ram


class RU:
    def __init__(self, id, CR):
        self.id = id
        self.CR = CR

    def __str__(self):
        return "RU: {}\tCR: {}".format(self.id, self.CR)


links = []
capacity = {}
delay = {}
crs = {}
paths = {}
conj_Fs = {}


def read_topology():
    with open(LINKS) as json_file:
        data = json.load(json_file)
        json_links = data["links"]
        for item in json_links:
            link = item
            source_node = link["fromNode"]
            destination_node = link["toNode"]

            capacity[(source_node, destination_node)] = link["capacity"]
            delay[(source_node, destination_node)] = link["delay"]
            links.append((source_node, destination_node))

            capacity[(destination_node, source_node)] = link["capacity"]
            delay[(destination_node, source_node)] = link["delay"]
            links.append((destination_node, source_node))
            '''
            if source_node < destination_node:
                capacity[(source_node, destination_node)] = link["capacity"]
                delay[(source_node, destination_node)] = link["delay"]
                links.append((source_node, destination_node))
            else:
                capacity[(destination_node, source_node)] = link["capacity"]
                delay[(destination_node, source_node)] = link["delay"]
                links.append((destination_node, source_node))
            '''
        with open(NODES) as json_file:
            data = json.load(json_file)
            json_nodes = data["nodes"]
            for item in json_nodes:
                node = item
                CR_id = node["nodeNumber"]
                node_CPU = node["cpu"]
                cr = CR(CR_id, node_CPU, 0)
                crs[CR_id] = cr
        crs[0] = CR(0, 0, 0)
        with open(PATHS) as json_paths_file:
            json_paths_f = json.load(json_paths_file)
            json_paths = json_paths_f["paths"]
            for item in json_paths:
                path = json_paths[item]
                path_id = path["id"]
                path_source = path["source"]
                if path_source == "CN":
                    path_source = 0
                path_target = path["target"]
                path_seq = path["seq"]
                paths_p = [path["p1"], path["p2"], path["p3"]]
                list_p1 = []
                list_p2 = []
                list_p3 = []
                for path_p in paths_p:
                    aux = ""
                    sum_delay = 0
                    for tup in path_p:
                        aux += tup
                        tup_aux = tup
                        tup_aux = tup_aux.replace('(', '')
                        tup_aux = tup_aux.replace(')', '')
                        tup_aux = tuple(map(int, tup_aux.split(', ')))
                        if path_p == path["p1"]:
                            list_p1.append(tup_aux)
                        elif path_p == path["p2"]:
                            list_p2.append(tup_aux)
                        elif path_p == path["p3"]:
                            list_p3.append(tup_aux)
                        sum_delay += delay[tup_aux]
                    if path_p == path["p1"]:
                        delay_p1 = sum_delay
                    elif path_p == path["p2"]:
                        delay_p2 = sum_delay
                    elif path_p == path["p3"]:
                        delay_p3 = sum_delay
                    if path_seq[0] == 0:
                        delay_p1 = 0
                    if path_seq[1] == 0:
                        delay_p2 = 0
                p = Path(path_id, path_source, path_target, path_seq, list_p1, list_p2, list_p3, delay_p1, delay_p2, delay_p3)
                paths[path_id] = p



def DRC_structure_T2():
    DRC5 = DRC(5, 0.98, 0.735, 3.185, 0.01, 0.01, 0.01, ['f8', 'f7'], ['f6', 'f5', 'f4', 'f3'], ['f2', 'f1', 'f0'], 10, 10, 0.25, 9.9, 13.2, 13.6)
    DRC9 = DRC(9, 0, 2.54, 2.354, 0, 0.01, 0.01, [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2'], ['f1', 'f0'], 0, 10, 0.25, 0, 9.9, 42.6)
    DRC8 = DRC(8, 0, 0, 4.9, 0, 0, 0.01, [0], [0], ['f8', 'f7', 'f6', 'f5', 'f4', 'f3', 'f2', 'f1', 'f0'], 0, 0, 10, 0, 0, 9.9)
    
    DRCs = {5: DRC5, 9: DRC9, 8: DRC8}
    return DRCs


def RU_location_T1():
    rus = {}
    count = 1
    with open(NODES) as json_file:
        data = json.load(json_file)
        json_crs = data["nodes"]
        for item in json_crs:
            node = json_crs[item]
            num_rus = node["RU"]
            num_cr = str(item).split('-', 1)[1]
            for i in range(0, num_rus):
                rus[count] = RU(count, int(num_cr))
                count += 1
    return rus


def RU_location_T2():
    rus = {}
    count = 1
    with open(NODES) as json_file:
        data = json.load(json_file)
        json_crs = data["nodes"]
        for item in json_crs:
            node = item
            num_rus = node["RU"]
            num_cr = node["nodeNumber"]
            for i in range(0, num_rus):
                rus[count] = RU(count, int(num_cr))
                count += 1
    return rus


DRC_f1 = 0
f1_vars = []
f2_vars = []


def run_stage_1():
    print("Running Stage - 1")
    print("-----------------------------------------------------------------------------------------------------------")
    alocation_time_start = time.time()
    # read_topology_T1()
    read_topology()
    # DRCs = DRC_structure_T1()
    DRCs = DRC_structure_T2()
    # rus = RU_location_T1()
    rus = RU_location_T2()

    read_topology_end = time.time()
    F1 = FS('f8', 2, 2)
    F2 = FS('f7', 2, 2)
    F3 = FS('f6', 2, 2)
    F4 = FS('f5', 2, 2)
    F5 = FS('f4', 2, 2)
    F6 = FS('f3', 2, 2)
    F7 = FS('f2', 2, 2)
    F8 = FS('f1', 2, 2)
    F9 = FS('f0', 2, 2)
    conj_Fs = {'f8': F1, 'f7': F2, 'f6': F3, 'f5': F4, 'f4': F5, 'f3': F6, 'f2': F7}
    mdl = Model(name='PlaceRAN Problem', log_output=True)
    mdl.parameters.mip.tolerances.absmipgap = 1
    i = [(p, d, b) for p in paths for d in DRCs for b in rus if (paths[p].seq[2] == rus[b].CR) and
                                                                ((paths[p].seq[0] != 0 and d in [1,2,4,5]) or
                                                                 (paths[p].seq[0] == 0 and paths[p].seq[1] != 0 and d in [6,7,9,10]) or
                                                                 (paths[p].seq[1] == 0 and d in [8])) and
                                                                (paths[p].delay_p1 <= DRCs[d].delay_BH) and
                                                                (paths[p].delay_p2 <= DRCs[d].delay_MH) and
                                                                (paths[p].delay_p3 <= DRCs[d].delay_FH)]
    j = [(c, f) for f in conj_Fs.keys() for c in crs.keys()]
    l = [c for c in crs.keys() if c != 0]

    mdl.x = mdl.binary_var_dict(keys=i, name='x')
    mdl.w = mdl.binary_var_dict(keys=l, name='w')
    mdl.z = mdl.binary_var_dict(keys=j, name='z')

    variable_allocation_end = time.time()


    # phy 1
    for c in crs:
        if(crs[c].id == 0):
            continue

        max_value = sum(1 for it in i if c in paths[it[0]].seq)
        max_value = max_value + 1

        mdl.add_constraint(mdl.w[crs[c].id] <= mdl.sum(mdl.x[it] for it in i if c in paths[it[0]].seq)/max_value + (1.0 - (1 / max_value)))
        mdl.add_constraint(mdl.w[crs[c].id] >= mdl.sum(mdl.x[it] for it in i if c in paths[it[0]].seq)/max_value)
    phy1 = mdl.sum(mdl.w[crs[c].id] for c in crs if crs[c].id != 0)


    phy1_end = time.time()


    # phy 2
    max_value = len(crs) * len(conj_Fs)

    ceil_expressions = {}
    for it in i:
        c = paths[it[0]].seq[0]
        if c != 0:
            for f in DRCs[it[1]].Fs_CU:
                if f not in conj_Fs.keys():
                    continue
                ceil_expressions.setdefault((c, f), mdl.linear_expr()).add(mdl.x[it])

        c = paths[it[0]].seq[1]
        if c != 0:
            for f in DRCs[it[1]].Fs_DU:
                if f not in conj_Fs.keys():
                    continue
                ceil_expressions.setdefault((c, f), mdl.linear_expr()).add(mdl.x[it])
        
        c = paths[it[0]].seq[2]
        if c != 0:
            for f in DRCs[it[1]].Fs_RU:
                if f not in conj_Fs.keys():
                    continue
                ceil_expressions.setdefault((c, f), mdl.linear_expr()).add(mdl.x[it])
    
    phy2 = mdl.linear_expr()
    for key, expr in ceil_expressions.items():
        mdl.add_constraint(mdl.z[key] >= expr / max_value)
        mdl.add_constraint(mdl.z[key] <= expr / max_value + (1.0 - (1 / max_value)))
        phy2 += mdl.sum(expr - mdl.z[key])

        

    phy2_end = time.time()

    mdl.minimize(phy1 - phy2)
    
    objective_end = time.time()

    for b in rus:
        mdl.add_constraint(mdl.sum(mdl.x[it] for it in i if it[2] == b) == 1, 'unicity')

    single_path_end = time.time()

    capacity_expressions = {}
    for it in i:
        for link in paths[it[0]].p1:
            capacity_expressions.setdefault(link, mdl.linear_expr()).add_term(mdl.x[it], DRCs[it[1]].bw_BH)
        
        for link in paths[it[0]].p2:
            capacity_expressions.setdefault(link, mdl.linear_expr()).add_term(mdl.x[it], DRCs[it[1]].bw_MH)
        
        for link in paths[it[0]].p3:
            capacity_expressions.setdefault(link, mdl.linear_expr()).add_term(mdl.x[it], DRCs[it[1]].bw_FH)

    for l in links:
        if l in capacity_expressions.keys():
            mdl.add_constraint(capacity_expressions[l] <= capacity[l], 'links_bw')

    capacity_end = time.time()

    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p1) <= DRCs[it[1]].delay_BH, 'delay_req_p1')
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p2) <= DRCs[it[1]].delay_MH, 'delay_req_p2')
    for it in i:
        mdl.add_constraint((mdl.x[it] * paths[it[0]].delay_p3 <= DRCs[it[1]].delay_FH), 'delay_req_p3')
    
    link_delay_end = time.time()

    for c in crs:
        mdl.add_constraint(
            mdl.sum(mdl.x[it] * DRCs[it[1]].cpu_CU for it in i if c == paths[it[0]].seq[0]) + 
            mdl.sum(mdl.x[it] * DRCs[it[1]].cpu_DU for it in i if c == paths[it[0]].seq[1]) + 
            mdl.sum(mdl.x[it] * DRCs[it[1]].cpu_RU for it in i if c == paths[it[0]].seq[2]) <= crs[c].cpu, 'crs_cpu_usage')
    cpu_end = time.time()
    
    if heuristic_file != None:
        print('Inserindo solução heuristica...')
        with open(heuristic_file) as file:
            hs = json.load(file)
            
        warm_start = mdl.new_solution()
        for it in hs['dv']:
            tuple_dv = it.split('_')
            print(tuple_dv)
            if tuple_dv[0] == 'x':
                warm_start.add_var_value(mdl.x[(int(tuple_dv[1]), int(tuple_dv[2]), int(tuple_dv[3]))], 1)
            elif tuple_dv[0] == 'z':
                warm_start.add_var_value(mdl.z[(int(tuple_dv[1]), tuple_dv[2])], 1)
            elif tuple_dv[0] == 'w':
                warm_start.add_var_value(mdl.w[int(tuple_dv[1])], 1)
        mdl.add_mip_start(warm_start)
        print('OK')

    if callback:
        from cplex.callbacks import Context
        from my_callback import HeuristicCallback
        contextmask = 0
        contextmask |= Context.id.relaxation
        #contextmask |= 32
        heuristiccb = HeuristicCallback()
        mdl.cplex.set_callback(heuristiccb, contextmask)

        dict_sol = {}
        for sol in mdl.iter_variables():
            dict_sol[sol.name] = sol.index
            dict_sol[sol.index] = sol.name
            
        with open('dict_sol.json', 'w') as file:
            json.dump(dict_sol, file, indent=4)
        
    mdl.export_as_lp('opt.lp')
    
    alocation_time_end = time.time()
    start_time = time.time()
    mdl.solve()
    end_time = time.time()

    disp_Fs = {}

    for cr in crs:
        disp_Fs[cr] = {'f8': 0, 'f7': 0, 'f6': 0, 'f5': 0, 'f4': 0, 'f3': 0, 'f2': 0, 'f1': 0, 'f0': 0}

    for it in i:
        for cr in crs:
            if mdl.x[it].solution_value > 0:
                if cr in paths[it[0]].seq:
                    seq = paths[it[0]].seq
                    if cr == seq[0]:
                        Fs = DRCs[it[1]].Fs_CU
                        for o in Fs:
                            if o != 0:
                                dct = disp_Fs[cr]
                                dct["{}".format(o)] += 1
                                disp_Fs[cr] = dct

                    if cr == seq[1]:
                        Fs = DRCs[it[1]].Fs_DU
                        for o in Fs:
                            if o != 0:
                                dct = disp_Fs[cr]
                                dct["{}".format(o)] += 1
                                disp_Fs[cr] = dct

                    if cr == seq[2]:
                        Fs = DRCs[it[1]].Fs_RU
                        for o in Fs:
                            if o != 0:
                                dct = disp_Fs[cr]
                                dct["{}".format(o)] += 1
                                disp_Fs[cr] = dct

    for cr in disp_Fs:
        print(str(cr) + str(disp_Fs[cr]))

    for it in i:
        if mdl.x[it].solution_value > 0:
            print("x{} -> {}".format(it, mdl.x[it].solution_value))
            print(paths[it[0]].seq)

    print("Stage 1 - Alocation Time: {}".format(alocation_time_end - alocation_time_start))
    print("Stage 1 - Read Topo Time: {}".format(read_topology_end - alocation_time_start))
    print("Stage 1 - Var Alloc Time: {}".format(variable_allocation_end - read_topology_end))
    print("Stage 1 - Phy1 Proc Time: {}".format(phy1_end - variable_allocation_end))
    print("Stage 1 - Phy2 Proc Time: {}".format(phy2_end - phy1_end))
    print("Stage 1 - Objc Proc Time: {}".format(objective_end - phy2_end))
    print("Stage 1 - Path Proc Time: {}".format(single_path_end - objective_end))
    print("Stage 1 - Cap  Proc Time: {}".format(capacity_end - single_path_end))
    print("Stage 1 - link Proc Time: {}".format(link_delay_end - capacity_end))
    print("Stage 1 - cpu  Proc Time: {}".format(cpu_end - link_delay_end))
    print("Stage 1 - Enlapsed Time: {}".format(end_time - start_time))
    print("Stage 1 -Optimal Solution: {}".format(mdl.solution.get_objective_value()))
    
    print("FO: {}".format(mdl.solution.get_objective_value()))

    global f1_vars
    for it in i:
        if mdl.x[it].solution_value > 0:
            f1_vars.append(it)
    print('Numero nos:',mdl.solve_details.nb_nodes_processed)
    print('Variaveis de Decisão: ', len(list(mdl.iter_variables())))
    print('Restrições: ', len(list(mdl.iter_constraints())))
    
    return mdl.solution.get_objective_value()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--warm_start", help="Inserir a solução heuristica como ponto de entrada")
    parser.add_argument("-c", "--heuristic_callback", help="Inserir a solução heuristica pela callback")
    args = parser.parse_args()

    if args.warm_start:
        heuristic_file = args.warm_start
        print(heuristic_file)

    if args.heuristic_callback and args.heuristic_callback == 'True':
        callback = True
    
    start_all = time.time()

    FO_Stage_1 = run_stage_1()

    end_all = time.time()

    print("TOTAL TIME: {}".format(end_all - start_all))