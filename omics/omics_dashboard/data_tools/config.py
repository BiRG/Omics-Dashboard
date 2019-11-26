import os


DATADIR: str = os.environ.get('DATADIR', '/var/omics_dashboard')
TMPDIR: str = os.environ.get('TMPDIR', '/tmp')
COMPUTESERVER: str = os.environ.get('COMPUTESERVER', 'http://jobserver:8000')
MODULEDIR: str = os.path.join(os.environ.get('MODULEDIR', os.path.join(DATADIR, 'modules')), 'cwl')
UPLOADDIR: str = f'{TMPDIR}/uploads'
OMICSSERVER: str = os.environ.get('OMICSSERVER', 'http://localhost/omics')
REDIS_URL: str = f'redis://{os.environ.get("REDISSERVER", "redis")}:{os.environ.get("REDISPORT", 6379)}/{os.environ.get("REDISDB", 0)}'
