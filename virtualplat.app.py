import React, { useRef, useState, useEffect } from "react";

// Pizarra virtual para enseñanza de matemática (secundaria)
// Característica clave: al dibujar números, el trazado se suaviza y
// si se reconoce como dígito, se reemplaza por un dígito vectorial "limpio".
// Estilo: Tailwind CSS

// Nota: este componente es autónomo y usa un reconocedor $1 muy simple (plantillas
// incluidas) + suavizado de trazos con Catmull-Rom -> Bezier. Para producción
// puedes reemplazar el reconocedor por uno más robusto (TensorFlow.js, ML5, etc.)

export default function PizarraVirtualMatematicas() {
  const canvasRef = useRef(null);
  const ctxRef = useRef(null);
  const [drawing, setDrawing] = useState(false);
  const [strokes, setStrokes] = useState([]); // cada stroke = array de puntos
  const currentStrokeRef = useRef([]);
  const [color, setColor] = useState("black");
  const [thickness, setThickness] = useState(6);
  const [mode, setMode] = useState("draw"); // draw | erase
  const [message, setMessage] = useState("");

  // Inicializar canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    canvas.width = canvas.clientWidth * devicePixelRatio;
    canvas.height = canvas.clientHeight * devicePixelRatio;
    const ctx = canvas.getContext("2d");
    ctx.scale(devicePixelRatio, devicePixelRatio);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctxRef.current = ctx;
    redrawAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Funciones de utilidades: distancia
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

  // Suavizado Catmull-Rom a Bezier para trazar curvas suaves
  function smoothStrokePoints(points) {
    if (points.length < 3) return points;
    const out = [];
    // add first point
    out.push(points[0]);
    for (let i = 0; i < points.length - 2; i++) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const p2 = points[i + 2];
      // control points for cubic bezier (approximation)
      const cp1 = { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 };
      const cp2 = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
      out.push(cp1, p1, cp2);
    }
    out.push(points[points.length - 1]);
    return out;
  }

  // Dibuja un stroke (array de puntos) en el canvas con suavizado
  function drawStroke(ctx, points, opts = {}) {
    if (!ctx || points.length === 0) return;
    ctx.save();
    ctx.globalCompositeOperation = opts.erase ? "destination-out" : "source-over";
    ctx.lineWidth = opts.lineWidth || thickness;
    ctx.strokeStyle = opts.color || color;

    // si pocos puntos, dibujar línea simple
    if (points.length < 3) {
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
      ctx.stroke();
      ctx.restore();
      return;
    }

    const sm = smoothStrokePoints(points);
    ctx.beginPath();
    ctx.moveTo(sm[0].x, sm[0].y);
    // dibujar como segmentos Bezier-cúbicos aproximados (usando grupos de 3)
    for (let i = 1; i + 2 < sm.length; i += 3) {
      const cp1 = sm[i];
      const cp2 = sm[i + 1];
      const p = sm[i + 2];
      ctx.bezierCurveTo(cp1.x, cp1.y, cp2.x, cp2.y, p.x, p.y);
    }
    ctx.stroke();
    ctx.restore();
  }

  function handlePointerDown(e) {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX || e.touches[0].clientX) - rect.left;
    const y = (e.clientY || e.touches[0].clientY) - rect.top;
    setDrawing(true);
    currentStrokeRef.current = [{ x, y }];
    setMessage("");
  }

  function handlePointerMove(e) {
    if (!drawing) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX || (e.touches && e.touches[0].clientX)) - rect.left;
    const y = (e.clientY || (e.touches && e.touches[0].clientY)) - rect.top;
    const p = { x, y };
    const cur = currentStrokeRef.current;
    // filtrar puntos muy cercanos
    if (cur.length === 0 || dist(cur[cur.length - 1], p) > 1) {
      cur.push(p);
      // dibujar en tiempo real el stroke actual
      // para rendimiento: solo limpiar y redibujar lo necesario
      redrawAll();
      drawStroke(ctxRef.current, cur, { lineWidth: thickness, color: color, erase: mode === "erase" });
    }
  }

  function handlePointerUp() {
    if (!drawing) return;
    setDrawing(false);
    const stroke = currentStrokeRef.current.slice();
    if (stroke.length > 0) {
      setStrokes(s => [...s, { points: stroke, color, thickness, erase: mode === "erase" }]);
      // Intentar reconocer si es dígito
      setTimeout(() => tryRecognizeAndReplace(stroke), 10);
    }
    currentStrokeRef.current = [];
  }

  // Redibuja todo a partir de strokes
  function redrawAll() {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width / devicePixelRatio, canvas.height / devicePixelRatio);
    for (const s of strokes) drawStroke(ctx, s.points, { lineWidth: s.thickness, color: s.color, erase: s.erase });
  }

  // --- RECONOCEDOR SIMPLE $1-INSPIRED PARA DÍGITOS ---
  // Normaliza, re-muestra a N puntos y compara con plantillas.
  const RESAMPLE_N = 64;

  function resample(points, n = RESAMPLE_N) {
    if (points.length === 0) return [];
    const I = pathLength(points) / (n - 1);
    const newPts = [points[0]];
    let D = 0.0;
    for (let i = 1; i < points.length; i++) {
      const d = dist(points[i - 1], points[i]);
      if (D + d >= I) {
        const qx = points[i - 1].x + ((I - D) / d) * (points[i].x - points[i - 1].x);
        const qy = points[i - 1].y + ((I - D) / d) * (points[i].y - points[i - 1].y);
        const q = { x: qx, y: qy };
        newPts.push(q);
        points.splice(i, 0, q);
        D = 0.0;
      } else D += d;
    }
    while (newPts.length < n) newPts.push(points[points.length - 1]);
    return newPts;
  }

  function pathLength(pts) {
    let d = 0;
    for (let i = 1; i < pts.length; i++) d += dist(pts[i - 1], pts[i]);
    return d;
  }

  function centroid(points) {
    const s = points.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), { x: 0, y: 0 });
    return { x: s.x / points.length, y: s.y / points.length };
  }

  function boundingBox(points) {
    let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    for (const p of points) {
      if (p.x < minx) minx = p.x; if (p.y < miny) miny = p.y;
      if (p.x > maxx) maxx = p.x; if (p.y > maxy) maxy = p.y;
    }
    return { minx, miny, maxx, maxy, w: maxx - minx, h: maxy - miny };
  }

  function scaleToSquare(points, size = 200) {
    const box = boundingBox(points);
    const scale = Math.max(box.w, box.h) || 1;
    return points.map(p => ({ x: (p.x - box.minx) / scale * size, y: (p.y - box.miny) / scale * size }));
  }

  function translateToOrigin(points) {
    const c = centroid(points);
    return points.map(p => ({ x: p.x - c.x, y: p.y - c.y }));
  }

  // Distancia RMS entre puntos
  function pathDistance(a, b) {
    let d = 0;
    for (let i = 0; i < a.length; i++) d += dist(a[i], b[i]);
    return d / a.length;
  }

  // Plantillas simples para dígitos 0-9 (formular plantillas muy básicas como puntos)
  // Para mantener el ejemplo autocontenido, generaremos plantillas geométricas simples.
  function digitTemplates() {
    const t = {};
    // generar plantillas con puntos en formas aproximadas
    // 0: círculo
    t[0] = makeCircleTemplate();
    // 1: línea vertical
    t[1] = makeLineTemplate();
    // 2..9: combinaciones simples (esto es ejemplar — mejorar en producción)
    t[2] = makeTwoTemplate();
    t[3] = makeThreeTemplate();
    t[4] = makeFourTemplate();
    t[5] = makeFiveTemplate();
    t[6] = makeSixTemplate();
    t[7] = makeSevenTemplate();
    t[8] = makeEightTemplate();
    t[9] = makeNineTemplate();
    // procesar templates: resample, scale, translate
    for (const k in t) {
      t[k] = translateToOrigin(scaleToSquare(resample(t[k].slice())));
    }
    return t;
  }

  // helpers para crear plantillas geométricas
  function makeCircleTemplate() {
    const pts = [];
    for (let a = 0; a < Math.PI * 2; a += 0.3) pts.push({ x: Math.cos(a) * 50 + 100, y: Math.sin(a) * 50 + 100 });
    return pts;
  }
  function makeLineTemplate() {
    const pts = [];
    for (let y = 30; y <= 170; y += 3) pts.push({ x: 100, y });
    return pts;
  }
  function makeTwoTemplate() {
    const pts = [];
    for (let x = 40; x <= 160; x += 3) pts.push({ x, y: 40 });
    for (let t = 0; t <= 1; t += 0.03) pts.push({ x: 160 - t * 120, y: 40 + t * 80 });
    for (let x = 40; x <= 160; x += 3) pts.push({ x, y: 120 + (x - 40) * 0.4 });
    return pts;
  }
  function makeThreeTemplate() {
    const pts = [];
    for (let t = 0; t <= 1; t += 0.03) pts.push({ x: 40 + t * 120, y: 50 + Math.sin(t * Math.PI) * 20 });
    for (let t = 0; t <= 1; t += 0.03) pts.push({ x: 40 + t * 120, y: 120 + Math.sin(t * Math.PI) * 20 });
    return pts;
  }
  function makeFourTemplate() {
    const pts = [];
    for (let y = 40; y <= 120; y += 3) pts.push({ x: 140 - (y - 40) * 0.5, y });
    for (let x = 40; x <= 140; x += 3) pts.push({ x, y: 120 });
    for (let y = 40; y <= 160; y += 3) pts.push({ x: 90, y });
    return pts;
  }
  function makeFiveTemplate() {
    const pts = [];
    for (let x = 160; x >= 40; x -= 3) pts.push({ x, y: 40 });
    for (let t = 0; t <= 1; t += 0.03) pts.push({ x: 40 + t * 120, y: 40 + t * 80 });
    for (let x = 40; x <= 160; x += 3) pts.push({ x, y: 120 + (x - 40) * 0.4 });
    return pts;
  }
  function makeSixTemplate() {
    const pts = [];
    for (let a = Math.PI; a <= Math.PI * 3; a += 0.3) pts.push({ x: Math.cos(a) * 40 + 120, y: Math.sin(a) * 40 + 100 });
    return pts;
  }
  function makeSevenTemplate() {
    const pts = [];
    for (let x = 40; x <= 160; x += 3) pts.push({ x, y: 40 });
    for (let t = 0; t <= 1; t += 0.03) pts.push({ x: 160 - t * 120, y: 40 + t * 120 });
    return pts;
  }
  function makeEightTemplate() {
    const pts = [];
    for (let a = 0; a <= Math.PI * 2; a += 0.25) pts.push({ x: Math.cos(a) * 30 + 120, y: Math.sin(a) * 30 + 80 });
    for (let a = 0; a <= Math.PI * 2; a += 0.25) pts.push({ x: Math.cos(a) * 30 + 120, y: Math.sin(a) * 30 + 140 });
    return pts;
  }
  function makeNineTemplate() {
    const pts = [];
    for (let a = -Math.PI; a <= Math.PI; a += 0.25) pts.push({ x: Math.cos(a) * 30 + 120, y: Math.sin(a) * 30 + 80 });
    for (let y = 80; y <= 160; y += 3) pts.push({ x: 120, y });
    return pts;
  }

  const TEMPLATES = digitTemplates();

  function recognizeDigit(points) {
    if (points.length < 10) return { digit: null, score: Infinity };
    let pts = resample(points.map(p => ({ x: p.x, y: p.y })), RESAMPLE_N);
    pts = translateToOrigin(scaleToSquare(pts));
    let best = { digit: null, score: Infinity };
    for (const k in TEMPLATES) {
      const d = pathDistance(pts, TEMPLATES[k]);
      if (d < best.score) best = { digit: k, score: d };
    }
    return best;
  }

  // Reemplaza visualmente el trazo por un dígito "limpio" si confianza suficiente
  function tryRecognizeAndReplace(stroke) {
    // Strategy: si stroke es relativamente compacto (alto ratio de w/h < 1.2 y tamaño razonable)
    const box = boundingBox(stroke);
    const maxDim = Math.max(box.w, box.h);
    if (maxDim < 15) return; // muy pequeño

    const res = recognizeDigit(stroke);
    // umbral arbitrario: score menor a 15 -> buena coincidencia
    if (res.digit !== null && res.score < 15) {
      // borrar el stroke original (marcar como erase)
      // y dibujar un número "perfecto" en su lugar usando canvas
      const ctx = ctxRef.current;
      // dibujar número centrado en el bounding box
      const centerX = box.minx + box.w / 2;
      const centerY = box.miny + box.h / 2;
      // limpiar área cercana (pequeño rectángulo) antes de reemplazar
      ctx.clearRect(box.minx - 10, box.miny - 10, box.w + 20, box.h + 20);
      // eliminar el stroke de la lista de strokes (último añadido)
      setStrokes(s => {
        const copy = s.slice(0, -1);
        // agregar un objeto especial: digit
        copy.push({ digit: parseInt(res.digit, 10), x: box.minx, y: box.miny, w: box.w, h: box.h });
        return copy;
      });
      setMessage(`Reconocido como: ${res.digit} (confianza approx ${res.score.toFixed(1)})`);
    } else {
      // si no reconocido, sólo redibujar todo
      redrawAll();
    }
  }

  // Dibuja elementos de strokes y dígitos reemplazados
  function drawAllToCanvas() {
    const ctx = ctxRef.current;
    if (!ctx) return;
    ctx.clearRect(0, 0, canvasRef.current.width / devicePixelRatio, canvasRef.current.height / devicePixelRatio);
    for (const s of strokes) {
      if (s.digit !== undefined) {
        // dibujar dígito limpio (vectorial) en el rectángulo
        drawNiceDigit(ctx, s.digit, s.x, s.y, s.w, s.h);
      } else {
        drawStroke(ctx, s.points, { lineWidth: s.thickness, color: s.color, erase: s.erase });
      }
    }
  }

  // Dibuja un dígito estilizado (usando canvas) en la caja dada
  function drawNiceDigit(ctx, d, x, y, w, h) {
    ctx.save();
    ctx.lineWidth = Math.max(2, Math.min(12, Math.min(w, h) * 0.08));
    ctx.strokeStyle = "#111827"; // color casi negro
    ctx.fillStyle = "#111827";
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.font = `${Math.floor(Math.min(w, h) * 0.9)}px serif`;
    ctx.textBaseline = "middle";
    ctx.textAlign = "center";
    ctx.fillText(String(d), x + w / 2, y + h / 2 + 1);
    ctx.restore();
  }

  // Cuando cambian los strokes, redibujar
  useEffect(() => drawAllToCanvas(), [strokes]);

  // controles
  function undo() {
    setStrokes(s => s.slice(0, -1));
  }
  function clearAll() {
    setStrokes([]);
    setMessage("");
  }
  function savePNG() {
    const link = document.createElement("a");
    link.download = "pizarra.png";
    link.href = canvasRef.current.toDataURL("image/png");
    link.click();
  }

  return (
    <div className="flex flex-col gap-3 p-4 bg-gray-50 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Pizarra Virtual — Matemáticas (secundaria)</h2>
        <div className="flex gap-2">
          <button className="px-3 py-1 rounded bg-blue-600 text-white" onClick={() => setMode("draw")}>Dibujar</button>
          <button className="px-3 py-1 rounded bg-yellow-500 text-white" onClick={() => setMode("erase")}>Borrar</button>
          <button className="px-3 py-1 rounded bg-gray-200" onClick={undo}>Deshacer</button>
          <button className="px-3 py-1 rounded bg-red-500 text-white" onClick={clearAll}>Limpiar</button>
          <button className="px-3 py-1 rounded bg-green-600 text-white" onClick={savePNG}>Guardar PNG</button>
        </div>
      </div>

      <div className="flex gap-3">
        <div className="w-56 p-3 bg-white rounded shadow">
          <label className="block text-sm">Color</label>
          <input type="color" value={color} onChange={e => setColor(e.target.value)} className="w-full h-10" />
          <label className="block text-sm mt-2">Grosor</label>
          <input type="range" min={1} max={30} value={thickness} onChange={e => setThickness(parseInt(e.target.value))} className="w-full" />
          <div className="mt-3 text-sm text-gray-600">Modo: <strong>{mode}</strong></div>
          <div className="mt-3 text-sm text-gray-700">Consejo: Escribe los números de forma clara y sin levantar demasiado el lápiz — el sistema intentará reconocer y limpiar automáticamente los dígitos.</div>
        </div>

        <div className="flex-1 relative bg-white rounded shadow" style={{ minHeight: 420 }}>
          <canvas
            ref={canvasRef}
            onMouseDown={handlePointerDown}
            onTouchStart={handlePointerDown}
            onMouseMove={handlePointerMove}
            onTouchMove={handlePointerMove}
            onMouseUp={handlePointerUp}
            onTouchEnd={handlePointerUp}
            onMouseLeave={handlePointerUp}
            className="w-full h-full touch-none"
            style={{ width: "100%", height: "100%", background: "white", borderRadius: 8 }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">{message}</div>
        <div className="text-sm text-gray-500">Herramientas: reconocimiento simple de dígitos + suavizado de trazos.</div>
      </div>
    </div>
  );
}
