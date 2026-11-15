/* Lifecore hologram - Three.js scene: BodyParts3D body + anatomical heart with cardiac motion.
 * Color follows the heart rate (gray < 60, blue, yellow 90-100, red from 114 bpm). Live mode polls receiver /estado.
 * Build: npm run build  (writes app/static/hologram/holo.js). Some inline comments are in Spanish. */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// ------------------------------------------------------------ configuración (por URL)
let CFG = { bpms: [72], estado: 'normal', etiqueta: 'AST-001', sub: '', fuente: '' };
try { const raw = new URLSearchParams(location.search).get('cfg'); if (raw) CFG = { ...CFG, ...JSON.parse(raw) }; } catch (e) { /* usa valores por defecto */ }
const VER = CFG.v || Date.now();
const COL_N = [58, 134, 224], COL_A = [224, 58, 30];          // cuerpo: azul institucional (rojo si hay alerta)
const ACC_N = [86, 164, 242], ACC_A = [224, 58, 30];             // detalles: azul (rojo si hay alerta)
const HEX_HEART = 0x56a4f2, HEX_BODY = 0x5aa3ec;
const CSS_HEART = COL_N.slice(), CSS_ACC = ACC_N.slice();
// color según los lpm: gris (<60) · azul (normal) · amarillo (90-100) · rojo desde 114 (pulso de pie de los astronautas NASA cercanos al desmayo al aterrizar)
const ZONAS = [  // [lpm, cuerpo, detalle]
  [50, [170, 182, 200], [196, 206, 222]], [58, [170, 182, 200], [196, 206, 222]],
  [64, [58, 134, 224], [86, 164, 242]], [78, [58, 134, 224], [86, 164, 242]],
  [88, [236, 172, 0], [246, 196, 50]], [100, [236, 172, 0], [246, 196, 50]],
  [114, [224, 58, 30], [224, 58, 30]]
];
function colorPorLpm(b) {
  const Z = ZONAS; if (b <= Z[0][0]) return [Z[0][1], Z[0][2], 0];
  for (let i = 1; i < Z.length; i++) if (b <= Z[i][0]) {
    const t = (b - Z[i - 1][0]) / (Z[i][0] - Z[i - 1][0]);
    const mix = (p, q) => p.map((v, j) => Math.round(v + (q[j] - v) * t));
    return [mix(Z[i - 1][1], Z[i][1]), mix(Z[i - 1][2], Z[i][2]), i === Z.length - 1 ? t : 0];
  }
  const L = Z[Z.length - 1]; return [L[1], L[2], 1];
}
const nombreZona = (b) => b < 60 ? 'BAJO' : b < 80 ? 'NORMAL' : b < 100 ? 'SUBIENDO' : b < 114 ? 'ALTO' : 'MUY ALTO';

const accCol = new THREE.Color(0x1f6fd1);           // se mezcla con el color de alerta según el estado
let stateK = CFG.estado === 'alerta' ? 1 : 0, stateTarget = stateK;
const lerp = (a, b, t) => a + (b - a) * t;
const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

// ------------------------------------------------------------ escena
const root = document.getElementById('root');
const glCanvas = document.getElementById('gl'), hud = document.getElementById('hud'), hctx = hud.getContext('2d');
const loadEl = document.getElementById('load'), backBtn = document.getElementById('back');
const renderer = new THREE.WebGLRenderer({ canvas: glCanvas, antialias: true, alpha: true });
renderer.setClearColor(0x000000, 0);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.15;
const gl = renderer.getContext();
const dbg = gl.getExtension('WEBGL_debug_renderer_info');
const SOFTWARE = /swiftshader|llvmpipe|software|basic render/i.test(String(dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)));
const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.55;
const camera = new THREE.PerspectiveCamera(35, 1, 0.02, 20);
let W = 1, H = 1, DPR = 1;
function resize() {
  const r = root.getBoundingClientRect(); W = Math.max(50, r.width); H = Math.max(50, r.height);
  DPR = Math.min(2, window.devicePixelRatio || 1);
  renderer.setPixelRatio(DPR); renderer.setSize(W, H, false);
  hud.width = Math.round(W * DPR); hud.height = Math.round(H * DPR); hctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  camera.aspect = W / H; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(root); resize();

scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const key = new THREE.DirectionalLight(0xfff0e8, 2.2); key.position.set(1.4, 2.2, 3); scene.add(key);
const rimL = new THREE.DirectionalLight(HEX_HEART, 1.0); rimL.position.set(-2, 1, -2); scene.add(rimL);
const fillL = new THREE.DirectionalLight(0x9fb8ff, 0.5); fillL.position.set(-2, -0.5, 2); scene.add(fillL);

const uniforms = { uTime: { value: 0 }, uFade: { value: 1 } };
function holoMat(color, base, rimA, lines, side = THREE.FrontSide, power = 2.2) {
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uAcc: { value: accCol }, uColor: { value: new THREE.Color(color) }, uBase: { value: base }, uRim: { value: rimA }, uLines: { value: lines }, uPow: { value: power } },
    vertexShader: `varying vec3 vN; varying vec3 vV; varying vec3 vW;
      void main(){ vec4 mv=modelViewMatrix*vec4(position,1.0); vN=normalize(normalMatrix*normal); vV=-mv.xyz; vW=(modelMatrix*vec4(position,1.0)).xyz; gl_Position=projectionMatrix*mv; }`,
    fragmentShader: `uniform vec3 uColor, uAcc; uniform float uFade,uTime,uBase,uRim,uLines,uPow; varying vec3 vN; varying vec3 vV; varying vec3 vW;
      void main(){ float f=pow(1.0-abs(dot(normalize(vN),normalize(vV))),uPow);
        float ln=smoothstep(0.90,1.0,abs(sin(vW.y*95.0)));
        float band=mod(uTime*0.42,2.4)-0.3; float sc=exp(-pow((vW.y-band)*16.0,2.0));
        float a=clamp((uBase+uRim*f+uLines*ln+0.22*sc)*uFade,0.0,0.95);
        gl_FragColor=vec4(mix(uColor*(0.85+0.25*f), uAcc, clamp(0.55*ln*step(0.001,uLines)+0.9*sc+0.25*f,0.0,1.0)),a); }`,
    transparent: true, blending: THREE.NormalBlending, depthWrite: false, side
  });
}

