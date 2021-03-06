"""
Hidden Markov Model Evolver

Usage:
    fsm_evolve.py [-h] [--generations GENERATIONS] [--population POPULATION]
    [--mu MUTATION_RATE] [--bottleneck BOTTLENECK] [--processes PROCESSORS]
    [--output OUTPUT_FILE] [--objective OBJECTIVE] [--repetitions REPETITIONS]
    [--turns TURNS] [--noise NOISE] [--nmoran NMORAN]
    [--states NUM_STATES]

Options:
    -h --help                   Show help
    --generations GENERATIONS   Generations to run the EA [default: 500]
    --population POPULATION     Population size  [default: 40]
    --mu MUTATION_RATE          Mutation rate [default: 0.1]
    --bottleneck BOTTLENECK     Number of individuals to keep from each generation [default: 10]
    --processes PROCESSES       Number of processes to use [default: 1]
    --output OUTPUT_FILE        File to write data to [default: hmm_params.csv]
    --objective OBJECTIVE       Objective function [default: score]
    --repetitions REPETITIONS   Repetitions in objective [default: 100]
    --turns TURNS               Turns in each match [default: 200]
    --noise NOISE               Match noise [default: 0.00]
    --nmoran NMORAN             Moran Population Size, if Moran objective [default: 4]
    --states NUM_STATES         Number of FSM states [default: 5]
"""

#####
# This is a potential candidate for PSO optimization, which will require
# combining the matrices.
#####

import random
from random import randrange, choice

from docopt import docopt
import numpy as np

from axelrod import Actions, flip_action
from axelrod.strategies.hmm import HMMPlayer

from evolve_utils import Params, Population, prepare_objective

C, D = Actions.C, Actions.D


def copy_lists(rows):
    new_rows = list(map(list, rows))
    return new_rows

def random_vector(size):
    """Create a random vector of values in [0, 1] that sums to 1."""
    vector = []
    s = 1
    for _ in range(size - 1):
        r = s * random.random()
        vector.append(r)
        s -= r
    vector.append(s)
    return vector

def normalize_vector(vec):
    s = sum(vec)
    vec = [v / s for v in vec]
    return vec

def mutate_row(row, mutation_rate):
    randoms = np.random.random(len(row))
    for i in range(len(row)):
        if randoms[i] < mutation_rate:
            ep = random.uniform(-1, 1) / 4
            row[i] += ep
            if row[i] < 0:
                row[i] = 0
            if row[i] > 1:
                row[i] = 1
    return row


