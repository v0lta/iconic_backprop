# based on https://gist.github.com/karpathy/d4dee566867f8291f086,
# https://github.com/wiseodd/hipsternet/blob/master/hipsternet/neuralnet.py
# see also https://arxiv.org/pdf/1503.04069.pdf

import numpy as np


class MSELoss(object):
    ''' Mean squared error loss function. '''
    def forward(self, label, out):
        diff = out - label
        return np.mean(0.5*diff*diff)

    def backward(self, label, out):
        return out - label


class Tanh(object):
    def forward(self, inputs):
        return np.tanh(inputs)

    def backward(self, inputs, delta):
        return (1. - np.tanh(inputs)*np.tanh(inputs))*delta

    def prime(self, inputs):
        return (1. - np.tanh(inputs)*np.tanh(inputs))


class Sigmoid(object):

    def sigmoid(self, inputs):
        sig = np.exp(inputs)/(1 + np.exp(inputs))
        return np.nan_to_num(sig)

    def forward(self, inputs):
        return self.sigmoid(inputs)

    def backward(self, inputs, delta):
        return self.sigmoid(inputs)*(1 - self.sigmoid(inputs))*delta

    def prime(self, inputs):
        return self.sigmoid(inputs)*(1 - self.sigmoid(inputs))


class BasicCell(object):
    """Basic (Elman) rnn cell."""

    def __init__(self, hidden_size=250, input_size=1, output_size=1,
                 activation=Tanh()):
        self.hidden_size = hidden_size
        # input to hidden
        self.Wxh = np.random.randn(1, hidden_size, input_size)
        self.Wxh = self.Wxh / np.sqrt(hidden_size)
        # hidden to hidden
        self.Whh = np.random.randn(1, hidden_size, hidden_size)
        self.Whh = self.Whh / np.sqrt(hidden_size)
        # hidden to output
        self.Why = np.random.randn(1, output_size, hidden_size)
        self.Why = self.Why / np.sqrt(hidden_size)
        # hidden bias
        self.bh = np.zeros((1, hidden_size, 1))
        # output bias
        self.by = np.random.randn(1, output_size, 1)*0.01
        self.activation = activation

    def zero_state(self, batch_size):
        return np.zeros((batch_size, self.hidden_size, 1))

    def forward(self, x, h):
        h = np.matmul(self.Whh, h) + np.matmul(self.Wxh, x) + self.bh
        h = self.activation.forward(h)
        y = np.matmul(self.Why, h) + self.by
        return y, h

    def backward(self, deltay, deltah, x, h, hm1):
        # output backprop
        dydh = np.matmul(np.transpose(self.Why, [0, 2, 1]), deltay)
        dWhy = np.matmul(deltay, np.transpose(h, [0, 2, 1]))
        dby = 1*deltay

        delta = self.activation.backward(inputs=h, delta=dydh) + deltah
        # recurrent backprop
        dWxh = np.matmul(delta, np.transpose(x, [0, 2, 1]))
        dWhh = np.matmul(delta, np.transpose(hm1, [0, 2, 1]))
        dbh = 1*delta
        deltah = np.matmul(np.transpose(self.Whh, [0, 2, 1]), delta)
        # deltah, dWhh, dWxh, dbh, dWhy, dby
        return deltah, dWhh, dWxh, dbh, dWhy, dby