// ------------------------------------------------------------ material de tejido (corazón)
const beatU = { value: 0 };
// movimiento cardiaco: tiempo desde el último latido y geometría de referencia (se calcula al cargar)
const heartU = { uTms: { value: 5000 }, uTs: { value: 1 }, uCV: { value: new THREE.Vector3() }, uAxis: { value: new THREE.Vector3(0, -1, 0) }, uCA: { value: new THREE.Vector3() } };
const sm = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const envAtria = t => Math.exp(-Math.pow((t - 25) / 38, 2));
const envVent = t => sm(50, 190, t) * (1 - sm(235, 430, t));
function tissueMat(look, kind = 0) {
  const m = new THREE.MeshPhysicalMaterial({
    color: look.color, roughness: look.rough ?? 0.5, metalness: 0,
    clearcoat: SOFTWARE ? 0 : (look.coat ?? 0.5), clearcoatRoughness: look.coatRough ?? 0.28,
    sheen: SOFTWARE ? 0 : (look.sheen ?? 0.3), sheenColor: new THREE.Color(look.sheenColor ?? '#a86a60'), sheenRoughness: 0.6, side: THREE.DoubleSide
  });
  m.defines = { USE_TISSUE: '' }; 
  const u = { uAO: { value: look.ao ?? 0.85 }, uMottle: { value: look.mottle ?? 0.25 }, uMottleTint: { value: new THREE.Color(look.mottleTint ?? '#6e2a25') },
    uFat: { value: look.fat ?? 0 }, uFatColor: { value: new THREE.Color(look.fatColor ?? '#e2c272') }, uRim: { value: look.rim ?? 0.25 }, uRimColor: { value: new THREE.Color(look.rimColor ?? '#ff6a55') }, uBeat: beatU, uAlert: { value: 0 }, uKind: { value: kind }, ...heartU };
  m.userData.u = u;
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, u);
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute vec4 _tissue;\nvarying vec4 vTissue;\nuniform float uTms,uTs,uKind; uniform vec3 uCV,uAxis,uCA;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vTissue = _tissue;
        {
          float t = uTms / uTs;
          float atr = exp(-pow((t - 25.0) / 38.0, 2.0));
          float sv = smoothstep(50.0, 190.0, t) * (1.0 - smoothstep(235.0, 430.0, t));
          vec3 p = transformed;
          if (uKind < 0.5) {                                   // ventrículos (y vasos que viajan sobre ellos): contracción + torsión + acortamiento
            vec3 d = p - uCV; float al = dot(d, uAxis); vec3 rad = d - al * uAxis;
            float tw = 0.17 * sv * clamp(al / 0.05, -1.0, 1.0);
            p += -rad * 0.075 * sv - uAxis * al * 0.05 * sv + cross(uAxis, rad) * tw;
          } else if (uKind < 1.5) {                            // aurículas: contracción previa a la sístole ventricular
            p += -(p - uCA) * 0.085 * atr;
          } else if (uKind < 2.5) {                            // grandes arterias: onda de presión que se propaga
            float dly = length(p - uCV) * 650.0;
            float w = exp(-pow((t - dly - 210.0) / 80.0, 2.0));
            p += normal * 0.0022 * w;
          } else {                                             // venas: leve pulso por la contracción auricular
            p += normal * 0.001 * atr;
          }
          transformed = p;
        }`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uAO,uMottle,uFat,uRim,uBeat,uAlert; uniform vec3 uMottleTint,uFatColor,uRimColor;\nvarying vec4 vTissue;')
      .replace('#include <color_fragment>', `#include <color_fragment>
        float fatM = clamp(vTissue.b * uFat, 0.0, 1.0);
        float ao = mix(1.0, vTissue.r, uAO * (1.0 - 0.75 * fatM));
        diffuseColor.rgb = mix(diffuseColor.rgb, uFatColor, fatM);
        diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * uMottleTint, (1.0 - vTissue.g) * uMottle);
        diffuseColor.rgb *= ao;`)
      .replace('#include <aomap_fragment>', `#include <aomap_fragment>
        reflectedLight.indirectDiffuse *= ao; reflectedLight.indirectSpecular *= ao * ao;`)
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
        float facing = abs(dot(normal, normalize(vViewPosition)));
        totalEmissiveRadiance += uRimColor * (uRim + 0.55 * uBeat) * pow(1.0 - facing, 2.5) * ao * diffuseColor.rgb;
        totalEmissiveRadiance += diffuseColor.rgb * 0.22 * uBeat;
        totalEmissiveRadiance += vec3(1.0, 0.12, 0.2) * uAlert * (0.12 + 0.5 * uBeat) * (0.35 + pow(1.0 - facing, 1.6));`);
  };
  m.customProgramCacheKey = () => 'tissue-astra';
  return m;
}
const LOOK = {
  wall: { color: '#c8645a', rough: 0.5, coat: 0.5, sheen: 0.35, rim: 0.3, mottle: 0.32, mottleTint: '#a0504a', fat: 0.95, fatColor: '#e4c577' },
  artery: { color: '#e07a70', rough: 0.45, coat: 0.45, rim: 0.12, ao: 0.75, mottle: 0.15, mottleTint: '#b67d72' },
  vein: { color: '#8a62b8', rough: 0.38, coat: 0.7, sheenColor: '#c48ba0', rim: 0.24, rimColor: '#b0506e', ao: 0.75, mottle: 0.12, mottleTint: '#6a3a70' },
  coronary: { color: '#e8504a', rough: 0.32, coat: 0.8, coatRough: 0.15, rim: 0.3, ao: 0.6, mottle: 0.1 },
  cvein: { color: '#9a5a90', rough: 0.32, coat: 0.8, coatRough: 0.15, rim: 0.28, rimColor: '#a8506e', ao: 0.6, mottle: 0.1 }
};
const NODE_LOOK = (n) => {
  if (/wall$/.test(n)) return 'wall';
  if (/coronary-artery|descending-artery|circumflex/.test(n)) return 'coronary';
  if (/cardiac-vein|coronary-sinus/.test(n)) return 'cvein';
  if (/vena-cava|pulmonary-vein/.test(n)) return 'vein';
  if (/aorta|aortic-arch|pulmonary-trunk|pulmonary-artery/.test(n)) return 'artery';
  return null;                    // cámaras, válvulas y músculos papilares: ocultos dentro de la pared
};