class HMMParams(Params):

    def __init__(self, num_states, mutation_rate=None, transitions_C=None,
                 transitions_D=None, emission_probabilities=None,
                 initial_state=0, initial_action=C):
        self.PlayerClass = HMMPlayer
        self.num_states = num_states
        if mutation_rate is None:
            self.mutation_rate = 10 / (num_states ** 2)
        else:
            self.mutation_rate = mutation_rate
        if transitions_C is None:
            self.randomize()
        else:
            # Make sure to copy the lists
            self.transitions_C = copy_lists(transitions_C)
            self.transitions_D = copy_lists(transitions_D)
            self.emission_probabilities = list(emission_probabilities)
            self.initial_state = initial_state
            self.initial_action = initial_action


    def player(self):
        player = self.PlayerClass(self.transitions_C, self.transitions_D,
                                  self.emission_probabilities,
                                  self.initial_state, self.initial_action)
        return player

    def copy(self):
        return HMMParams(self.num_states, self.mutation_rate,
                         self.transitions_C, self.transitions_D,
                         self.emission_probabilities,
                         self.initial_state, self.initial_action)

    @staticmethod
    def random_params(num_states):
        t_C = []
        t_D = []
        for _ in range(num_states):
            t_C.append(random_vector(num_states))
            t_D.append(random_vector(num_states))
        initial_state = randrange(num_states)
        # initial_action = choice([C, D])
        initial_action = C
        return t_C, t_D, initial_state, initial_action

    def randomize(self):
        t_C, t_D, initial_state, initial_action = self.random_params(self.num_states)
        self.emission_probabilities = [random.random() for _ in range(self.num_states)]
        self.transitions_C = t_C
        self.transitions_D = t_D
        self.initial_state = initial_state
        self.initial_action = initial_action

    @staticmethod
    def mutate_rows(rows, mutation_rate):
        for i, row in enumerate(rows):
            row = mutate_row(row, mutation_rate)
            rows[i] = normalize_vector(row)
        return rows

    def mutate(self):
        self.transitions_C = self.mutate_rows(
            self.transitions_C, self.mutation_rate)
        self.transitions_D = self.mutate_rows(
            self.transitions_D, self.mutation_rate)
        self.emission_probabilities = mutate_row(
            self.emission_probabilities, self.mutation_rate)
        if random.random() < self.mutation_rate / 10:
            self.initial_action = flip_action(self.initial_action)
        if random.random() < self.mutation_rate / (10 * self.num_states):
            self.initial_state = randrange(self.num_states)
        # Change node size?

    @staticmethod
    def crossover_rows(rows1, rows2):
        num_states = len(rows1)
        crosspoint = randrange(num_states)
        new_rows = copy_lists(rows1[:crosspoint])
        new_rows += copy_lists(rows2[crosspoint:])
        return new_rows

    @staticmethod
    def crossover_weights(w1, w2):
        crosspoint = random.randrange(len(w1))
        new_weights = list(w1[:crosspoint]) + list(w2[crosspoint:])
        return new_weights

    def crossover(self, other):
        # Assuming that the number of states is the same
        t_C = self.crossover_rows(self.transitions_C, other.transitions_C)
        t_D = self.crossover_rows(self.transitions_D, other.transitions_D)
        emissions = self.crossover_weights(
            self.emission_probabilities, other.emission_probabilities)
        return HMMParams(self.num_states, self.mutation_rate,
                         t_C, t_D, emissions,
                         self.initial_state, self.initial_action)

    @staticmethod
    def repr_rows(rows):
        ss = []
        for row in rows:
            ss.append("_".join(list(map(str, row))))
        return "|".join(ss)

    def __repr__(self):
        return "{}:{}:{}:{}:{}".format(
            self.initial_state,
            self.initial_action,
            self.repr_rows(self.transitions_C),
            self.repr_rows(self.transitions_D),
            self.repr_rows([self.emission_probabilities])
        )

    @classmethod
    def parse_repr(cls, s):
        def parse_matrix(sm):
            rows = []
            lines = sm.split('|')
            for line in lines:
                row = line.split('_')
                row = list(map(float, row))
                rows.append(row)
            return row
        lines = s.split(':')
        initial_state = int(lines[0])
        initial_action = lines[1]
        t_C = parse_matrix(lines[2])
        t_D = parse_matrix(lines[3])
        ps = parse_matrix(lines[4])
        return cls(t_C, t_D, ps, initial_state, initial_action)


if __name__ == '__main__':
    arguments = docopt(__doc__, version='HMM Evolver 0.3')
    print(arguments)
    processes = int(arguments['--processes'])

    # Vars for the genetic algorithm
    population = int(arguments['--population'])
    mutation_rate = float(arguments['--mu'])
    generations = int(arguments['--generations'])
    bottleneck = int(arguments['--bottleneck'])
    output_filename = arguments['--output']

    # Objective
    name = str(arguments['--objective'])
    repetitions = int(arguments['--repetitions'])
    turns = int(arguments['--turns'])
    noise = float(arguments['--noise'])
    nmoran = int(arguments['--nmoran'])

    # FSM
    num_states = int(arguments['--states'])
    param_args = [num_states, mutation_rate]

    objective = prepare_objective(name, turns, noise, repetitions, nmoran)
    population = Population(HMMParams, param_args, population, objective,
                            output_filename, bottleneck, processes=processes)
    population.run(generations)
