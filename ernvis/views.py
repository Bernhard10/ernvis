from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import (ascii, bytes, chr, dict, filter, hex, input,
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)
from . import app

from flask import jsonify, render_template

import forgi.threedee.model.coarse_grain as ftmc
import forgi.threedee.utilities.vector as ftuv
import fess.builder.models as fbm
import forgi.threedee.utilities.graph_pdb as ftug
import forgi.threedee.utilities.rmsd as ftur
import time, random, copy

import numpy as np

from cProfile import Profile
from pstats import Stats
prof = Profile()
prof.disable()



@app.template_filter('looptype')
def looptype(loopname):
  l=loopname[0]
  if l=="h":
    return "hairpin loop"
  elif l=="s":
    return "stem"
  elif l=="i":
    return "interior loop"
  elif l=="m":
    return "multiloop" 
  elif l=="t":
    return "three prime single stranded region"
  elif l=="f":
    return "five prime single stranded region"
  return "???"


# ======= VIEWS RETURNING HTML ===============

@app.route('/')
def index():
  return render_template("index.html")

@app.route('/structure/<string:filename>/loop/<string:loopname>/stats.html')
def loopInfo(filename, loopname):
    cg=ftmc.CoarseGrainRNA(filename)
    #prof.enable()
    sm=fbm.SpatialModel(cg, fast=True)
    #prof.disable()
    #prof.dump_stats('mystats.stats')
    #stats = Stats('mystats.stats')
    #stats.sort_stats('cumulative', 'time')
    #stats.print_stats()
    sm.load_sampled_elems()
    if loopname in cg.coords:
        try:
            stats=sm.elem_defs[loopname]
        except KeyError:
            stats=None
        return render_template("loopinfo.html", name=loopname, stats=stats)
    else:
        abort(404)

# ======= VIEWS RETURNING JSON ===============

@app.route('/structure/<string:filename>/3D')
def showStructure(filename):
    cg=ftmc.CoarseGrainRNA(filename)
    forJson={ "loops":[]}
    for element in cg.coords:
        forJson["loops"].append(cylinderToThree(cg.coords[element], element))
    return jsonify(forJson)

# ======= VIEWS ALLOWING POST METHOD ==========
@app.route('/structure/<string:filename>/loop/<string:loopname>/get_next')
def changeLoop(filename, loopname):
    cg=ftmc.CoarseGrainRNA(filename)
    sm=fbm.SpatialModel(cg, fast=True)
    sm.load_sampled_elems()
    if loopname not in cg.coords:
        abort(404)
    original_cg=copy.deepcopy(sm.bg)

    change_elem(sm, loopname)
    cg=sm.bg

    centroid0 = ftuv.get_vector_centroid(ftug.bg_virtual_residues(original_cg))
    centroid1 = ftuv.get_vector_centroid(ftug.bg_virtual_residues(cg))
    crds0 = ftuv.center_on_centroid(ftug.bg_virtual_residues(original_cg))
    crds1 = ftuv.center_on_centroid(ftug.bg_virtual_residues(cg))
    rot_mat = ftur.optimal_superposition(crds0, crds1)
    for k in cg.coords.keys():
        cg.coords[k] = (np.dot(rot_mat, cg.coords[k][0] - centroid1),
                        np.dot(rot_mat, cg.coords[k][1] - centroid1))
        if k[0] == 's':
            cg.twists[k] = (np.dot(rot_mat, cg.twists[k][0]),
                            np.dot(rot_mat, cg.twists[k][1]))

    cg.to_cg_file(filename)
    forJson={ "loops":[]}
    for element in cg.coords:
        forJson["loops"].append(cylinderToThree(cg.coords[element], element))
    return jsonify(forJson)

# ======= HELPER FUNCTIONS ====================
def cylinderToThree(line, name):
    start, end=line
    length=ftuv.magnitude(end-start)
    look_at=end
    center=(start+end)/2
    return {"center":center.tolist(), "look_at":look_at.tolist(), "length":length, "type":name[0], "name":name}

def change_elem(sm, d):
    '''
    Change the given element.
    '''
    new_stat = random.choice(sm.conf_stats.sample_stats(sm.bg, d))
    print(new_stat)
    sm.elem_defs[d] = new_stat
    sm.traverse_and_build(start=d)

    