// ------------------------------------------------------------ grupos y carga
const HEART_ORIGIN = new THREE.Vector3(0.0214, 1.305, 0.0234);
const heartG = new THREE.Group(); heartG.position.copy(HEART_ORIGIN);
const pulse = new THREE.Group(); heartG.add(pulse); scene.add(heartG);
const bodyGroup = new THREE.Group(); scene.add(bodyGroup);
let skinMat = null; const ringMats = [];
const heartMeshes = [], tissueMats = [], heartNodes = {};
let built = false, bodyBox = new THREE.Box3(new THREE.Vector3(-0.5, 0, -0.2), new THREE.Vector3(0.5, 1.75, 0.2));

const BODY_STYLE = {
  skin: [HEX_BODY, 0.07, 0.8, 0.14, THREE.DoubleSide, 2.0, 5],
  skeleton: [0x9fbfe6, 0.14, 0.6, 0, THREE.FrontSide, 1.6, 2],
  airways: [0x5ab8f0, 0.55, 1.0, 0, THREE.FrontSide, 1.4, 3],
  pulmonary_vessels: [0xa595ee, 0.35, 0.9, 0, THREE.FrontSide, 1.5, 3],
  arteries: [0xf0644a, 0.55, 1.0, 0, THREE.FrontSide, 1.3, 3],
  veins: [0x4a98ee, 0.50, 1.0, 0, THREE.FrontSide, 1.3, 3],
  organs: [0x4cc9a0, 0.14, 0.5, 0, THREE.FrontSide, 1.8, 2],
  brain: [0xb59cf0, 0.25, 0.7, 0, THREE.FrontSide, 1.6, 2]
};

