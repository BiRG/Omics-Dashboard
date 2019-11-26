from .browser import browser
from .analyses import analyses
from .collections import collections
from .external_files import external_files
from .jobs import jobs
from .sample_groups import sample_groups
from .samples import samples
from .user_groups import user_groups
from .users import users
from .workflows import workflows


browser_blueprints = [
    browser, analyses, collections, external_files, jobs, sample_groups, samples, user_groups, users, workflows
]
