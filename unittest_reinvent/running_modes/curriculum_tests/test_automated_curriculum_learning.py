import os
import shutil
import unittest

from running_modes.automated_curriculum_learning.automated_curriculum_runner import AutomatedCurriculumRunner
from reinvent_models.reinvent_core.models.model import Model
from running_modes.automated_curriculum_learning.logging import AutoCLLogger
from running_modes.configurations.automated_curriculum_learning.automated_curriculum_learning_configuration import \
    AutomatedCLConfiguration
from running_modes.configurations.automated_curriculum_learning.curriculum_strategy_configuration import CurriculumStrategyConfiguration
from running_modes.configurations.automated_curriculum_learning.curriculum_objective import CurriculumObjective
from running_modes.configurations.automated_curriculum_learning.production_strategy_configuration import ProductionStrategyConfiguration

from reinvent_scoring.scoring.component_parameters import ComponentParameters
from reinvent_scoring.scoring.diversity_filters.reinvent_core.diversity_filter_parameters import \
    DiversityFilterParameters
from reinvent_scoring.scoring.enums.diversity_filter_enum import DiversityFilterEnum
from reinvent_scoring.scoring.enums.scoring_function_component_enum import ScoringFunctionComponentNameEnum
from reinvent_scoring.scoring.enums.scoring_function_enum import ScoringFunctionNameEnum
from reinvent_scoring.scoring.scoring_function_parameters import ScoringFunctionParameters

from running_modes.configurations.general_configuration_envelope import GeneralConfigurationEnvelope
from running_modes.configurations.logging.reinforcement_log_configuration import ReinforcementLoggerConfiguration
from running_modes.configurations.reinforcement_learning.inception_configuration import InceptionConfiguration
from running_modes.enums.curriculum_type_enum import CurriculumTypeEnum
from running_modes.enums.curriculum_strategy_enum import CurriculumStrategyEnum
from running_modes.enums.production_strategy_enum import ProductionStrategyEnum
from running_modes.enums.logging_mode_enum import LoggingModeEnum
from running_modes.enums.running_mode_enum import RunningModeEnum
from running_modes.utils import set_default_device_cuda
from unittest_reinvent.fixtures.paths import MAIN_TEST_PATH, PRIOR_PATH
from unittest_reinvent.fixtures.test_data import ASPIRIN, CELECOXIB


class TestAutomatedCurriculumLearning(unittest.TestCase):

    def setUp(self):
        set_default_device_cuda()
        self.cs_enum = CurriculumStrategyEnum()
        self.ps_enum = ProductionStrategyEnum()
        self.lm_enum = LoggingModeEnum()
        self.run_mode_enum = RunningModeEnum()
        self.sf_enum = ScoringFunctionNameEnum()
        self.sf_component_enum = ScoringFunctionComponentNameEnum()
        self.filter_enum = DiversityFilterEnum()
        self.workfolder = MAIN_TEST_PATH
        self.logging_path = f"{self.workfolder}/log"
        smiles = [ASPIRIN, CELECOXIB]

        automated_cl_parameters, parameters = self._create_configuration(smiles)

        self.runner = AutomatedCurriculumRunner(automated_cl_parameters, AutoCLLogger(parameters),
                                                prior=Model.load_from_file(PRIOR_PATH),
                                                agent=Model.load_from_file(PRIOR_PATH))

    def tearDown(self):
        if os.path.isdir(self.workfolder):
            shutil.rmtree(self.workfolder)

    def _create_configuration(self, smiles):
        # Curriculum Phase Configuration
        curriculum_sf_parameters = vars(ComponentParameters(name="tanimoto similarity", weight=1,
                                                            specific_parameters={"smiles": smiles},
                                                            component_type=self.sf_component_enum.TANIMOTO_SIMILARITY))

        curriculum_objectives = [CurriculumObjective(ScoringFunctionParameters(name=self.sf_enum.CUSTOM_PRODUCT,
                                                                               parameters=[curriculum_sf_parameters]))]

        curriculum_df = DiversityFilterParameters(self.filter_enum.NO_FILTER, 0.05, 25, 0.4)
        curriculum_inception = InceptionConfiguration(smiles, 100, 10)

        curriculum_config = CurriculumStrategyConfiguration(name=self.cs_enum.USER_DEFINED,
                                                            curriculum_objectives=curriculum_objectives,
                                                            diversity_filter=curriculum_df,
                                                            inception=curriculum_inception, max_num_iterations=3)

        # Production Phase Configuration
        production_sf_parameters = vars(ComponentParameters(name="tanimoto similarity", weight=1,
                                                            specific_parameters={"smiles": smiles},
                                                            component_type=self.sf_component_enum.TANIMOTO_SIMILARITY))

        production_df = DiversityFilterParameters(self.filter_enum.IDENTICAL_MURCKO_SCAFFOLD, 0.05, 25, 0.4)
        production_inception = InceptionConfiguration(smiles, 100, 10)

        production_config = ProductionStrategyConfiguration(name=self.ps_enum.STANDARD,
                                                            scoring_function=
                                                            ScoringFunctionParameters(
                                                                name=self.sf_enum.CUSTOM_PRODUCT,
                                                                parameters=[production_sf_parameters]),
                                                            diversity_filter=production_df, inception=production_inception,
                                                            retain_inception=False, n_steps=3)

        automated_cl_parameters = AutomatedCLConfiguration(prior=PRIOR_PATH, agent=PRIOR_PATH,
                                                           curriculum_strategy=curriculum_config,
                                                           production_strategy=production_config,
                                                           curriculum_type=CurriculumTypeEnum.AUTOMATED)

        logging = ReinforcementLoggerConfiguration(recipient=self.lm_enum.LOCAL,
                                                   logging_path=self.logging_path, result_folder=self.workfolder,
                                                   logging_frequency=0, job_name="unit_test_job")

        parameters = GeneralConfigurationEnvelope(parameters=vars(automated_cl_parameters), logging=vars(logging),
                                                  run_type=self.run_mode_enum.CURRICULUM_LEARNING, version="3.0")

        return automated_cl_parameters, parameters

    def test_automated_curriculum_learning(self):
        self.runner.run()
        self.assertTrue(os.path.isdir(self.logging_path))