async function load() {
  const [man, buf, gltf] = await Promise.all([
    fetch('body.json?v='+VER,{cache:'no-store'}).then(r => r.json()),
    fetch('body.bin?v='+VER,{cache:'no-store'}).then(r => r.arrayBuffer()),
    new GLTFLoader().loadAsync('heart.glb?v='+VER)
  ]);
  for (const [name, G] of Object.entries(man.groups)) {
    const st = BODY_STYLE[name]; if (!st) continue;
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(buf, G.positions, G.vertices * 3), 3));
    geom.setAttribute('normal', new THREE.BufferAttribute(new Int16Array(buf, G.normals, G.vertices * 3), 3, true));
    geom.setIndex(new THREE.BufferAttribute(new Uint32Array(buf, G.index, G.indices), 1));
    geom.computeBoundingBox(); geom.computeBoundingSphere();
    const mesh = new THREE.Mesh(geom, holoMat(...st.slice(0, 6))); mesh.renderOrder = st[6]; mesh.frustumCulled = false; bodyGroup.add(mesh);
    if (name === 'skin') { bodyBox = geom.boundingBox.clone(); skinMat = mesh.material; }
  }
  // corazón anatómico
  const kindOf = (n) => /ventricular-wall|coronary|descending-artery|circumflex|cardiac-vein/.test(n) ? 0 : /atrium-wall/.test(n) ? 1 : /aorta|aortic-arch|pulmonary-trunk|pulmonary-artery/.test(n) ? 2 : 3;
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return;
    const lk = NODE_LOOK(o.name); heartNodes[o.name] = o;
    if (!lk) { o.visible = false; return; }
    const mt = tissueMat(LOOK[lk], kindOf(o.name)); tissueMats.push(mt); o.material = mt; o.renderOrder = 0; heartMeshes.push(o);
  });
  pulse.add(gltf.scene);
}

// ------------------------------------------------------------ cámara y controles
const BODY_VIEW = { tx: 0, ty: 0.9, tz: 0, yaw: 0, pitch: 0.08, dist: 3.1 };
const cam = { ...BODY_VIEW }, goal = { ...BODY_VIEW };
let focused = false, fade = 1, lastInteract = -1e9, ptr = null, hover = false, ptrXY = null;
const HEART_CENTER = HEART_ORIGIN.clone().add(new THREE.Vector3(0.006, 0.0, 0.0));
function setFocus(v) {
  focused = v;
  if (v) { Object.assign(goal, { tx: HEART_CENTER.x, ty: HEART_CENTER.y + 0.012, tz: HEART_CENTER.z, yaw: 0, pitch: 0.04, dist: 0.46 }); backBtn.style.display = 'block'; }
  else { Object.assign(goal, BODY_VIEW); backBtn.style.display = 'none'; }
}
backBtn.addEventListener('click', e => { e.stopPropagation(); setFocus(false); });
window.addEventListener('keydown', e => { if (e.key === 'Escape') setFocus(false); });
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
function hitHeart(x, y) {
  if (!heartMeshes.length) return false;
  const r = glCanvas.getBoundingClientRect();
  ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
  heartG.updateMatrixWorld(true);
  ray.setFromCamera(ndc, camera);
  if (ray.intersectObjects(heartMeshes, false).length) return true;
  if (!focused) {
    const p = HEART_CENTER.clone().project(camera);
    const sx = (p.x * 0.5 + 0.5) * r.width + r.left, sy = (-p.y * 0.5 + 0.5) * r.height + r.top;
    return Math.hypot(x - sx, y - sy) < 26;
  }
  return false;
}
glCanvas.addEventListener('pointerdown', e => { ptr = { x: e.clientX, y: e.clientY, t: performance.now(), moved: false, lx: e.clientX, ly: e.clientY }; glCanvas.setPointerCapture(e.pointerId); lastInteract = performance.now(); });
glCanvas.addEventListener('pointermove', e => {
  ptrXY = [e.clientX, e.clientY];
  if (ptr) {
    const dx = e.clientX - ptr.lx, dy = e.clientY - ptr.ly; ptr.lx = e.clientX; ptr.ly = e.clientY;
    if (Math.hypot(e.clientX - ptr.x, e.clientY - ptr.y) > 5) ptr.moved = true;
    if (ptr.moved) { goal.yaw -= dx * 0.007; goal.pitch = clamp(goal.pitch + dy * 0.004, -0.5, 1.0); cam.yaw = goal.yaw; cam.pitch = goal.pitch; lastInteract = performance.now(); }
  }
});
glCanvas.addEventListener('pointerup', e => {
  if (ptr && !ptr.moved && performance.now() - ptr.t < 600) {
    const hit = hitHeart(e.clientX, e.clientY);
    if (hit && !focused) setFocus(true); else if (!hit && focused) setFocus(false);
  }
  ptr = null;
});
glCanvas.addEventListener('wheel', e => {
  e.preventDefault(); lastInteract = performance.now();
  const lo = focused ? 0.2 : 1.2, hi = focused ? 0.9 : 4.5;
  goal.dist = clamp(goal.dist * (1 + Math.sign(e.deltaY) * 0.08), lo, hi);
}, { passive: false });

