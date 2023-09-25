from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any


class Solver(ABC):
    def __init__(self, instance, statistics, threads, free_search=True):
        self.instance = instance
        self.model = self.set_model()
        self.solver = self.set_solver()
        self.free_search = free_search
        self.statistics = statistics
        self.objectives = None
        self.threads = self.set_threads(threads)
        Solver.init_statistics(statistics)

    @abstractmethod
    def set_model(self):
        pass

    @abstractmethod
    def set_solver(self):
        pass

    @abstractmethod
    def set_threads(self, threads):
        pass

    @staticmethod
    def init_statistics(statistics):
        # todo remove the cp_ part from the statistics names
        statistics["cp_solutions"] = 0
        statistics["cp_total_nodes"] = 0
        statistics["time_cp_sec"] = 0
        statistics["time_fzn_sec"] = 0
        statistics["cp_solutions_list"] = []

    @abstractmethod
    def solve(self, optimize_not_satisfy = True):
        pass

    def set_optimization_sense(self, sense):
        if sense == "min":
            self.set_minimization()
        elif sense == "max":
            self.set_maximization()
        else:
            raise ValueError("Invalid optimization sense: " + sense)

    @abstractmethod
    def add_variables(self):
        pass

    @abstractmethod
    def add_basic_constraints(self):
        pass

    @abstractmethod
    def add_constraints_leq(self, constraint, rhs):
        pass

    @abstractmethod
    def remove_constraints(self, constraint):
        pass

    @abstractmethod
    def set_minimization(self):
        pass

    @abstractmethod
    def set_maximization(self):
        pass

    @abstractmethod
    def set_time_limit(self, timeout):
        pass

    @abstractmethod
    def set_single_objective(self, objective_expression):
        pass

    @abstractmethod
    def get_main_objective(self):
        pass

    @abstractmethod
    def build_objective_e_constraint_saugmecon(self, range_array):
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def get_solution_values(self):
        pass

    @abstractmethod
    def get_selected_images(self):
        pass

    # status---------------------------------------------------
    @abstractmethod
    def get_status(self):
        pass

    @abstractmethod
    def status_time_limit(self):
        pass

    @abstractmethod
    def status_infeasible(self):
        pass
    # status end-------------------------------------------------

    def update_statistics(self, seconds):
        # todo remove the cp_ part from the statistics names
        self.statistics["time_cp_sec"] += seconds
        solution = self.get_complete_solution()
        if solution is None:
            return
        self.statistics["cp_solutions"] += 1
        self.statistics["cp_total_nodes"] += self.get_nodes_solution(solution)
        self.statistics["time_cp_sec"] += seconds
        self.statistics["cp_solutions_list"].append(self.statistics["time_cp_sec"])

    @abstractmethod
    def get_complete_solution(self):
        pass

    @abstractmethod
    def get_nodes_solution(self, solution):
        pass

    # def prepare_solution(self):
    #     one_solution = self.get_solution_values()
    #     selected_images = self.get_selected_images()
    #     taken = [False] * len(self.instance.images)
    #     for image in selected_images:
    #         taken[image] = True
    #     ref_points = self.ref_points
    #     # ef_array = copy.deepcopy(ef_array)
    #     solution = Solution(objs=one_solution, taken=taken,
    #                         minimize_objs=[True] * len(one_solution), ref_point=ref_points)
    #     status = self.get_status()
    #     statistics = None
    #     minizinc_formatted_solution = MinizincResultFormat(status=status, solution=solution, statistics=statistics)
    #     return minizinc_formatted_solution


# @dataclass
# class MinizincResultFormat:
#     status: None
#     solution: Any
#     statistics: None
#
#     def __getitem__(self, key):
#         if isinstance(self.solution, list):
#             if isinstance(key, tuple):
#                 return getattr(self.solution.__getitem__(key[0]), key[1])
#             else:
#                 return self.solution.__getitem__(key)
#         else:
#             return getattr(self.solution, key)
#
# @dataclass
# class Solution:
#     objs: List[int]
#     minimize_objs: List[bool]
#     taken: List[bool]
#     ref_point: List[int]
#     # ef_array: List[int]



