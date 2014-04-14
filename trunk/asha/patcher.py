
from .parser import *
from ..general.patcher import *

class AshaPatcher(Patcher):
    def __init__(self, isVerbose=True):
        self.parser = ASHA()

    
