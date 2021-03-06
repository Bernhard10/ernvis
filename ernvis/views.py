from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import (ascii, bytes, chr, dict, filter, hex, input,
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)
from . import app
from . import caching

from flask import jsonify, render_template, request, abort, redirect, url_for

import forgi.threedee.model.coarse_grain as ftmc
import forgi.threedee.utilities.vector as ftuv
import fess.builder.models as fbm
import fess.builder.energy as fbe
import forgi.threedee.utilities.graph_pdb as ftug
import forgi.threedee.utilities.rmsd as ftur
import time, random, copy, uuid, os.path
import subprocess

import numpy as np

import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

from cProfile import Profile
from pstats import Stats
prof = Profile()
prof.disable()

smCache = caching.CgFileCache()

# ========== FILTERS FOR JINJA2 =========
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

@app.template_filter('energy_name')
def energy_name(shortname):
  s=shortname
  if s=="ROG":
    return "Radius of Gyration Energy (ROG)"
  elif s=="AME(0)":
    return "A-Minor Energy (hairpin)"
  elif s=="AME(1)":
    return "A-Minor Energy (interior loop)"
  elif s=="10SLD" or s.startswith("10SLD,"):
    return "Hairpin-hairpin Interaction (SLD)" 
  return s

@app.template_filter('markup_dotbracket')
def markup_dotbracket(cg):
  db=cg.to_dotbracket_string()
  c2l={}
  for key, positions in cg.defines.items():
      if len(positions)>1:
          c2l[positions[0]]=(key, positions[1])
      if len(positions)>3:
          c2l[positions[2]]=(key, positions[3])
  outdb=[]
  for start in sorted(c2l):
      outdb.append('<span class="{0} dotbracket_element" element_name="{0}">'.format(c2l[start][0])+db[start-1:c2l[start][1]]+'</span>')
  return "".join(outdb)
# ===========  ROOT  =======================
@app.route('/')
def index():
  return render_template("index.html")

# ===========  ROOT>STRUCTURES =============
@app.route('/structures', methods=["POST"])
def upload_structure():
    fasta=request.form["fasta"]
    cg = ftmc.CoarseGrainRNA()
    cg.from_fasta(fasta)
    filename=get_new_filename()
    cg.to_cg_file("user_files/"+filename)        
    subprocess.Popen(["ernvis/buildstructure.py", "user_files/"+filename])
    print("Subprocess started")
    return redirect(url_for("structure_main", filename=filename))

# ===========  ROOT>STRUCTURES>StructureID =============

@app.route('/structures/<string:filename>/')
def structure_main(filename):
  return render_template("structure.html")

@app.route('/structures/<string:filename>/404')
def show404(filename):
  return render_template("show404.html")

@app.route('/structures/<string:filename>/3D')
def showStructure(filename):
    sm=get_sm(filename)
    try:
        return getStructureJson(sm)
    except KeyError as e:
        log.exception(e)
        smCache.removeSM(filename)
        return jsonify({"status":"NOT READY", "message":"Please wait, while your structure is being built."})



@app.route('/structures/<string:filename>/loop/<string:loopname>/', methods=["POST"])
def changeLoop(filename, loopname):
    posted=request.get_json(force=True)
    if posted["action"]=="change" and posted["method"]=="random":
        sm=get_sm(filename)
        sm.load_sampled_elems()
        if loopname not in sm.bg.coords:
            abort(404)
        original_cg=copy.deepcopy(sm.bg)
        new_filename=get_new_filename()
        smCache.renameSM(filename, new_filename)
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

        filename=get_new_filename()
        cg.to_cg_file("user_files/"+filename)

        return jsonify({"url": url_for("structure_main", filename=filename)})
    else:
        abort(403)


@app.route('/structures/<string:filename>/loop/<string:loopname>/stats.html')
def loopInfo(filename, loopname):
    sm=get_sm(filename)
    cg=sm.bg
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

@app.route('/structures/<string:filename>/stats')
def structureStats(filename):
    sm=get_sm(filename)
    cg=sm.bg
    clash_energy=fbe.StemVirtualResClashEnergy()
    clash_energy.eval_energy(sm)
    numclashes=sum(len(clash_energy.bad_atoms[x]) for x in clash_energy.bad_atoms)
    junction_energy=fbe.RoughJunctionClosureEnergy()
    j=junction_energy.eval_energy(sm)
    print("J Energy is ",j)
    return render_template("structureinfo.html", cg=cg, numclashes=numclashes, 
                            clashbulges=", ".join(sorted(set(clash_energy.bad_bulges), key=lambda x: int(x[1:]))),
                            bad_junctions=", ".join(sorted(set(junction_energy.bad_bulges), key=lambda x: int(x[1:]))))

@app.route('/structures/<string:filename>/styles/fornac.css')
def fornacstyle(filename):
   return app.send_static_file('styles/fornac.css')

@app.route('/structures/<string:filename>/energy')
def structureEnergy(filename):
    sm=get_sm(filename)
    #posted=request.get_json(force=True)
    #if "energy" in posted:
    #    pass    
    sld_energies=[]
    for hloop in sm.bg.hloop_iterator():
        sld_energies+= [fbe.ShortestLoopDistancePerLoop(hloop)]
    combined_energy=fbe.CombinedEnergy([], [fbe.RadiusOfGyrationEnergy(), fbe.AMinorEnergy(loop_type = 'h'), fbe.AMinorEnergy(loop_type = 'i')]+[fbe.CombinedEnergy([], sld_energies)])

    return render_template("energy.html", energy=combined_energy, sm=sm)
# ======= VIEWS RETURNING JSON ===============



@app.route('/structures/<string:filename>/virtualAtoms')
def showvirtualAtoms(filename):
    sm=get_sm(filename)
    cg=sm.bg
    clash_energy=fbe.StemVirtualResClashEnergy()
    clash_energy.eval_energy(sm)
    forJson={ "virtual_atoms":[]}
    virtualAtoms = ftug.virtual_atoms(sm.bg, sidechain=True)
    for residuePos in virtualAtoms.keys():
        stem=cg.get_node_from_residue_num(residuePos)
        if stem[0]!="s": continue #Only virtual res for stems!
        residue=virtualAtoms[residuePos]
        for aname in residue.keys():
            isClashing=False
            if stem in clash_energy.bad_bulges:
                for clashing in clash_energy.bad_atoms[stem]:
                    if np.allclose(residue[aname], clashing):
                        isClashing=True
                        break;
            atomInfo={
                "atomname":aname,
                "center":residue[aname].tolist(),
                "is_clashing":isClashing,
                "loop": stem
            }
            forJson["virtual_atoms"].append(atomInfo)
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

def getStructureJson(sm):
    
    clash_energy=fbe.StemVirtualResClashEnergy()
    try:
        clash_energy.eval_energy(sm)
    except KeyError:
        sm.bg.add_all_virtual_residues()
        clash_energy.eval_energy(sm)
    forJson={ "loops":[], "bad_bulges":[], "status":"OK"}
    for element in sm.bg.coords:
        forJson["loops"].append(cylinderToThree(sm.bg.coords[element], element))

    if clash_energy.bad_bulges:
        forJson["bad_bulges"]=list(set(clash_energy.bad_bulges))

    forJson["dotbracket"]=sm.bg.to_dotbracket_string()
    forJson["sequence"]=sm.bg.seq
    return jsonify(forJson)

    
def get_new_filename():
    while True:
        filename=str(uuid.uuid4())
        if not os.path.exists("user_files/"+filename):
            return filename

def get_sm(filename):
    try:
        return smCache.loadSM(filename)
    except IOError:
        abort(404)
