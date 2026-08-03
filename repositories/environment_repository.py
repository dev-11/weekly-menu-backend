import os


class EnvironmentRepository:
    @staticmethod
    def get_parameter(parameter_name):
        return os.environ[parameter_name]
