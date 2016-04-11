var scene = new THREE.Scene();
var camera = new THREE.PerspectiveCamera( 75, 1.0, 0.1, 1000 ); //FieldOfView, Aspect, near, far clipping
var renderer = new THREE.WebGLRenderer();
var controls;
var raycaster;
var mouse;
var rnaLoops=[];
var virtualAtoms=[];
var selectedLoop = null;
var container;
window.onpopstate = function(){
  location.reload();
}

function showElem(data, bad_bulges){
    var typ=data["type"];
    var length=data["length"];
    var center=data["center"];
    var look_at=data["look_at"];
    var color;
    if (typ=="s"){
      r=3;
    }else{
      r=1;
    }
    if (typ=="s"){
      if ($.inArray(data["name"], bad_bulges)>-1){
          color=0x445500
      }else{
          color=0x00ff00;
      }
    }else if (typ=="i"){
      color=0xffff00;
    }else if (typ=="m"){
       color=0xff0000;
    }else if(typ=="h"){
      color=0x0000ff;
    }else{
      color=0xaaaaaa;
    }
    var geometry = new THREE.CylinderGeometry( r, r , length );
    var material = new THREE.MeshLambertMaterial( { color: color } );

    geometry.applyMatrix( new THREE.Matrix4().makeRotationX( THREE.Math.degToRad( 90 ) ) );
    var stem = new THREE.Mesh( geometry, material );
    stem.position.x=center[0];
    stem.position.y=center[1];
    stem.position.z=center[2];
    look_at=new THREE.Vector3(look_at[0], look_at[1], look_at[2]);
    stem.lookAt(look_at);
    stem.name=data["name"]
    return stem;
}

function showAtom(data){
    var is_clashing=data["is_clashing"];
    var center=data["center"];
    var color;
    if (is_clashing){
          color=0xffaa00;
    }else{
          color=0xaaffaa;
    }

    var geometry = new THREE.SphereGeometry( 0.7 );
    var material = new THREE.MeshLambertMaterial( { color: color } );
    var atom = new THREE.Mesh( geometry, material );
    atom.position.x=center[0];
    atom.position.y=center[1];
    atom.position.z=center[2];

    atom.stemname=data["loop"];
    atom.atomtype_name=data["atomname"]
    return atom;
}


function init(){
  renderer.setSize( 500,500);
  renderer.setClearColor( 0xf0f0f0 );
  $( renderer.domElement ).insertAfter("#canvasWrap h1");

  camera.position.z = 100;
  controls = new THREE.TrackballControls( camera, renderer.domElement );
  controls.rotateSpeed = 5.0;
  controls.zoomSpeed = 0.5;
  controls.panSpeed = 3.0;
  controls.noZoom = false;
  controls.noPan = false;
  controls.staticMoving = true;
  controls.dynamicDampingFactor = 0.3;

  //controls.keys = [ 65, 83, 68 ];
  controls.addEventListener( 'change', render );
  var directionalLight = new THREE.DirectionalLight( 0xffffff , 0.2);
  directionalLight.position.set( 0, 1, 0 );
  scene.add( directionalLight );
  var camlight = new THREE.PointLight( 0xffffff, 1, 0);
  camera.add(camlight);
  var light = new THREE.AmbientLight( 0x202020 ); // soft white light
  scene.add( light );
  scene.add( camera );

  raycaster = new THREE.Raycaster();
  mouse = new THREE.Vector2();

  renderer.domElement.addEventListener( 'click', selectLoop, false );

  // LOAD THE RNA
  loadRNA("3D");

}

function refreshCanvas(){
    for( var i = scene.children.length - 1; i >= 0; i--) { 
      object=scene.children[i];
      if(object.type === "Mesh"){
          scene.remove(object);
      }
    }
    rnaLoops=[];
    loadRNA("3D");
}

