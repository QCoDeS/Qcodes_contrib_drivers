"""
A collection of small utility functions
to help with the operation of the
M91 QCoDeS driver
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from enum import IntEnum
from types import SimpleNamespace
from typing import Any

vdp_pairs = ["A (1-2)", "B (2-3)", "C (3-4)", "D (4-1)"]
hall_pairs = ["A (5-6)", "B (5-1)", "C (5-2)", "D (5-3)", "E (5-4)", "F (6-1)"]

class plot_colour_modes(IntEnum):
    DARK = 0
    LIGHT = 10

def apply_plot_style(fig: matplotlib.figure.Figure, axs: matplotlib.axes._axes.Axes, colourMode: str) -> None:
    match colourMode:
        case plot_colour_modes.LIGHT:
            plot_face_colour = "gainsboro"
            axes_face_colour = "white"
            grid_colour = "darkgrey"
        case plot_colour_modes.DARK | _ :
            plot_face_colour = "dimgrey"
            axes_face_colour = "black"
            grid_colour = "silver"
    fig.set_facecolor(plot_face_colour)
    if isinstance(axs, np.ndarray):
        for ax in axs:
            if isinstance(ax, np.ndarray):
                for a in ax:
                    a.set_facecolor(axes_face_colour)
                    a.grid(visible=True, which = 'major', color = grid_colour, linestyle = '--')
            else:
                ax.set_facecolor(axes_face_colour)
                ax.grid(visible=True, which = 'major', color = grid_colour, linestyle = '--')
    else:
        axs.set_facecolor(axes_face_colour)
        axs.grid(visible=True, which = 'major', color = grid_colour, linestyle = '--')

def plot_check(check_results: SimpleNamespace, check_axs: np.ndarray[Any, np.dtype[np.object_]]) -> None:

    n_checks = len(check_results.ContactPairIVResults)
    pairs = vdp_pairs if n_checks == 4 else hall_pairs
    plot_points = len(check_results.ContactPairIVResults[0].IvCurvePoints)
    excitation_span = [check_results.Setup.ExcitationValueStart,
                       check_results.Setup.ExcitationValueEnd]
    excitation_type = check_results.Setup.ExcitationType

    for i in range(n_checks):
        volts = []
        amps = []
        fit = []
        for j in range(plot_points):
            volts.append(float(
                check_results.ContactPairIVResults[i].IvCurvePoints[j].VoltageInVolts))
            amps.append(float(
                check_results.ContactPairIVResults[i].IvCurvePoints[j].CurrentInAmps))
        fit.append(excitation_span[0]*check_results.ContactPairIVResults[i].Slope
                   + check_results.ContactPairIVResults[i].Offset)
        fit.append(excitation_span[1]*check_results.ContactPairIVResults[i].Slope
                   + check_results.ContactPairIVResults[i].Offset)
        if excitation_type == 1:
            check_axs[i].scatter(amps, volts, s=30, facecolors='none', edgecolors='deepskyblue')
            check_axs[i].set_xlabel('Current (A)')
            if i == 0:
                check_axs[i].set_ylabel('Voltage (V)')
        elif excitation_type == 0:
            check_axs[i].scatter(volts, amps, s=30, facecolors='none', edgecolors='deepskyblue')
            check_axs[i].set_xlabel('Voltage (V)')
            if i == 0:
                check_axs[i].set_ylabel('Current (A)')
        check_axs[i].plot(excitation_span, fit, color='darkorange')
        check_axs[i].set_title(f'Pair {pairs[i]}')
        check_axs[i].ticklabel_format(axis='both', style='scientific', scilimits=(-2, 2), useMathText='True')

def print_line(check_result: SimpleNamespace, i: int, pairs: list[str]) -> None:
    " Format and print a contact check data record"
    slope = check_result.Slope
    offset = check_result.Offset
    rsq = check_result.RSquared
    rsp_pass = check_result.RSquaredPass
    print(f'Pair {pairs[i]}:\t{slope:.6f}\t{offset:.6f}\t{rsq:.6f}\t{rsp_pass}')

def show_contact_check_results(check_results: list[SimpleNamespace]) -> None:
    " Print the contact check header then send the results for display "
    print("Results:")
    print("\t\tGradient\tIntercept\tR-squared\tPassed")
    sep=""
    for i in range(54):
        sep+='='
    print(f"\t\t{sep}")

    n_checks = len(check_results)
    pairs = vdp_pairs if n_checks == 4 else hall_pairs
    for i, data in enumerate(check_results):
        print_line(data, i, pairs)