// ------------------------------------------------------------ latidos y HUD
const BPMS = CFG.bpms && CFG.bpms.length ? CFG.bpms : [72];
let idx = 0, bpmShown = BPMS[0], bpmColor = BPMS[0];
let lastBeat = performance.now() - 60000 / bpmShown, nextBeat = performance.now() + 300;
const g = (t, m, s) => { const d = (t - m) / s; return Math.exp(-0.5 * d * d); };
const wave = t => 0.14 * g(t, -150, 28) - 0.16 * g(t, -22, 8) + 1.0 * g(t, 0, 9) - 0.28 * g(t, 22, 9) + 0.30 * g(t, 190, 40);
function tick(now) {
  if (LIVE && liveOn) { nextBeat = now + 1e9; return; }   // en vivo: manda el sensor
  if (LIVE) { nextBeat = now + 1e9; lastBeat = Math.min(lastBeat, now - 1e7); return; }   // sin señal: no inventa latidos
  if (nextBeat > now + 5000) nextBeat = now + 300;
  while (now >= nextBeat) {
    lastBeat = nextBeat; let b = BPMS[idx % BPMS.length]; idx++;
    bpmShown = b;
    const bt = BPMS.length === 1 ? b + (Math.random() - 0.5) * 3 : b;   // leve variación entre latidos, el número mostrado no cambia
    nextBeat = lastBeat + 60000 / clamp(bt, 30, 200);
  }
}
const hist = []; const WIN = 5200;
// ---- sensor en vivo (receptor.py): cada latido recibido hace latir el corazón
const LIVE = CFG.live || null;                 // URL base del receptor, p. ej. http://localhost:8000
let liveOn = false, liveSeq = -1, liveBpm = null, liveBase = null;
const CALIB_N = 20;
const fuenteTxt = () => LIVE ? (liveOn ? 'SENSOR EN VIVO · WiFi' : 'SIN SEÑAL DEL SENSOR · esperando') : CFG.fuente;
function mediana(a) { const s = a.slice().sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; }
async function poll() {
  try {
    const r = await fetch(LIVE + '/estado', { cache: 'no-store' }); const d = await r.json();
    const fresco = d.edad_s != null && d.edad_s < 4 && d.bpm;
    if (fresco && d.seq !== liveSeq) {
      liveSeq = d.seq;
      if (d.calidad === 'ok') { lastBeat = performance.now(); bpmShown = d.bpm; liveBpm = d.bpm; }
    }
    liveOn = !!fresco;
    if (!liveOn) { liveBase = null; stateTarget = 0; }         // sin señal: vuelve a normal y se recalibra al volver
    if (liveOn && d.recientes) {
      if (!liveBase && d.recientes.length >= CALIB_N) {        // línea base propia: primeros latidos válidos
        const r = d.recientes.slice(-CALIB_N), med = mediana(r);
        const mad = mediana(r.map(x => Math.abs(x - med)));
        liveBase = { med, escala: Math.max(1.4826 * mad, 0.08 * med), umbral: (CFG.base && CFG.base.umbral) || 2.5 };
      }
      if (liveBase && d.recientes.length >= 3) {
        const z = (mediana(d.recientes.slice(-12)) - liveBase.med) / liveBase.escala;
        stateTarget = Math.abs(z) >= liveBase.umbral ? 1 : 0;
      } else stateTarget = 0;
    }
  } catch (e) { liveOn = false; }
}
if (LIVE) { setInterval(poll, 200); }