function loadRNA(url){
  //Make previous RNA transparent, but keep in the scene until "Refresh" is clicked.
  for (var i=0; i<rnaLoops.length; i++){
    //scene.remove( rnaLoops[i] );
    hsl=rnaLoops[i].material.color.getHSL();
    rnaLoops[i].material.color.setHSL(hsl.h, hsl.s/2, hsl.l*1.5);
    rnaLoops[i].material.transparent=true;
    rnaLoops[i].material.opacity=rnaLoops[i].material.opacity*0.2;
  }
  for (var i=0; i<virtualAtoms.length; i++){
      scene.remove(virtualAtoms[i]);
  }
  virtualAtoms=[]
  rnaLoops=[];
  //Load RNA to scene.
  $.getJSON(url, "", function(data){
    if (data["status"]=="OK"){
        $(".message").remove();
        //Load RNA stats
        $("#structureStats").load("stats", function(){
            $(".dotbracket_element").click(
                function(){
                    element=$(this).attr("element_name");
                    pickLoopByName(element);
                }
            );
        });
        // Fornac
        container = new fornac.FornaContainer("#rna_ss", {'applyForce': !$("#allowFornacEdit").is(':checked')});
        var options = {'structure': data["dotbracket"],
                        'sequence': data["sequence"]
        };
        container.addRNA(options.structure, options);
        $("#allowFornacEdit").change(function() {
            container.options.applyForce=!this.checked
            container.animate=!this.checked
            if (this.checked){
              container.stopAnimation();
            }else{
              container.startAnimation();
            }
        });
        //
        $("#energyInfo").load("energy");
        loadVirtualAtoms();
        for (var i = 0; i < data["loops"].length; i++) {
            var stem=showElem(data["loops"][i], data["bad_bulges"]);
            scene.add(stem);
            rnaLoops.push(stem);
            if (selectedLoop && stem.name==selectedLoop.name){
                pickLoop(stem);
            }
        }
        render();
    }else if (data["status"]=="NOT READY"){

        $( '<div class="message">'+data["message"]+'</div>' ).insertAfter("#canvasWrap h1");
        setTimeout(function(){loadRNA(url);}, 1000);
    }
  }).error( function(){$("body").load("404");}) 
  render();
}

function loadVirtualAtoms(){
  //Load VirtualAtoms (This call might keep the server busy for some time)
  if ($("#showVirtualAtoms").is(':checked')){
    $.getJSON("virtualAtoms", "", function(data){
        for (var i = 0; i < data["virtual_atoms"].length; i++) {
            atom=showAtom(data["virtual_atoms"][i]);
            scene.add(atom);
            virtualAtoms.push(atom);
        }
        render();
    });
  }
}
function pickObject(object){
    object.material.oldColor=object.material.color.getHex();
    object.material.color.addScalar(-0.4);
    object.geometry.colorsNeedUpdate = true;
}
function pickLoop(loop){
    selectedLoop=loop;
    pickObject(selectedLoop)
    for (var i=0; i<virtualAtoms.length; i++){            
        if (virtualAtoms[i].stemname==loop.name){

            pickObject(virtualAtoms[i]);
        }
    }
    $("#selectedLoop").load("loop/"+selectedLoop.name+"/stats.html", function(){
        $("#changeElementButton").click(
            function(){
                $.post("loop/"+selectedLoop.name+"/", JSON.stringify({"action":"change", "method":"random"}), function(data){
                    window.history.pushState("","", data.url);
                    loadRNA("3D")
                },"json");
            }
        )
    });
    $("."+selectedLoop.name).addClass("picked_string_"+selectedLoop.name.charAt(0))
    $("."+selectedLoop.name).addClass("picked_string")
    render();
}
function pickLoopByName(name){
  if (selectedLoop){
    //restore color of prev. selected loop
    unpickLoop(selectedLoop)
  }
  for (var i=0; i<rnaLoops.length; i++){
    if (rnaLoops[i].name==name){
      pickLoop(rnaLoops[i])
    }
  }
}

function unpickLoop(loop){
    $(".dotbracket_element").removeClass("picked_string")
    $(".dotbracket_element").removeClass("picked_string_m")
    $(".dotbracket_element").removeClass("picked_string_s")
    $(".dotbracket_element").removeClass("picked_string_h")
    $(".dotbracket_element").removeClass("picked_string_i")
    $(".dotbracket_element").removeClass("picked_string_f")
    $(".dotbracket_element").removeClass("picked_string_t")
    unpickObject(loop);
    for (var i=0; i<virtualAtoms.length; i++){
        if (virtualAtoms[i].stemname==loop.name){
            unpickObject(virtualAtoms[i]);
        }
    }
}
function unpickObject(object){
  object.material.color.setHex(object.material.oldColor)
}
function render() {
	renderer.render( scene, camera );
}
function animate() {
	requestAnimationFrame( animate );
	controls.update();

}

function selectLoop( event ){
  mouse.x = ( event.offsetX / renderer.domElement.clientWidth ) * 2 - 1;
  mouse.y = - ( event.offsetY / renderer.domElement.clientHeight ) * 2 + 1;
  raycaster.setFromCamera( mouse, camera );
  var intersects = raycaster.intersectObjects( rnaLoops, true );

  if ( intersects.length > 0 ) { 

    if (selectedLoop){
      //restore color of prev. selected loop
      unpickLoop(selectedLoop)

    }
    //set new selected Loop    
    pickLoop(intersects[0].object);
  }
  
}

init();
render();
animate();
