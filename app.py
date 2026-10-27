from insurance_operations.job_api import create_job_app
from insurance_operations.settings import JobRunnerSettings

app = create_job_app(JobRunnerSettings())
