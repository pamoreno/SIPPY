# -*- coding: utf-8 -*-
"""
Created on Mon May 28 13:03:03 2018

@author: Riccardo Bacci di Capaci

CST example

A Continuous Stirred Tank to be identified from input-output data

"""

# import package
from __future__ import division         # compatibility layer between Python 2 and Python 3
from past.utils import old_div
from sippy import functionset as fset
from sippy import functionsetSIM as fsetSIM
from sippy import *
#
# import functionset as fset
# import functionsetSIM as fsetSIM
# from __init__ import *
#
import numpy as np
import control
import control.matlab as cnt
import matplotlib.pyplot as plt

from distutils.version import StrictVersion

if StrictVersion(control.__version__) >= StrictVersion('0.8.2'):
	lsim = cnt.lsim
else:
	def lsim(sys, U = 0.0, T = None, X0 = 0.0):
		U_ = U
		if isinstance(U_, (np.ndarray, list)):
			U_ = U_.T
		return cnt.lsim(sys, U_, T, X0)

# sampling time
ts = 1.         # [min]

# time settings (t final, samples number, samples vector)
tfin = 4000
npts = int(old_div(tfin,ts)) + 1
Time = np.linspace(0, tfin, npts)

# Data
V = 10.0        # tank volume [m^3]         --> assumed to be constant
ro = 1100.0     # solution density [kg/m^3] --> assumed to be constant
cp = 4.180     # specific heat [kJ/kg*K]    --> assumed to be constant
Lam = 2272.0    # latent heat   [kJ/kg]     --> assumed to be constant (Tvap = 100°C, Pvap = 1atm)
# initial conditions
# Ca_0
# Tin_0


# VARIABLES

# 4 Inputs
# - as v. manipulated
# Input Flow rate Fin           [m^3/min]
# Steam Flow rate W             [kg/min]
# - as disturbances 
# Input Concentration Ca_in     [kg salt/m^3 solution]
# Input Temperature T_in        [°C]
# U = [F, W, Ca_in, T_in]
m = 4   

# 2 Outputs
# Output Concentration Ca       [kg salt/m^3 solution]  (Ca = Ca_out)
# Output Temperature T          [°C]                    (T = T_out)
# X = [Ca, T]
p = 2 


# Function with System Dynamics
def Fdyn(X,U):
    # Balances
    
    # V is constant ---> perfect Level Control
    # ro*F_in = ro*F_out = ro*F --> F = F_in = F_out at each instant
    
    # Mass Balance on A
    # Ca_in*F - Ca*F = V*dCA/dt
    #
    dx_0 = (U[2]*U[0] - X[0]*U[0])/V
    
    # Energy Balance
    # ro*cp*F*T_in - ro*cp*F*T + W*Lam = (V*ro*cp)*dT/dt
    #
    dx_1 = (ro*cp*U[0]*U[3] - ro*cp*U[0]*X[1] + U[1]*Lam)/(V*ro*cp)
    
    fx = np.append(dx_0,dx_1)
    
    return fx
    
# Build input sequences 
U = np.zeros((m,npts))
   
# manipulated inputs as GBN
# Input Flow rate Fin = F = U[0]    [m^3/min]
prob_switch_1 = 0.05
F_min = 0.4
F_max = 0.6 
Range_GBN_1 = [F_min,F_max]
U[0,:] = fset.GBN_seq(npts, prob_switch_1, Range = Range_GBN_1)    
# Steam Flow rate W = U[1]          [kg/min]
prob_switch_2 = 0.05
W_min = 20
W_max = 40
Range_GBN_2 = [W_min,W_max]
U[1,:] = fset.GBN_seq(npts, prob_switch_2, Range = Range_GBN_2)

# disturbance inputs as RW (random-walk)

# Input Concentration Ca_in = U[2]  [kg salt/m^3 solution]
Ca_0 = 10.0                         # initial condition
sigma_Ca = 0.01                      # variation
U[2,:] = fset.RW_seq(npts, Ca_0, sigma = sigma_Ca)
# Input Temperature T_in            [°C]
Tin_0 = 25.0                        # initial condition
sigma_T = 0.01                       # variation
U[3,:] = fset.RW_seq(npts, Tin_0, sigma = sigma_T)
   