// etiquetas: [texto, estructura, dirección del punto más extremo]
const LABEL_DEFS = [
  ['Aorta', 'aortic-arch', [0.2, 1, -0.1]], ['Arteria pulmonar', 'pulmonary-trunk', [0.4, 1, 0.5]], ['Vena cava superior', 'superior-vena-cava', [-0.3, 1, 0.3]],
  ['Aurícula derecha', 'right-atrium-wall', [-1, 0.2, 0.5]], ['Aurícula izquierda', 'left-atrium-wall', [1, 1, 0.1]],
  ['Ventrículo derecho', 'ventricular-wall', [-0.6, -0.1, 1]], ['Ventrículo izquierdo', 'ventricular-wall', [1, -0.4, 0.3]],
  ['Arteria coronaria izq. (DA)', 'left-anterior-descending-artery', [0.6, -0.4, 1]], ['Arteria coronaria derecha', 'right-coronary-artery', [-1, -0.1, 0.8]]
];
let LABELS = [];
function setupMotion() {
  const vw = heartNodes['ventricular-wall'], ra = heartNodes['right-atrium-wall'], la = heartNodes['left-atrium-wall'];
  if (!vw) return;
  const mean = (ms) => { const c = new THREE.Vector3(), v = new THREE.Vector3(); let n = 0; for (const m of ms) { if (!m) continue; const p = m.geometry.getAttribute('position'); for (let i = 0; i < p.count; i += 3) { c.add(v.fromBufferAttribute(p, i)); n++; } } return c.multiplyScalar(1 / Math.max(n, 1)); };
  const cV = mean([vw]), cA = mean([ra, la]);
  const dir = new THREE.Vector3(0.5, -0.85, 0.3).normalize(), p = vw.geometry.getAttribute('position'), v = new THREE.Vector3();
  let best = -1e9, apex = new THREE.Vector3(); for (let i = 0; i < p.count; i += 2) { v.fromBufferAttribute(p, i); const s = v.dot(dir); if (s > best) { best = s; apex.copy(v); } }
  heartU.uCV.value.copy(cV); heartU.uCA.value.copy(cA); heartU.uAxis.value.copy(apex.sub(cA)).normalize();
}
function computeLabels() {
  const out = [];
  for (const [t, node, dir] of LABEL_DEFS) {
    const m = heartNodes[node]; if (!m) continue;
    const d = new THREE.Vector3(...dir).normalize(), pos = m.geometry.getAttribute('position');
    let best = -1e9, bp = new THREE.Vector3(), v = new THREE.Vector3();
    for (let i = 0; i < pos.count; i += 2) { v.fromBufferAttribute(pos, i); const s = v.dot(d); if (s > best) { best = s; bp.copy(v); } }
    out.push([t, bp]);
  }
  LABELS = out;
}
const v3 = new THREE.Vector3();
function toScreenW(p) { v3.copy(p).project(camera); return [(v3.x * 0.5 + 0.5) * W, (-v3.y * 0.5 + 0.5) * H]; }