class LSTMcell(object):
    def __init__(self, hidden_size=250,
                 input_size=1, output_size=1):
        self.hidden_size = hidden_size
        # create the weights
        s = 1./np.sqrt(hidden_size)
        self.Wz = np.random.randn(1, hidden_size, input_size)*s
        self.Wi = np.random.randn(1, hidden_size, input_size)*s
        self.Wf = np.random.randn(1, hidden_size, input_size)*s
        self.Wo = np.random.randn(1, hidden_size, input_size)*s

        self.Rz = np.random.randn(1, hidden_size, hidden_size)*s
        self.Ri = np.random.randn(1, hidden_size, hidden_size)*s
        self.Rf = np.random.randn(1, hidden_size, hidden_size)*s
        self.Ro = np.random.randn(1, hidden_size, hidden_size)*s

        self.bz = np.zeros((1, hidden_size, 1))*s
        self.bi = np.random.randn(1, hidden_size, 1)*s
        self.bf = np.random.randn(1, hidden_size, 1)*s
        self.bo = np.random.randn(1, hidden_size, 1)*s

        self.pi = np.random.randn(1, hidden_size, 1)*s
        self.pf = np.random.randn(1, hidden_size, 1)*s
        self.po = np.random.randn(1, hidden_size, 1)*s

        self.state_activation = Tanh()
        self.out_activation = Tanh()
        self.gate_i_act = Sigmoid()
        self.gate_f_act = Sigmoid()
        self.gate_o_act = Sigmoid()

        self.Wout = np.random.randn(1, output_size, hidden_size)*s
        self.bout = np.random.randn(1, output_size, 1)

    def zero_state(self, batch_size):
        return np.zeros((batch_size, self.hidden_size, 1))

    def forward(self, x, h, c):
        # block input
        zbar = np.matmul(self.Wz, x) + np.matmul(self.Rz, h) + self.bz
        z = self.state_activation.forward(zbar)
        # input gate
        ibar = np.matmul(self.Wi, x) + np.matmul(self.Ri, h) + self.pi*c \
            + self.bi
        i = self.gate_i_act.forward(ibar)
        # forget gate
        fbar = np.matmul(self.Wf, x) + np.matmul(self.Rf, h) + self.pf*c \
            + self.bf
        f = self.gate_f_act.forward(fbar)
        # cell
        c = z * i + c * f
        # output gate
        obar = np.matmul(self.Wo, x) + np.matmul(self.Ro, h) + self.po*c \
            + self.bo
        o = self.gate_o_act.forward(obar)
        # block output
        h = self.out_activation.forward(c)*o
        # linear projection
        y = np.matmul(self.Wout, h) + self.bout
        return y, c, h, zbar, ibar, fbar, obar

    def backward(self, x, h, zbar, ibar, fbar, obar, c, cm1,
                 deltay, deltaz, deltac, deltao, deltai, deltaf):
        # projection backward
        dWout = np.matmul(deltay, np.transpose(h, [0, 2, 1]))
        dbout = 1*deltay
        deltay = np.matmul(np.transpose(self.Wout, [0, 2, 1]), deltay)
        
        # block backward
        deltah = deltay \
            + np.matmul(np.transpose(self.Rz, [0, 2, 1]), deltaz) \
            + np.matmul(np.transpose(self.Ri, [0, 2, 1]), deltai) \
            + np.matmul(np.transpose(self.Rf, [0, 2, 1]), deltaf) \
            + np.matmul(np.transpose(self.Ro, [0, 2, 1]), deltao)

        deltao = deltah * self.out_activation.forward(c)\
            * self.gate_o_act.prime(obar)
        deltac = deltah * self.gate_o_act.forward(obar)\
            * self.state_activation.prime(c)\
            + self.po*deltao \
            + self.pi*deltai \
            + self.pf*deltaf \
            + deltac*self.gate_f_act.forward(fbar)
        deltaf = deltac * cm1 * self.gate_f_act.prime(fbar)
        deltai = deltac * self.state_activation.forward(zbar)
        deltaz = deltac*self.gate_i_act.forward(ibar)\
            * self.state_activation.prime(zbar)

        # weight backward
        dWz = np.matmul(deltaz, np.transpose(x, [0, 2, 1]))
        dWi = np.matmul(deltai, np.transpose(x, [0, 2, 1]))
        dWf = np.matmul(deltaf, np.transpose(x, [0, 2, 1]))
        dWo = np.matmul(deltao, np.transpose(x, [0, 2, 1]))

        dRz = np.matmul(deltaz, np.transpose(h, [0, 2, 1]))
        dRi = np.matmul(deltai, np.transpose(h, [0, 2, 1]))
        dRf = np.matmul(deltaf, np.transpose(h, [0, 2, 1]))
        dRo = np.matmul(deltao, np.transpose(h, [0, 2, 1]))

        dbz = deltaz
        dbi = deltai
        dbf = deltaf
        dbo = deltao

        dpi = c*deltai
        dpf = c*deltaf
        dpo = c*deltao

        return deltac, deltaz, deltao, deltai, deltaf, \
            dWout, dbout, dWz, dWi, dWf, dWo, dRz, dRi,\
            dRf, dRo, dbz, dbi, dbf, dbo,\
            dpi, dpf, dpo


