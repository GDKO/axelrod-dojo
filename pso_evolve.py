"""
Particle Swarm strategy training code.

Original version by Georgios Koutsovoulos @GDKO :
  https://gist.github.com/GDKO/60c3d0fd423598f3c4e4
Based on Martin Jones @mojones original LookerUp code

Usage:
    pso_evolve.py [-h] [--generations GENERATIONS] [--population POPULATION]
    [--processes PROCESSORS] [--output OUTPUT_FILE] [--objective OBJECTIVE]
    [--repetitions REPETITIONS] [--turns TURNS] [--noise NOISE]
    [--nmoran NMORAN]
    [--plays PLAYS] [--op_plays OP_PLAYS] [--op_start_plays OP_START_PLAYS]

Options:
    -h --help                   Show help
    --generations GENERATIONS   Generations to run the EA [default: 100]
    --population POPULATION     Starting population size  [default: 40]
    --processes PROCESSES       Number of processes to use [default: 1]
    --output OUTPUT_FILE        File to write data to [default: pso_tables.csv]
    --objective OBJECTIVE       Objective function [default: score]
    --repetitions REPETITIONS   Repetitions in objective [default: 100]
    --turns TURNS               Turns in each match [default: 200]
    --noise NOISE               Match noise [default: 0.00]
    --nmoran NMORAN             Moran Population Size, if Moran objective [default: 4]
    --plays PLAYS               Number of recent plays in the lookup table [default: 2]
    --op_plays OP_PLAYS         Number of recent plays in the lookup table [default: 2]
    --op_start_plays OP_START_PLAYS     Number of opponent starting plays in the lookup table [default: 2]
"""

from docopt import docopt
import pyswarm

from axelrod import Gambler
from axelrod.strategies.lookerup import (
    create_lookup_table_keys, Plays)
from evolve_utils import prepare_objective, score_for


def optimizepso(param_args, objective, opponents=None):
    def f(pattern):
        self_plays, op_plays, op_openings = param_args
        params = Plays(self_plays=self_plays, op_plays=op_plays,
                       op_openings=op_openings)
        return -score_for(Gambler, objective,
                          args=[None, None, pattern, params],
                          opponents=opponents)
    return f

if __name__ == "__main__":
    arguments = docopt(__doc__, version='PSO Evolve 0.3')
    print(arguments)
    processes = int(arguments['--processes'])

    # Population Args
    population = int(arguments['--population'])
    generations = int(arguments['--generations'])

    # Objective
    name = str(arguments['--objective'])
    repetitions = int(arguments['--repetitions'])
    turns = int(arguments['--turns'])
    noise = float(arguments['--noise'])
    nmoran = int(arguments['--nmoran'])

    # Lookup Tables
    plays = int(arguments['--plays'])
    op_plays = int(arguments['--op_plays'])
    op_start_plays = int(arguments['--op_start_plays'])
    param_args = [plays, op_plays, op_start_plays]

    objective = prepare_objective(name, turns, noise, repetitions, nmoran)

    size = len(create_lookup_table_keys(plays, op_plays, op_start_plays))
    lb = [0] * size
    ub = [1] * size

    optimizer = optimizepso(param_args, objective)

    # There is a multiprocessing version (0.7) of pyswarm available at
    # https://github.com/tisimst/pyswarm, just pass processes=X
    # Pip installs version 0.6
    if pyswarm.__version__ == "0.7":
        xopt, fopt = pyswarm.pso(
            optimizer, lb, ub, swarmsize=population, maxiter=generations,
            debug=True, phip=0.8, phig=0.8, omega=0.8, processes=processes)
    else:
        xopt, fopt = pyswarm.pso(
            optimizer, lb, ub, swarmsize=population, maxiter=generations,
            debug=True, phip=0.8, phig=0.8, omega=0.8)
    print(xopt)
    print(fopt)
