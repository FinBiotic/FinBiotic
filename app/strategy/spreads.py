#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 10 08:12:26 2017

@author: jonfroiland
"""


class Spreads(object):

    def __init__(self, dfD, mid):
        self.dfD = dfD
        self.mid = float(mid)
        self.pivot, self.rl1, self.rl2, self.rl3, \
            self.sl1, self.sl2, self.sl3 = self.spreads()

    def spreads(self):
        # Do not change or you will get SINGLE POSITIONER INDEX fault.
        pivot = self.dfD.iloc[-1]['Daily Pivot Point'].round(5)
        rl1 = self.dfD.iloc[-1]['Resistance Level 1'].round(5)
        rl2 = self.dfD.iloc[-1]['Resistance Level 2'].round(5)
        rl3 = self.dfD.iloc[-1]['Resistance Level 3'].round(5)
        sl1 = self.dfD.iloc[-1]['Support Level 1'].round(5)
        sl2 = self.dfD.iloc[-1]['Support Level 2'].round(5)
        sl3 = self.dfD.iloc[-1]['Support Level 3'].round(5)
        return float(pivot), float(rl1), float(rl2), float(rl3), float(sl1), float(sl2), float(sl3)

    def spreadRates(self):
        if self.pivot < self.mid < self.rl1:
            over = self.mid - self.pivot
            spread = self.rl1 - self.pivot
            rate1 = round(over/spread, 5)
            rate2 = round(1 - rate1, 5)
            # print "PP_RL1", over, spread, rate1, rate2
            return rate1, rate2

        elif self.rl1 < self.mid < self.rl2:
            over = self.mid - self.rl1
            spread = self.rl2 - self.rl1
            rate1 = round(over/spread, 5)
            rate2 = round(1 - rate1, 5)
            # print "RL1_RL2", over, spread, rate1, rate2
            return rate1, rate2

        elif self.rl2 < self.mid < self.rl3:
            over = self.mid - self.rl2
            spread = self.rl3 - self.rl2
            rate1 = round(over/spread, 5)
            rate2 = round(1 - rate1, 5)
            # print "RL2_RL3", over, spread, rate1, rate2
            return rate1, rate2

        elif self.pivot > self.mid > self.sl1:
            over = self.mid - self.sl1
            spread = self.pivot - self.sl1
            rate1 = round(over/spread, 5)
            rate2 = round(1 - rate1, 5)
            # print "PP_SL1", over, spread, rate1, rate2
            return rate1, rate2

        elif self.sl1 > self.mid > self.sl2:
            over = self.mid - self.sl2
            spread = self.sl1 - self.sl2
            rate1 = round(over/spread, 5)
            rate2 = round(1 - rate1, 5)
            # print "SL1_SL2", over, spread, rate1, rate2
            return rate1, rate2

        elif self.sl2 > self.mid > self.sl3:
            over = self.mid - self.sl3
            spread = self.sl2 - self.sl3
            rate1 = round(over/spread, 5)
            rate2 = round(1 - rate1, 5)
            # print "SL2_SL3", over, spread, rate1, rate2
            return rate1, rate2

        else:
            pass
