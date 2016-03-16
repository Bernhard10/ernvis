var scene = new THREE.Scene();
var camera = new THREE.PerspectiveCamera( 75, 1.0, 0.1, 1000 ); //FieldOfView, Aspect, near, far clipping
var renderer = new THREE.WebGLRenderer();
var controls;
var raycaster;
var mouse;
var rnaLoops=[];
var selectedLoop = null;

function showElem(data){
    typ=data["type"];
    length=data["length"];
    center=data["center"];
    look_at=data["look_at"];
    if (typ=="s"){
      r=3;
    }else{
      r=1;
    }
    if (typ=="s"){
      color=0x00ff00;
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

function init(){
  renderer.setSize( 500,500);
  renderer.setClearColor( 0xf0f0f0 );
  document.body.appendChild( renderer.domElement );

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
  loadRNA("/structure/test.coord/3D");

}

function loadRNA(url){    
  for (var i=0; i<rnaLoops.length; i++){
    //scene.remove( rnaLoops[i] );
    hsl=rnaLoops[i].material.color.getHSL();
    rnaLoops[i].material.color.setHSL(hsl.h, hsl.s/2, hsl.l*1.5);
    rnaLoops[i].material.transparent=true;
    rnaLoops[i].material.opacity=rnaLoops[i].material.opacity*0.2;
  }
  rnaLoops=[]
  $.getJSON(url, "", function(data){
    for (var i = 0; i < data["loops"].length; i++) {
        var stem=showElem(data["loops"][i]);
        scene.add(stem);
        rnaLoops.push(stem);
        camera.lookAt(stem);
        if (selectedLoop && stem.name==selectedLoop.name){
            console.log("picking")
            pickLoop(stem);
        }
    }
    render();
  });
  render();
}

function pickLoop(obje){
    selectedLoop=obje;
    selectedLoop.material.oldColor=selectedLoop.material.color.getHex();
    selectedLoop.material.color.addScalar(-0.4);
    selectedLoop.geometry.colorsNeedUpdate = true;
    $("#selectedLoop").load("/structure/test.coord/loop/"+selectedLoop.name+"/stats.html", function(){
        $("#changeElementButton").click(
            function(){
                loadRNA("/structure/test.coord/loop/"+selectedLoop.name+"/get_next")
            }
        )
    });
    render();
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
      selectedLoop.material.color.setHex(selectedLoop.material.oldColor)
    }
    //set new selected Loop    
    pickLoop(intersects[0].object);
  }
  
}

init();
render();
animate();
