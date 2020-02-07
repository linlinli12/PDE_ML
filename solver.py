import os
import numpy as np
from scipy.io import loadmat
from scipy.integrate import solve_ivp
from time import time
from ode_fun import set_ode_fun
import random
from random import uniform
from random import randint
import torch
from multiprocessing import Pool
from model_simple import ModelSimple
import pandas as pd


min_values = np.float64([-4.0, -4.0, -3.0, -4.0, 0.0, -4.0, 0.0, 0.0, -2.0, -4.0, \
              -4.0, -2.0, -5.0, -2.0, -2.0, -5.0, -2.0, -5.0, -5.0])
max_values = np.float64([0.0, 0.0, -1.0, 0.0, 2.0, 0.0, 2.0, 2.0, 1.0, 0.0, \
              0.0, 2.0, -1.0, 2.0, 2.0, -3.0, 2.0, -3.0, -1.0])


class Parameters:
    def __init__(self):
        # para_grid, para_grid_jBC, para_grid_k, para_grid_ki = read_parameters(i)
        exp_data = loadmat('pSmad_WT_MT_new.mat')
        self.WT_exp, self.WT_ref_exp = read_exp_data(exp_data, 'pWT_57')
        self.CLF_exp, self.CLF_ref_exp = read_exp_data(exp_data, 'pCLF_57')
        self.ALF_exp, self.ALF_ref_exp = read_exp_data(exp_data, 'pALF_57')
        self.TLF_exp, self.TLF_ref_exp = read_exp_data(exp_data, 'pTLF_57')
        self.TALF_exp, _ = read_exp_data(exp_data, 'pTALF_57')
        self.SLF_exp, _ = read_exp_data(exp_data, 'pSLF_57')
        self.num_proteins = 6
        self.n = 36  # number of nodes to evaluate finite difference equations
        self.T = 7900.0  # how many time steps to use in PDE solution
        self.Ltot = 700.0  # length of embryo
        self.Lven_BMP = 400.0  # length of ventral region for BMP
        self.Lven_Tld = 700.0  # length of ventral region for Tolloid
        self.Ldor_Chd = 140.0  # length of dorsal region for Chordin
        self.Ldor_Nog = 78.0  # length of dorsal region for Noggin
        dx = self.Ltot / (self.n - 1)
        self.dx2 = dx * dx
        self.D_BMP = 4.4 / self.dx2  # diffusion rate of BMP
        self.D_Szd = 10.0 / self.dx2  # diffusion rate of Sizzled
        self.dec_BMP = 8.9e-5  # decay rate of BMP
        self.dec_Chd = 9.6e-5  # decay rate of Chordin
        self.nu = 4.0  # cooperative parameter
        self.Vs = 100.0
        self.kit = 123  # para_grid_ki[0]  # inhibitor constant of proteinase Tolloid
        self.kia = 26  # para_grid_ki[1]  # inhibitor constant of proteinase bmp1a
        self.k = 1652  # parameter for hill function
        self.ndor_Chd = round(self.Ldor_Chd * self.n / self.Ltot)
        self.ndor_Nog = round(self.Ldor_Nog * self.n / self.Ltot)
        x_lig = np.arange(0.0, self.Ltot + dx / 2, dx)
        self.yspace = np.exp(-((x_lig + dx) / 20 - 11) / 5) / (0.1 + np.exp(-((x_lig + dx) / 20 - 11) / 5))
        self.init = np.zeros((self.num_proteins * self.n,), dtype=np.float64)
        self.tspan = (0.0, self.T)


'''
def read_parameters(i):
    para_grid = loadmat('para_screened.mat')['para_grid'][i]
    para_grid_jBC = loadmat('para_grid_jBC_screened.mat')['para_grid_jBC'][i]
    para_grid_k = loadmat('para_grid_k_screened.mat')['k'][0, i]
    para_grid_ki = loadmat('para_grid_ki_screened.mat')['para_grid_ki'][i]
    return para_grid, para_grid_jBC, para_grid_k, para_grid_ki
'''


def read_exp_data(exp_data, var_name):
    exp_data = exp_data[var_name][0]
    ref = (np.sort(exp_data)[-5:]).mean()
    exp_data = exp_data[:16]
    return exp_data, ref

def crandint(min_val, max_val):
    return (max_val - min_val) * (randint(0, 15)/15.0) + min_val

