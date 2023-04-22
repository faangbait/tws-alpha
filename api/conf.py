import logging, os, time, pathlib
from pprint import pp

class Config:
    VERSION = "0.0.1"
    ACCOUNT = "DU7002581"
    BASE_PATH = pathlib.Path(os.getcwd())

def set_logger(file_level=logging.ERROR, console_level=logging.WARN):
    os.makedirs("_logs", exist_ok=True)

    recfmt = '(%(threadName)s) %(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s'
    timefmt = '%y%m%d_%H:%M:%S'

    logger = logging.getLogger('tws-alpha')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(filename=time.strftime("_logs/tws.%Y%m%d_%H%M%S.log"))
    fh.setLevel(file_level)

    ch = logging.StreamHandler()
    ch.setLevel(console_level)

    fmtr = logging.Formatter(fmt=recfmt, datefmt=timefmt)

    fh.setFormatter(fmtr)
    ch.setFormatter(fmtr)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