function drawHUD(now, env, focusAmt) {
  const c = hctx; c.clearRect(0, 0, W, H);
  const m = Math.max(12, W * 0.025);
  c.textBaseline = 'top'; c.textAlign = 'left';
  c.fillStyle = rgba(CSS_HEART, 0.95); c.font = `600 ${Math.max(13, W * 0.022)}px 'Chakra Petch',sans-serif`; c.fillText(CFG.etiqueta, m, m);
  c.fillStyle = 'rgba(40,70,115,.6)'; c.font = `${Math.max(10, W * 0.016)}px 'Chakra Petch',sans-serif`; c.fillText(CFG.sub, m, m + Math.max(17, W * 0.03));
  c.textAlign = 'right'; c.fillStyle = rgba(CSS_HEART, 0.95); c.font = `600 ${Math.max(11, W * 0.018)}px 'Chakra Petch',sans-serif`;
  c.fillText(LIVE && !liveOn ? 'SIN SEÑAL' : nombreZona(bpmShown), W - m, m);
  c.fillStyle = 'rgba(40,70,115,.6)'; c.font = `${Math.max(10, W * 0.016)}px 'Chakra Petch',sans-serif`; c.fillText(fuenteTxt(), W - m, m + Math.max(17, W * 0.03));
  c.textAlign = 'left'; c.textBaseline = 'alphabetic';
  const big = clamp(W * 0.11, 34, 80), by = m + Math.max(17, W * 0.03) + 24 + big;
  c.save(); c.shadowColor = rgba(CSS_ACC, 0.35); c.shadowBlur = 4 + 8 * env;
  c.fillStyle = '#0B1F3A'; c.font = `700 ${big}px 'Chakra Petch',sans-serif`; c.fillText((LIVE && !liveOn ? '--' : String(Math.round(bpmShown))), m, by); c.restore();
  c.fillStyle = rgba(CSS_HEART, 0.9); c.font = `600 ${Math.max(12, big * 0.28)}px 'Chakra Petch',sans-serif`; c.fillText('lpm', m + 2, by + big * 0.32);
  const v = wave(now - lastBeat) + wave(now - nextBeat); hist.push([now, v]);
  while (hist.length && now - hist[0][0] > WIN) hist.shift();
  const ex0 = W * 0.42, ex1 = W * 0.95, ey = H * 0.925, ea = H * 0.055;
  c.strokeStyle = rgba(CSS_ACC, 0.3); c.lineWidth = 1; c.beginPath(); c.moveTo(ex0, ey); c.lineTo(ex1, ey); c.stroke();
  c.lineJoin = 'round';
  for (const [lw, al] of [[6, 0.12], [2.0, 0.95]]) {
    c.strokeStyle = lw > 3 ? rgba(CSS_ACC, 0.35) : rgba(CSS_HEART, al); c.lineWidth = lw; c.beginPath();
    for (let i = 0; i < hist.length; i++) { const x = ex1 - (now - hist[i][0]) / WIN * (ex1 - ex0), y = ey - hist[i][1] * ea; if (i === 0) c.moveTo(x, y); else c.lineTo(x, y); }
    c.stroke();
  }
  c.fillStyle = 'rgba(40,70,115,.5)'; c.font = `${Math.max(9, W * 0.0135)}px 'Chakra Petch',sans-serif`; c.textAlign = 'right';
  c.fillText('ECG ilustrativo · BodyParts3D (CC BY 4.0, DBCLS)', ex1, H - 8);
  const [hx, hy] = toScreenW(HEART_CENTER);
  const a0 = 1 - focusAmt;
  if (a0 > 0.02) {
    const pr = clamp((now - lastBeat) / 700, 0, 1);
    c.strokeStyle = rgba(CSS_ACC, 0.95 * a0); c.lineWidth = 1.6; c.beginPath(); c.arc(hx, hy, 15 + 5 * env, 0, 6.283); c.stroke();
    c.strokeStyle = rgba(CSS_ACC, 0.6 * (1 - pr) * a0); c.beginPath(); c.arc(hx, hy, 15 + pr * 26, 0, 6.283); c.stroke();
    const lx = hx + 62, ly = hy - 42;
    c.strokeStyle = rgba(CSS_ACC, 0.85 * a0); c.lineWidth = 1; c.beginPath(); c.moveTo(hx + 11, hy - 11); c.lineTo(lx, ly); c.lineTo(lx + 108, ly); c.stroke();
    c.textAlign = 'left'; c.textBaseline = 'bottom'; c.fillStyle = `rgba(11,31,58,${0.95 * a0})`; c.font = `600 ${Math.max(12, W * 0.02)}px 'Chakra Petch',sans-serif`; c.fillText('Corazón', lx + 2, ly - 3);
    c.fillStyle = `rgba(40,70,115,${0.75 * a0})`; c.font = `${Math.max(10, W * 0.0155)}px 'Chakra Petch',sans-serif`; c.fillText(hover ? 'clic para enfocar' : 'haz clic para enfocar', lx + 2, ly + 17);
  }
  if (focusAmt > 0.55 && LABELS.length) {
    const al = clamp((focusAmt - 0.55) / 0.35, 0, 1);
    const [cx0] = toScreenW(HEART_CENTER);
    const rad = (0.075 / (2 * cam.dist * Math.tan(0.30543))) * H;
    const items = LABELS.map(([t, p]) => { const w = pulse.localToWorld(p.clone()); const [x, y] = toScreenW(w); return { t, x, y, side: x < cx0 ? -1 : 1 }; });
    for (const side of [-1, 1]) {
      const arr = items.filter(i => i.side === side).sort((a, b) => a.y - b.y);
      let last = -1e9; for (const it of arr) { it.ly = Math.max(it.y, last + 30); last = it.ly; }
      for (const it of arr) {
        const lx = cx0 + side * (rad * 0.9 + 30);
        c.strokeStyle = rgba(CSS_ACC, 0.85 * al); c.lineWidth = 1; c.beginPath(); c.moveTo(it.x, it.y); c.lineTo(lx - side * 14, it.ly); c.lineTo(lx, it.ly); c.stroke();
        c.fillStyle = rgba(CSS_ACC, al); c.beginPath(); c.arc(it.x, it.y, 3, 0, 6.283); c.fill();
        c.fillStyle = `rgba(11,31,58,${al})`; c.font = `600 ${Math.max(11, W * 0.0165)}px 'Chakra Petch',sans-serif`; c.textBaseline = 'middle';
        c.textAlign = side < 0 ? 'right' : 'left'; c.fillText(it.t, lx + side * 5, it.ly);
      }
    }
  }
  c.strokeStyle = rgba(CSS_ACC, 0.7); c.lineWidth = 1.5; const L = 18, o = 6;
  [[o, o, 1, 1], [W - o, o, -1, 1], [o, H - o, 1, -1], [W - o, H - o, -1, -1]].forEach(k => { c.beginPath(); c.moveTo(k[0], k[1] + k[3] * L); c.lineTo(k[0], k[1]); c.lineTo(k[0] + k[2] * L, k[1]); c.stroke(); });
}

// ------------------------------------------------------------ suelo y bucle
const floor = new THREE.Group();
for (const r of [0.16, 0.27, 0.38]) {
  const ringM = new THREE.MeshBasicMaterial({ color: 0x1f6fd1, transparent: true, opacity: 0.4, blending: THREE.NormalBlending, depthWrite: false, side: THREE.DoubleSide });
  ringMats.push(ringM);
  const ring = new THREE.Mesh(new THREE.RingGeometry(r - 0.0022, r + 0.0022, 96), ringM);
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.003; floor.add(ring);
}
const rippleMat = new THREE.MeshBasicMaterial({ color: 0x1f6fd1, transparent: true, opacity: 0, blending: THREE.NormalBlending, depthWrite: false, side: THREE.DoubleSide });
const rippleMesh = new THREE.Mesh(new THREE.RingGeometry(0.985, 1.0, 96), rippleMat); rippleMesh.rotation.x = -Math.PI / 2; rippleMesh.position.y = 0.004; floor.add(rippleMesh);
scene.add(floor);

