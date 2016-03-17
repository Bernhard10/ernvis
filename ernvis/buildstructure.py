#! /usr/bin/python
import forgi.threedee.model.coarse_grain as ftmc
import fess.builder.models as fbm
import forgi.threedee.utilities.vector as ftuv
import forgi.threedee.utilities.graph_pdb as ftug

import sys
if __name__=="__main__":
    filename=sys.argv[1]    
    print ("BUILDSTRUCTURE: Filename is ", filename)
    cg=ftmc.CoarseGrainRNA(filename)
    print ("BUILDSTRUCTURE: cg is ", cg)
    sm=fbm.SpatialModel(cg)
    print ("BUILDSTRUCTURE: sampling ")
    sm.sample_stats()
    print ("BUILDSTRUCTURE: traverse and build ")
    sm.traverse_and_build()
    print("BUILDSTRUCTURE: Writing File")

    centroid0 = ftuv.get_vector_centroid(ftug.bg_virtual_residues(sm.bg))
    for k in cg.coords.keys():
        cg.coords[k] = ((cg.coords[k][0] - centroid0),
                        (cg.coords[k][1] - centroid0))

    sm.bg.to_cg_file(filename)
    print ("BUILDSTRUCTURE: DONE")