class GRU(object):
    def __init__(self, hidden_size=250,
                 input_size=1, output_size=1):

        self.hidden_size = hidden_size
        # create the weights
        s = 1./np.sqrt(hidden_size)
        self.Wr = np.random.randn(1, hidden_size, input_size)*s
        self.Wu = np.random.randn(1, hidden_size, input_size)*s
        self.W = np.random.randn(1, hidden_size, input_size)*s

        self.Vr = np.random.randn(1, hidden_size, hidden_size)*s
        self.Vu = np.random.randn(1, hidden_size, hidden_size)*s
        self.V = np.random.randn(1, hidden_size, hidden_size)*s

        self.br = np.zeros((1, hidden_size, 1))*s
        self.bu = np.random.randn(1, hidden_size, 1)*s
        self.b = np.random.randn(1, hidden_size, 1)*s

        self.state_activation = Tanh()
        self.out_activation = Tanh()
        self.gate_r_act = Sigmoid()
        self.gate_u_act = Sigmoid()

        self.Wout = np.random.randn(1, output_size, hidden_size)*s
        self.bout = np.random.randn(1, output_size, 1)

    def zero_state(self, batch_size):
        return np.zeros((batch_size, self.hidden_size, 1))

    def forward(self, x, h, c):
        # reset gate
        rbar = np.matmul(self.Wr, x) + np.matmul(self.Vr, h) + self.br
        r = self.gate_r_act.forward(rbar)
        # update gate
        ubar = np.matmul(self.Wu, x) + np.matmul(self.Vu, h) + self.b
        u = self.gate_u_act.forward(ubar)
        # block input
        hbar = r*h
        zbar = np.matmul(self.W, x) + np.matmul(self.V, hbar) + self.b
        z = self.state_activation.forward(zbar)
        # recurrent update
        hnew = u*z + (1 - u)*h
        # linear projection
        y = np.matmul(self.Wout, h) + self.bout

        return y, hnew, zbar, rbar, ubar

    def backward(self, x, h, hm1, zbar, ubar, rbar,
                 deltay, deltaz, deltah, deltau, deltar):
        # projection backward
        dWout = np.matmul(deltay, np.transpose(h, [0, 2, 1]))
        dbout = 1*deltay
        deltay = np.matmul(np.transpose(self.Wout, [0, 2, 1]), deltay)

        # block backward
        wtdz = np.matmul(np.transpose(self.W, [0, 2, 1]), deltaz)
        deltah = deltay \
            + (1 - self.gate)*self.gate_u_act(ubar) \
            + self.gate_r_act(rbar)*wtdz \
            + np.matmul(np.transpose(self.Wu, [0, 2, 1]), deltau) \
            + np.matmul(np.transpose(self.Wr, [0, 2, 1]), deltar)

        deltaz = self.gate_u_act(ubar) \
            * deltah * self.state_activation.prime(zbar)
        deltau = (self.state_activation(zbar) - h) \
            * deltah * self.gate_u_act(ubar)
        deltar = h*wtdz*self.gate_r_act.prime(rbar)

        # weight backward
        dW = np.matmul(deltaz, np.transpose(x, [0, 2, 1]))
        dWu = np.matmul(deltau, np.transpose(x, [0, 2, 1]))
        dWr = np.matmul(deltar, np.transpose(x, [0, 2, 1]))

        dV = np.matmul(deltaz, np.transpose(h, [0, 2, 1]))
        dVu = np.matmul(deltau, np.transpose(h, [0, 2, 1]))
        dVr = np.matmul(deltar, np.transpose(h, [0, 2, 1]))

        db = deltaz
        dbu = deltau
        dbr = deltar

        return deltah, deltaz, deltau, deltar,\
            dWout, dbout, dW, dWu, dWr, dV, dVu,\
            dVr, db, dbu, dbr
