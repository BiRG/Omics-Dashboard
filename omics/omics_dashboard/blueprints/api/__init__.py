from .api import api
from .analyses import analyses_api
from .collections import collections_api
from .external_files import external_files_api
from .jobs import jobs_api
from .sample_groups import sample_groups_api
from .samples import samples_api
from .user_groups import user_groups_api
from .users import users_api
from .workflows import workflows_api

api_blueprints = [
    api, analyses_api, collections_api, external_files_api, jobs_api, sample_groups_api, samples_api, user_groups_api,
    users_api, workflows_api
]
