from model.mo.MosaicCloudMIPmodel import MosaicCloudMIPmodel
from model.mo.Solvers.Solver import Solver
import gurobipy as gp


class GurobiSolver(Solver):
    def get_solution_values(self):
        # todo fix this method
        one_solution = [self.solver.get_main_objective().getValue()]
        for i in range(len(self.mosaic_model.objectives)):
            if type(self.mosaic_model.objectives[i]) == gp.Var:
                one_solution.append(self.mosaic_model.objectives[i].x)
            else:
                one_solution.append(self.mosaic_model.objectives[i].getValue())
        # make sure the values of the objectives are rounded down to the nearest integer
        one_solution = [int(round(x, 0)) for x in one_solution]
        return one_solution

    def get_selected_images(self):
        pass

    def get_status(self):
        pass

    def set_minimization(self):
        pass

    def set_maximization(self):
        pass

    def set_time_limit(self, timeout):
        pass

    def reset(self):
        self.mosaic_model.model.reset(1)

    def status_time_limit(self):
        pass

    def __int__(self, instance, statistics, timer, threads, free_search=True):
        super().__init__(instance, statistics, timer, threads, free_search)
        self.model = gp.Model()
        self.elements, self.areas = gp.multidict({i: instance.areas[i] for i in range(len(instance.areas))})
        self.images_id, self.images, self.costs = gp.multidict({i: [instance.images[i], instance.costs[i]]
                                                                for i in range(len(instance.images))})
        # cloud processing
        self.cloud_covered_by_image = gp.tupledict(instance.cloud_covered_by_image)
        self.clouds_id, self.area_clouds = gp.multidict(instance.clouds_id_area)
        self.total_area_clouds = int(sum(self.area_clouds.values()))
        # resolution processing
        self.resolution = gp.tupledict(zip(self.images_id, instance.resolution))
        self.min_resolution = min(instance.resolution)
        # incidence angle processing
        self.incidence_angle = gp.tupledict(zip(self.images_id, instance.incidence_angle))
        # multiply to convert to integers
        # variables
        self.select_image = None
        self.cloud_covered = None
        self.resolution_element = None
        self.effective_image_resolution = None
        self.effective_incidence_angle = None
        self.current_max_incidence_angle = None
        self.add_variables()
        self.objectives = []
        self.add_objectives()
        self.constraint_objectives = [0] * len(self.objectives)

    def add_variables(self):
        # decision variables
        self.select_image = self.model.addVars(len(self.images), vtype=gp.GRB.BINARY, name="select_image_i")
        self.cloud_covered = self.model.addVars(self.clouds_id, vtype=gp.GRB.BINARY, name="cloud_covered_e")
        # support variables
        self.resolution_element = self.model.addVars(self.elements, lb=self.min_resolution, ub=max(self.resolution.values()), vtype=gp.GRB.INTEGER,
                                                     name="resolution_element_i")
        self.effective_image_resolution = self.model.addVars(len(self.images), vtype=gp.GRB.INTEGER,
                                                        name="effective_resolution_image_i")
        self.effective_incidence_angle = self.model.addVars(len(self.images), vtype=gp.GRB.INTEGER,
                                                       name="effective_incidence_angle_i")
        self.current_max_incidence_angle = self.model.addVar(vtype=gp.GRB.INTEGER,
                                                             name="max_allowed_incidence_angle")

    def add_objectives(self):
        # for cloud coverage
        self.objectives.append(self.total_area_clouds-(gp.quicksum(self.cloud_covered[c] * self.area_clouds[c]
                                                                   for c in self.clouds_id)))
        self.objectives_slack.append(-self.total_area_clouds)

        # for resolution
        self.objectives.append(gp.quicksum(self.resolution_element[e] for e in self.elements))
        self.objectives_slack.append(0)

        # for incidence angle
        self.objectives.append(self.current_max_incidence_angle)
        self.objectives_slack.append(0)

    def optimize_e_constraint_saugmecon(self, range_array):
        obj = self.get_main_objective()
        delta = 0.001 # delta should be between 0.001 and 0.000001
        rest_obj = 0
        for i in range(len(self.objectives)):
            rest_obj += self.objectives[i]/range_array[i]
        obj = obj + (delta * rest_obj)
        self.model.setObjective(obj)

    def get_main_objective(self):
        return gp.quicksum(self.select_image[i] * self.costs[i] for i in self.images_id)

    def add_basic_constraints(self):
        max_resolution = max(self.resolution.values())
        big_resolution = 2 * max_resolution
        # cover constraint
        self.model.addConstrs(gp.quicksum(self.select_image[i] for i in self.images_id if e in self.images[i]) >= 1
                              for e in self.elements)
        # cloud constraint
        self.model.addConstrs(gp.quicksum(self.select_image[i] for i in self.cloud_covered_by_image.keys()
                                          if c in self.cloud_covered_by_image[i]) >= self.cloud_covered[c]
                                            for c in self.clouds_id)
        self.model.addConstrs(gp.quicksum(self.select_image[i] for i in self.cloud_covered_by_image.keys()
                                          if c in self.cloud_covered_by_image[i]) <=
                              self.cloud_covered[c] * len(self.images) for c in self.clouds_id)

        # calculate resolution for each element
        self.model.addConstrs(((self.select_image[i] == 0) >> (self.effective_image_resolution[i] == big_resolution)
                               for i in self.images_id))
        self.model.addConstrs(((self.select_image[i] == 1) >> (self.effective_image_resolution[i] == self.resolution[i])
                               for i in self.images_id))
        self.model.addConstrs(self.resolution_element[e] == gp.min_(self.effective_image_resolution[i] for i in
                                                                    self.images_id if e in self.images[i])
                                                                    for e in self.elements)
        # incidence angle constraint
        # The below approach using indicator constraints is faster than the one commented below
        self.model.addConstrs(((self.select_image[i] == 0) >> (self.effective_incidence_angle[i] == 0)
                               for i in self.images_id))
        self.model.addConstrs(((self.select_image[i] == 1) >> (self.effective_incidence_angle[i] == self.incidence_angle[i])
                               for i in self.images_id))
        # Approach not using indicator constraints, it is slower than the one above
        # self.model.addConstrs(self.effective_incidence_angle[i] == self.select_image[i] * self.incidence_angle[i]
        #                       for i in self.images_id)
        self.model.addConstr(self.current_max_incidence_angle == max_(self.effective_incidence_angle[i]
                                                                      for i in self.images_id))
        # constraints end--------------------------------------------------------------

    def add_objective_constraints(self, ef_array):
        for i in range(len(self.objectives)):
            self.constraint_objectives[i] = self.model.addConstr(self.objectives[i] <= ef_array[i])

    def update_objective_constraints(self, ef_array):
        for constraint in self.constraint_objectives:
             self.model.remove(constraint)
        self.add_objective_constraints(ef_array)

    def solve(self, optimize_not_satisfy):
        if optimize_not_satisfy:
            self.model.optimize()
        else:
            # todo do satisfiability
            pass