def set_continuous_parameters(parameters):
    parameters.D_Nog = (10 ** uniform(-2.0, 2.0))
    parameters.D_BMPChd = (10 ** uniform(-2.0, 2.0))
    parameters.D_BMPNog = (10 ** uniform(-2.0, 2.0))
    parameters.D_Chd = 0.5 * (10 ** uniform(0.0, 2.0))
    parameters.dec_Nog = 10 ** uniform(-5.0, -1.0)
    parameters.dec_Szd = 10 ** uniform(-5.0, -1.0)
    parameters.dec_BMPChd = 10 ** uniform(-5.0, -3.0)
    parameters.dec_BMPNog = 10 ** uniform(-5.0, -3.0)
    parameters.j3 = 10 ** uniform(-2.0, 2.0)
    parameters.k1 = 10 ** uniform(-4.0, 0.0)
    parameters.k_1 = parameters.k1
    parameters.k2 = 10 ** uniform(-4.0, 0.0)
    parameters.k_2 = 0.1 * parameters.k2
    parameters.kmt = 10 ** uniform(0.0, 2.0)
    parameters.kma = 10 ** uniform(0.0, 2.0)
    parameters.lambda_Tld_Chd = 10 ** uniform(-4.0, 0.0)
    parameters.lambda_Tld_BMPChd = 10 ** uniform(-4.0, 0.0)
    parameters.lambda_bmp1a_Chd = 10 ** uniform(-4.0, 0.0)
    parameters.lambda_bmp1a_BMPChd = 10 ** uniform(-4.0, 0.0)
    while True:
        parameters.j1 = 10 ** uniform(-3.0, -1.0)
        parameters.j2 = 10 ** uniform(-2.0, 1.0)
        if parameters.j2 > parameters.j1:
            break


def set_discrete_parameters(parameters):
    parameters.D_Nog = (10 ** crandint(-2, 2)) / parameters.dx2
    parameters.D_BMPChd = (10 ** crandint(-2, 2)) / parameters.dx2
    parameters.D_BMPNog = (10 ** crandint(-2, 2)) / parameters.dx2
    parameters.D_Chd = 0.5 * (10 ** crandint(0, 2)) / parameters.dx2
    parameters.dec_Nog = 10 ** crandint(-5, -1)
    parameters.dec_Szd = 10 ** crandint(-5, -1)
    parameters.dec_BMPChd = 10 ** crandint(-5, -3)
    parameters.dec_BMPNog = 10 ** crandint(-5, -3)
    parameters.j3 = 10 ** crandint(-2, 2)
    parameters.k1 = 10 ** crandint(-4, 0)
    parameters.k_1 = parameters.k1
    parameters.k2 = 10 ** crandint(-4, 0)
    parameters.k_2 = 0.1 * parameters.k2
    parameters.kmt = 10 ** crandint(0, 2)
    parameters.kma = 10 ** crandint(0, 2)
    parameters.lambda_Tld_Chd = 10 ** crandint(-4, 0)
    parameters.lambda_Tld_BMPChd = 10 ** crandint(-4, 0)
    parameters.lambda_bmp1a_Chd = 10 ** crandint(-4, 0)
    parameters.lambda_bmp1a_BMPChd = 10 ** crandint(-4, 0)
    while True:
        parameters.j1 = 10 ** crandint(-3, -1)
        parameters.j2 = 10 ** crandint(-2, 1)
        if parameters.j2 > parameters.j1:
            break


def read_from_file(parameters, path):
    data = pd.read_csv(path, header=None)
    data = data.iloc[:, :23].to_numpy()
    ind = np.random.randint(0, 10000)
    ind2 = np.random.randint(0, 10000)
    #data = data[ind * 7]
    parameters.D_Nog = data[ind*7, 0]
    parameters.D_BMPChd = data[ind*7, 1]
    parameters.D_BMPNog = data[ind*7, 2]
    parameters.D_Chd = data[ind*7, 3]
    parameters.dec_Nog = data[ind*7, 4]
    parameters.dec_Szd = data[ind*7, 5]
    parameters.dec_BMPChd = data[ind*7, 6]
    parameters.dec_BMPNog = data[ind*7, 7]
    parameters.j3 = data[ind*7, 8]
    parameters.k1 = data[ind*7, 9]
    parameters.k_1 = parameters.k1
    parameters.k2 = data[ind*7, 10]
    parameters.k_2 = 0.1 * parameters.k2
    parameters.kmt = data[ind*7, 11]
    parameters.kma = data[ind*7, 12]
    parameters.lambda_Tld_Chd = data[ind*7, 13]
    parameters.lambda_Tld_BMPChd = data[ind*7, 14]
    parameters.lambda_bmp1a_Chd = data[ind*7, 15]
    parameters.lambda_bmp1a_BMPChd = data[ind*7, 16]
    parameters.j1 = data[ind*7, 17]
    parameters.j2 = data[ind*7, 18]
    parameters.k = data[ind*7, 19]
    parameters.kit = data[ind*7, 20]
    parameters.kia = data[ind*7, 21]
    #parameters.Vs = data[22]