##### COLLECT DATA

# Output Initial conditions
Caout_0 = Ca_0
Tout_0 = (ro*cp*U[0,0]*Tin_0 + U[1,0]*Lam)/(ro*cp*U[0,0]) 
Xo1 = Caout_0*np.ones((1,npts))
Xo2 = Tout_0*np.ones((1,npts))
X = np.vstack((Xo1,Xo2))

# Run Simulation
for j in range(npts-1):  
    # Explicit Runge-Kutta 4 (TC dynamics is integrateed by hand)        
    Mx = 5                  # Number of elements in each time step
    dt = ts/Mx              # integration step
    # Output & Input
    X0k = X[:,j]
    Uk = U[:,j]
    # Integrate the model
    for i in range(Mx):         
        k1 = Fdyn(X0k, Uk)
        k2 = Fdyn(X0k + dt/2.0*k1, Uk)
        k3 = Fdyn(X0k + dt/2.0*k2, Uk)
        k4 = Fdyn(X0k + dt*k3, Uk)
        Xk_1 = X0k + (dt/6.0)*(k1 + 2.0*k2 + 2.0*k3 + k4)
    X[:,j+1] = Xk_1

# Add noise (with assigned variances)
var = [0.001, 0.001]    
noise = fset.white_noise_var(npts,var)    

# Build Output
Y = X + noise


#### IDENTIFICATION STAGE

# ARX - mimo
na_ords = [5,5] 
nb_ords = [[3,1,3,1], [3,3,1,3]]
theta = [[0,0,0,0], [0,0,0,0]]
# call id
Id_ARX = system_identification(Y, U, 'ARX', centering = 'MeanVal', ARX_orders = [na_ords, nb_ords, theta])

# ARMAX - mimo
na_ords = [5,5] 
nb_ords = [[2,2,2,2], [2,2,2,2]]
nc_ords = [3,3]
theta = [[1,1,1,1], [1,1,1,1]]
# Number of iterations
n_iter = 300
# call id
Id_ARMAX = system_identification(Y, U, 'ARMAX', centering = 'InitVal', ARMAX_orders = [na_ords, nb_ords, nc_ords, theta], ARMAX_max_iterations = n_iter)

# SS - mimo
# choose method
method = 'PARSIM-K'
SS_ord = 2
Id_SS = system_identification(Y, U, method, SS_fixed_order = SS_ord)

# GETTING RESULTS (Y_id)
# ARX
Y_arx = Id_ARX.Yid
# ARMAX    
Y_armax = Id_ARMAX.Yid
# SS
x_ss, Y_ss = fsetSIM.SS_lsim_process_form(Id_SS.A,Id_SS.B,Id_SS.C,Id_SS.D,U,Id_SS.x0)


##### PLOTS

# Input
plt.close('all')
plt.figure(1)

str_input = ['F [m$^3$/min]', 'W [kg/min]', 'Ca$_{in}$ [kg/m$^3$]', 'T$_{in}$ [$^o$C]']
for i in range(m):  
    plt.subplot(m,1,i+1)
    plt.plot(Time,U[i,:])
    plt.ylabel("Input " + str(i+1))
    plt.ylabel(str_input[i])
    plt.grid()
    plt.xlabel("Time")
    plt.axis([0, tfin, 0.95*np.amin(U[i,:]), 1.05*np.amax(U[i,:])])
    if i == 0:
        plt.title('identification')

# Output
plt.figure(2)
str_output = ['Ca [kg/m$^3$]', 'T [$^o$C]']
for i in range(p): 
    plt.subplot(p,1,i+1)
    plt.plot(Time,Y[i,:],'b')
    plt.plot(Time,Y_arx[i,:],'g')
    plt.plot(Time,Y_armax[i,:],'r')
    plt.plot(Time,Y_ss[i,:],'m')
    plt.ylabel("Output " + str(i+1))
    plt.ylabel(str_output[i])
    plt.legend(['Data','ARX','ARMAX','SS'])
    plt.grid()
    plt.xlabel("Time")
    if i == 0:
        plt.title('identification')