let tPrev = performance.now(); let dbgT = null;
function frame(now) {
  const dt = Math.min(0.05, (now - tPrev) / 1000); tPrev = now;
  tick(now);
  const tms = now - lastBeat;
  const ts = clamp(Math.sqrt((60000 / clamp(bpmShown, 30, 200)) / 830), 0.62, 1.3);       // más rápido el ritmo, sístole más corta
  const tH = dbgT != null ? dbgT : tms;
  heartU.uTms.value = Math.min(tH, 5000); heartU.uTs.value = ts;
  const env = envVent(tH / ts) + 0.35 * envAtria(tH / ts);
  if (built) {
    if (!focused && now - lastInteract > 4000) goal.yaw = 0.55 * Math.sin(now * 0.0004);
    const k = 1 - Math.exp(-dt * 4.2);
    for (const kk of ['tx', 'ty', 'tz', 'yaw', 'pitch']) cam[kk] += (goal[kk] - cam[kk]) * k;
    cam.dist *= Math.pow(goal.dist / cam.dist, k);
    camera.position.set(cam.tx + cam.dist * Math.sin(cam.yaw) * Math.cos(cam.pitch), cam.ty + cam.dist * Math.sin(cam.pitch), cam.tz + cam.dist * Math.cos(cam.yaw) * Math.cos(cam.pitch));
    camera.lookAt(cam.tx, cam.ty, cam.tz);
    camera.near = Math.max(0.01, cam.dist * 0.05); camera.updateProjectionMatrix();
    const focusAmt = clamp((BODY_VIEW.dist - cam.dist) / (BODY_VIEW.dist - 0.6), 0, 1);
    fade += ((focused ? 0.07 : 1) - fade) * (1 - Math.exp(-dt * 4)); uniforms.uFade.value = fade; uniforms.uTime.value = now / 1000;
    const sc = 1 + 0.008 * env; pulse.scale.set(sc, sc, sc);
    const objetivo = (LIVE && !liveOn) ? 70 : bpmShown;
    bpmColor += (objetivo - bpmColor) * (1 - Math.exp(-dt * 2.0));
    const [cb, cd, rojo] = colorPorLpm(bpmColor);
    stateK = rojo;
    for (let i = 0; i < 3; i++) { CSS_HEART[i] = cb[i]; CSS_ACC[i] = cd[i]; }
    const cc = [CSS_HEART[0] / 255, CSS_HEART[1] / 255, CSS_HEART[2] / 255], ac = [CSS_ACC[0] / 255, CSS_ACC[1] / 255, CSS_ACC[2] / 255];
    if (skinMat) skinMat.uniforms.uColor.value.setRGB(cc[0], cc[1], cc[2]);
    accCol.setRGB(ac[0], ac[1], ac[2]);
    rimL.color.setRGB(ac[0], ac[1], ac[2]); rippleMat.color.setRGB(ac[0], ac[1], ac[2]);
    for (const rm of ringMats) rm.color.setRGB(ac[0], ac[1], ac[2]);
    for (const tm of tissueMats) tm.userData.u.uAlert.value = stateK;
    beatU.value = env * (hover && !focused ? 1.6 : 1.0);
    rimL.intensity = 0.8 + 0.5 * env;
    const rp = clamp((now - lastBeat) / 1100, 0, 1); rippleMesh.scale.setScalar(0.12 + rp * 0.5); rippleMat.opacity = 0.55 * (1 - rp) * fade;
    for (const ch of floor.children) if (ch !== rippleMesh) ch.material.opacity = 0.4 * fade;
    if (ptrXY && !ptr) { const hv = hitHeart(ptrXY[0], ptrXY[1]); if (hv !== hover) { hover = hv; glCanvas.style.cursor = hv && !focused ? 'pointer' : (focused ? 'grab' : 'default'); } }
    renderer.render(scene, camera);
    drawHUD(now, env, focusAmt);
  } else drawHUD(now, env, 0);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
load().then(() => {
  heartG.updateMatrixWorld(true); setupMotion(); computeLabels();
  const h = bodyBox.max.y - bodyBox.min.y; BODY_VIEW.ty = bodyBox.min.y + h * 0.5; BODY_VIEW.dist = (h * 1.14) / (2 * Math.tan(THREE.MathUtils.degToRad(17.5)));
  Object.assign(cam, BODY_VIEW); Object.assign(goal, BODY_VIEW);
  built = true; loadEl.style.display = 'none'; window.__ASTRA_READY = true;
}).catch(err => { loadEl.textContent = 'No se pudo cargar el modelo 3D: ' + err; window.__ASTRA_ERR = String(err); });
window.__astra = { setT(v) { dbgT = v; }, setFocus, get focused() { return focused; } };