def normalize_inputs(data):
    data = torch.abs(data)
    data[abs(data) < 1e-8] = 1e-8
    data = torch.log10(data)
    data /= 10.0
    return data


def prepare_inputs(parameters):
    inputs = torch.zeros(23)
    inputs[0] = parameters.D_Nog
    inputs[1] = parameters.D_BMPChd
    inputs[2] = parameters.D_BMPNog
    inputs[3] = parameters.D_Chd
    inputs[4] = parameters.dec_Nog
    inputs[5] = parameters.dec_Szd
    inputs[6] = parameters.dec_BMPChd
    inputs[7] = parameters.dec_BMPNog
    inputs[8] = parameters.j3
    inputs[9] = parameters.k1
    inputs[10] = parameters.k2
    inputs[11] = parameters.kmt
    inputs[12] = parameters.kma
    inputs[13] = parameters.lambda_Tld_Chd
    inputs[14] = parameters.lambda_Tld_BMPChd
    inputs[15] = parameters.lambda_bmp1a_Chd
    inputs[16] = parameters.lambda_bmp1a_BMPChd
    inputs[17] = parameters.j1
    inputs[18] = parameters.j2
    inputs[19] = 0.0 #parameters.k
    inputs[20] = parameters.kit
    inputs[21] = parameters.kia
    inputs[22] = parameters.Vs
    #print(inputs)
    inputs = inputs.unsqueeze(0)
    inputs = normalize_inputs(inputs)
    return inputs


def inputs2parameters(inputs):
    parameters = Parameters()
    inputs = inputs.cpu().numpy().astype(np.float64)
    inputs = np.power(10, 10.0 * inputs)
    parameters.D_Nog = inputs[0]
    parameters.D_BMPChd = inputs[1]
    parameters.D_BMPNog = inputs[2]
    parameters.D_Chd = inputs[3]
    parameters.dec_Nog = inputs[4]
    parameters.dec_Szd = inputs[5]
    parameters.dec_BMPChd = inputs[6]
    parameters.dec_BMPNog = inputs[7]
    parameters.j3 = inputs[8]
    parameters.k1 = inputs[9]
    parameters.k_1 = parameters.k1
    parameters.k2 = inputs[10]
    parameters.k_2 = 0.1 * parameters.k2
    parameters.kmt = inputs[11]
    parameters.kma = inputs[12]
    parameters.lambda_Tld_Chd = inputs[13]
    parameters.lambda_Tld_BMPChd = inputs[14]
    parameters.lambda_bmp1a_Chd = inputs[15]
    parameters.lambda_bmp1a_BMPChd = inputs[16]
    parameters.j1 = inputs[17]
    parameters.j2 = inputs[18]
    parameters.k = inputs[19]
    parameters.kit = inputs[20]
    parameters.kia = inputs[21]
    parameters.Vs = inputs[22]
    return parameters


def solve_pde(parameters, ref_exp, ref_sim):
    fun = set_ode_fun(parameters)
    sol = solve_ivp(fun, parameters.tspan, parameters.init, method='BDF', rtol=1e-9)
    BMP = sol.y[:36, -1]
    #print(BMP)
    #print(np.log10(BMP)/10.0)
    if ref_sim is None:
        ref_sim = (np.sort(BMP)[-5:]).mean()
    BMP = BMP[0:32:2]
    BMP *= ref_exp / ref_sim
    return BMP, ref_sim


