from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import (ascii, bytes, chr, dict, filter, hex, input,
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)
import forgi.threedee.model.coarse_grain as ftmc
import fess.builder.models as fbm
import time
import forgi.threedee.model.stats as ftms

#This takes some time, which is why it is only executed once at startup of the server.
print(" * Loading default conformation stats")
default_conf_stats=ftms.get_conformation_stats()


class CgFileCache():
    def __init__(self):
        self.cached={}
        self.time={} 
        self.max_size=64
    def loadSM(self, filename):
        if filename not in self.cached:
            if len(self.cached)>self.max_size:
                self.cleanup()
            cg=ftmc.CoarseGrainRNA("user_files/"+filename)
            sm=fbm.SpatialModel(cg, conf_stats=default_conf_stats)
            self.cached[filename]=sm
            self.time[filename]=time.time()
        return self.cached[filename]
    def removeSM(self, filename): 
        """
        Remove a spatial model from the cache.    
        """
        del self.cached[filename]
        del self.time[filename]
    def renameSM(self, filename_old, filename_new):
        """
        If a spatial Model is modified, we usually want to assign a new name to it.
        The old name is deleted from the cache.
        """
        sm=self.cached[filename_old]
        del self.cached[filename_old]
        del self.time[filename_old]
        self.cached[filename_new]=sm
        self.time[filename_new]=time.time()
    def cleanup(self):
        todelete=sorted(self.time.keys(), key=lambda x: self.time[x])
        todelete=todelete[self.max_size:]
        for td in todelete:
            del self.cached[td]
            del self.time[td]