def solve_pde_nn(parameters, ref_exp, ref_nn, model):
    inputs = prepare_inputs(parameters).cuda()
    y = model(inputs).squeeze().detach().cpu().numpy()
    #y = y.view(36, 6).cpu().numpy()
    y = np.power(10.0, 10.0 * y)
    BMP = y #[:, 1]
    #print(BMP)
    if ref_nn is None:
        ref_nn = (np.sort(BMP)[-5:]).mean()
    BMP = BMP[0:32:2]
    BMP *= ref_exp / ref_nn
    return BMP, ref_nn


def run_simulation(parameters, model):
    # WT simulation
    WT_sim, ref_sim = solve_pde(parameters, parameters.WT_ref_exp, None)
    WT_nn, ref_nn = solve_pde_nn(parameters, parameters.WT_ref_exp, None, model)
    WT_nrmse = np.sqrt(np.power(WT_sim - parameters.WT_exp, 2).mean()) / 61.9087
    WT_nrmse_nn = np.sqrt(np.power(WT_nn - parameters.WT_exp, 2).mean()) / 61.9087
    WT_error = 100.0 * abs(WT_nrmse - WT_nrmse_nn) / WT_nrmse
    #print(WT_sim)
    #print(WT_nn)
    # CLF simulation
    j2 = parameters.j2
    parameters.j2 = 0.0
    CLF_sim, _ = solve_pde(parameters, parameters.WT_ref_exp, ref_sim)
    CLF_nn, _ = solve_pde_nn(parameters, parameters.WT_ref_exp, ref_nn, model)
    CLF_nrmse = np.sqrt(np.power(CLF_sim - parameters.CLF_exp, 2).mean()) / 61.9087
    CLF_nrmse_nn = np.sqrt(np.power(CLF_nn - parameters.CLF_exp, 2).mean()) / 61.9087
    CLF_error = 100.0 * abs(CLF_nrmse - CLF_nrmse_nn) / CLF_nrmse
    parameters.j2 = j2
    # NLF simulation
    j3 = parameters.j3
    parameters.j3 = 0.0
    NLF_sim, _ = solve_pde(parameters, parameters.WT_ref_exp, ref_sim)
    NLF_nn, _ = solve_pde_nn(parameters, parameters.WT_ref_exp, ref_nn, model)
    NLF_nrmse = np.sqrt(np.power(NLF_sim - parameters.WT_exp, 2).mean()) / 61.9087
    NLF_nrmse_nn = np.sqrt(np.power(NLF_nn - parameters.WT_exp, 2).mean()) / 61.9087
    NLF_error = 100.0 * abs(NLF_nrmse - NLF_nrmse_nn) / NLF_nrmse
    parameters.j3 = j3
    # ALF simulation
    lambda_bmp1a_Chd = parameters.lambda_bmp1a_Chd
    lambda_bmp1a_BMPChd = parameters.lambda_bmp1a_BMPChd
    parameters.lambda_bmp1a_Chd = 0.0
    parameters.lambda_bmp1a_BMPChd = 0.0
    ALF_sim, _ = solve_pde(parameters, parameters.WT_ref_exp, ref_sim)
    ALF_nn, _ = solve_pde_nn(parameters, parameters.WT_ref_exp, ref_nn, model)
    ALF_nrmse = np.sqrt(np.power(ALF_sim - parameters.ALF_exp, 2).mean()) / 61.9087
    ALF_nrmse_nn = np.sqrt(np.power(ALF_nn - parameters.ALF_exp, 2).mean()) / 61.9087
    ALF_error = 100.0 * abs(ALF_nrmse - ALF_nrmse_nn) / ALF_nrmse
    parameters.lambda_bmp1a_Chd = lambda_bmp1a_Chd
    parameters.lambda_bmp1a_BMPChd = lambda_bmp1a_BMPChd
    # TLF simulation
    lambda_Tld_Chd = parameters.lambda_Tld_Chd
    lambda_Tld_BMPChd = parameters.lambda_Tld_BMPChd
    parameters.lambda_Tld_Chd = 0.0
    parameters.lambda_Tld_BMPChd = 0.0
    TLF_sim, _ = solve_pde(parameters, parameters.WT_ref_exp, ref_sim)
    TLF_nn, _ = solve_pde_nn(parameters, parameters.WT_ref_exp, ref_nn, model)
    TLF_nrmse = np.sqrt(np.power(TLF_sim - parameters.TLF_exp, 2).mean()) / 61.9087
    TLF_nrmse_nn = np.sqrt(np.power(TLF_nn - parameters.TLF_exp, 2).mean()) / 61.9087
    TLF_error = 100.0 * abs(TLF_nrmse - TLF_nrmse_nn) / TLF_nrmse
    parameters.lambda_Tld_Chd = lambda_Tld_Chd
    parameters.lambda_Tld_BMPChd = lambda_Tld_BMPChd
    # TALF simulation
    lambda_bmp1a_Chd = parameters.lambda_bmp1a_Chd
    lambda_bmp1a_BMPChd = parameters.lambda_bmp1a_BMPChd
    lambda_Tld_Chd = parameters.lambda_Tld_Chd
    lambda_Tld_BMPChd = parameters.lambda_Tld_BMPChd
    parameters.lambda_bmp1a_Chd = 0.0
    parameters.lambda_bmp1a_BMPChd = 0.0
    parameters.lambda_Tld_Chd = 0.0
    parameters.lambda_Tld_BMPChd = 0.0
    TALF_sim, _ = solve_pde(parameters, parameters.WT_ref_exp, ref_sim)
    TALF_nn, _ = solve_pde_nn(parameters, parameters.WT_ref_exp, ref_nn, model)
    TALF_nrmse = np.sqrt(np.power(TALF_sim - parameters.TALF_exp, 2).mean()) / 61.9087
    TALF_nrmse_nn = np.sqrt(np.power(TALF_nn - parameters.TALF_exp, 2).mean()) / 61.9087
    TALF_error = 100.0 * abs(TALF_nrmse - TALF_nrmse_nn) / TALF_nrmse
    parameters.lambda_bmp1a_Chd = lambda_bmp1a_Chd
    parameters.lambda_bmp1a_BMPChd = lambda_bmp1a_BMPChd
    parameters.lambda_Tld_Chd = lambda_Tld_Chd
    parameters.lambda_Tld_BMPChd = lambda_Tld_BMPChd
    # SLF simulation
    Vs = parameters.Vs
    parameters.Vs = 0.0
    SLF_sim, _ = solve_pde(parameters, parameters.WT_ref_exp, ref_sim)
    SLF_nn, _ = solve_pde_nn(parameters, parameters.WT_ref_exp, ref_nn, model)
    SLF_nrmse = np.sqrt(np.power(SLF_sim - parameters.SLF_exp, 2).mean()) / 61.9087
    SLF_nrmse_nn = np.sqrt(np.power(SLF_nn - parameters.SLF_exp, 2).mean()) / 61.9087
    SLF_error = 100.0 * abs(SLF_nrmse - SLF_nrmse_nn) / SLF_nrmse
    parameters.Vs = Vs


    total_error = (WT_error + CLF_error + NLF_error + ALF_error + TLF_error + TALF_error + SLF_error) / 6.0
    
    #return [[WT_nrmse, WT_nrmse_nn], [CLF_nrmse, CLF_nrmse_nn], [NLF_nrmse, NLF_nrmse_nn], [ALF_nrmse, ALF_nrmse_nn],
    #        [TLF_nrmse, TLF_nrmse_nn], [TALF_nrmse, TALF_nrmse_nn], total_error]
    return [WT_error, CLF_error, NLF_error, ALF_error, TLF_error, TALF_error, SLF_error, total_error]

if __name__ == '__main__':
    #random.seed(0)
    os.environ['MKL_NUM_THREADS'] = '1'

    model = ModelSimple().cuda().eval()
    model_path = './model_best.pth.tar'
    print("=> loading checkpoint '{}'".format(model_path))
    checkpoint = torch.load(model_path)
    best_score = checkpoint['best_score']
    print(best_score)
    model.load_state_dict(checkpoint['state_dict'])
    print("=> loaded checkpoint '{}' (epoch {})".format(model_path, checkpoint['epoch']))

    parameters_list = []
    min_val = 1.0
    total_error = 0.0
    for i in range(10):
        parameters = Parameters()
        read_from_file(parameters, '../../../datasets/pde/val_data.csv')
        set_continuous_parameters(parameters)
        parameters_list.append(parameters)
    start_time = time()
    for i in range(10):
        results = run_simulation(parameters_list[i], model)
        total_error += results[-1]
        print(i, results)
        #break
    print(total_error / 10.0)
    #print(time()-start_time)
