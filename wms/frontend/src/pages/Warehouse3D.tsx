import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { PointerLockControls } from 'three/examples/jsm/controls/PointerLockControls.js'
import { Footprints, Orbit, Flame, Grid3x3, Gauge, Search, Boxes, Loader2, X } from 'lucide-react'
import { getAllLocations, getSensors, getLocationContents } from '../lib/api'
import { onRealtimeEvent } from '../lib/realtime'
import { BUILDING, CELL_W, ROW_D } from '../lib/warehouseLayout'

/**
 * 3D Digital Twin — immersiv "sklad bo'ylab yurish".
 *  • Orbit rejimi (qushbaqadan) VA Walk rejimi (birinchi shaxs, WASD + sichqoncha)
 *  • Ko'z darajasidagi kamera — haqiqiy zavod skladida yurgandek
 *  • Issiqlik xaritasi (band/bo'sh), hover yoritish, bosib tanlash
 *  • Real-time: qoldiq o'zgarsa tegishli pallet miltillaydi
 *  • Minimap — pastda joylashuv + kamera nuqtasi
 */

const TH = 1.35            // etaj balandligi
const BASE_Y = 0.12
const EYE = 1.7            // ko'z darajasi (m)

const STATE_COLOR: Record<string, number> = {
  occupied: 0x16a34a, partial: 0xd97706, blocked: 0xdc2626, empty: 0xcbd5e1,
}

type Slot = { cellId: string; row: string; tier: number; pos: number; status: string; locId: string | null }
type Mode = 'orbit' | 'walk'
type MiniRack = { x: number; z: number; w: number; d: number }

export default function Warehouse3D({ warehouseId }: { warehouseId: string }) {
  const mountRef = useRef<HTMLDivElement>(null)
  const [selected, setSelected] = useState<Slot | null>(null)
  const [stats, setStats] = useState({ total: 0, occ: 0, free: 0 })
  const [isDemo, setIsDemo] = useState(false)
  const [mode, setMode] = useState<Mode>('orbit')
  const [heatmap, setHeatmap] = useState(false)
  const [walkHint, setWalkHint] = useState(false)
  const [mini, setMini] = useState<{ racks: MiniRack[]; w: number; d: number; cam: [number, number] }>({ racks: [], w: 1, d: 1, cam: [0, 0] })
  const [query, setQuery] = useState('')
  const [contents, setContents] = useState<any | null>(null)
  const [contentsLoading, setContentsLoading] = useState(false)

  // Effekt bilan React o'rtasidagi ko'priklar (refs — qayta init qilmaslik uchun)
  const enterWalkRef = useRef<(() => void) | null>(null)
  const exitWalkRef = useRef<(() => void) | null>(null)
  const applyHeatRef = useRef<((on: boolean) => void) | null>(null)
  const flyToRef = useRef<((q: string) => Slot | null) | null>(null)

  useEffect(() => { mode === 'walk' ? enterWalkRef.current?.() : exitWalkRef.current?.() }, [mode])
  useEffect(() => { applyHeatRef.current?.(heatmap) }, [heatmap])

  // Tanlangan yacheyka ichidagi tovar/kodlarni yuklaymiz.
  useEffect(() => {
    if (!selected?.locId) { setContents(null); return }
    let cancel = false
    setContentsLoading(true); setContents(null)
    getLocationContents(selected.locId)
      .then(d => { if (!cancel) setContents(d) })
      .catch(() => { if (!cancel) setContents(null) })
      .finally(() => { if (!cancel) setContentsLoading(false) })
    return () => { cancel = true }
  }, [selected?.locId])

  const runSearch = () => {
    const hit = flyToRef.current?.(query.trim())
    if (hit) setSelected(hit)
  }

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return
    let disposed = false

    const width = mount.clientWidth || 800
    const height = mount.clientHeight || 600

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xdfe5ee)
    scene.fog = new THREE.Fog(0xdfe5ee, 60, 260)
    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 2000)
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(width, height)
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.05
    mount.appendChild(renderer.domElement)

    scene.add(new THREE.HemisphereLight(0xbcd0e6, 0x6b7688, 0.55))
    scene.add(new THREE.AmbientLight(0xffffff, 0.18))
    const dir = new THREE.DirectionalLight(0xffffff, 1.15)
    dir.position.set(40, 80, 30)
    dir.castShadow = true
    dir.shadow.mapSize.set(2048, 2048)
    dir.shadow.camera.near = 1; dir.shadow.camera.far = 400
    dir.shadow.camera.left = -120; dir.shadow.camera.right = 120
    dir.shadow.camera.top = 120; dir.shadow.camera.bottom = -120
    dir.shadow.bias = -0.0004
    scene.add(dir)
    const dir2 = new THREE.DirectionalLight(0xffffff, 0.3); dir2.position.set(-25, 40, -30); scene.add(dir2)

    // ── Controls: Orbit (default) + PointerLock (walk) ────────────────────────
    const orbit = new OrbitControls(camera, renderer.domElement)
    orbit.enableDamping = true
    orbit.dampingFactor = 0.12
    orbit.maxPolarAngle = Math.PI / 2.05
    const walk = new PointerLockControls(camera, renderer.domElement)

    let needsRender = true
    // Kamera "uchish" tween'i (qidiruv → yacheykaga silliq o'tish)
    let tween: { camA: THREE.Vector3; camB: THREE.Vector3; tgtA: THREE.Vector3; tgtB: THREE.Vector3; t: number } | null = null
    const render = () => { if (!disposed) renderer.render(scene, camera) }
    orbit.addEventListener('change', () => { needsRender = true })

    // Klaviatura (WASD / o'qlar)
    const keys: Record<string, boolean> = {}
    const onKeyDown = (e: KeyboardEvent) => { keys[e.code] = true }
    const onKeyUp = (e: KeyboardEvent) => { keys[e.code] = false }
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)

    let walkActive = false
    walk.addEventListener('lock', () => { walkActive = true; setWalkHint(true) })
    walk.addEventListener('unlock', () => {
      walkActive = false; setWalkHint(false)
      if (!disposed) setMode('orbit')
    })

    const root = new THREE.Group()
    scene.add(root)

    // Beton pol + grid
    const grid = new THREE.GridHelper(Math.max(BUILDING.w, BUILDING.h) + 8, 30, 0xb8c0cc, 0xd2d9e2)
    ;(grid.material as THREE.Material).opacity = 0.35
    ;(grid.material as THREE.Material).transparent = true
    scene.add(grid)
    const floorGeo = new THREE.PlaneGeometry(BUILDING.w + 40, BUILDING.h + 40)
    const floorMat = new THREE.MeshStandardMaterial({ color: 0xcdd2d8, roughness: 0.96 })
    const floor = new THREE.Mesh(floorGeo, floorMat)
    floor.rotation.x = -Math.PI / 2
    floor.receiveShadow = true
    scene.add(floor)

    // Matn sprite
    const labelDisposables: THREE.SpriteMaterial[] = []
    function makeLabel(text: string, color: string, bg: string, s = 1, depth = false): THREE.Sprite {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')!
      const fs = 48
      ctx.font = `bold ${fs}px sans-serif`
      const w = Math.ceil(ctx.measureText(text).width) + 30
      canvas.width = w; canvas.height = fs + 26
      ctx.font = `bold ${fs}px sans-serif`
      ctx.fillStyle = bg
      ctx.beginPath(); ctx.roundRect(0, 0, w, canvas.height, 12); ctx.fill()
      ctx.fillStyle = color; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      ctx.fillText(text, w / 2, canvas.height / 2)
      const tex = new THREE.CanvasTexture(canvas); tex.anisotropy = 4
      const mat = new THREE.SpriteMaterial({ map: tex, depthTest: depth, depthWrite: false, transparent: true })
      labelDisposables.push(mat)
      const sp = new THREE.Sprite(mat)
      sp.scale.set((w / canvas.height) * 1.5 * s, 1.5 * s, 1)
      return sp
    }

    const slotInfo: Slot[] = []
    const geoDisposables: THREE.BufferGeometry[] = []
    const matDisposables: THREE.Material[] = []
    const codeToInst: Map<string, number[]> = new Map()
    const statusColor: THREE.Color[] = []        // asl status rangi (heatmap qaytishi uchun)
    const heatColor: THREE.Color[] = []          // issiqlik xaritasi rangi
    let loadMeshRef: THREE.InstancedMesh | null = null

    // Hover highlight (wireframe box)
    const hlGeo = new THREE.BoxGeometry(1, 1, 1)
    const hlMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, wireframe: true, transparent: true, opacity: 0.9 })
    const highlight = new THREE.Mesh(hlGeo, hlMat)
    highlight.visible = false
    scene.add(highlight)
    const slotMatrix: THREE.Matrix4[] = []       // har slotning yuk matritsasi (highlight/flash uchun)

    getAllLocations(warehouseId).catch(() => [] as any[]).then((data: any[]) => {
      if (disposed) return

      const racksMap = new Map<string, { name: string; cells: any[]; maxT: number; maxP: number; rx: number; rz: number }>()
      for (const l of data) {
        if (l.tier == null || l.position == null) continue
        const rg = l.rack_group || (l.code || '').replace(/-\d+$/, '') || l.code || '?'
        let r = racksMap.get(rg)
        if (!r) { r = { name: rg, cells: [], maxT: 1, maxP: 1, rx: Infinity, rz: Infinity }; racksMap.set(rg, r) }
        r.cells.push({ id: l.id, code: l.code, tier: l.tier, position: l.position, status: l.status })
        r.maxT = Math.max(r.maxT, l.tier); r.maxP = Math.max(r.maxP, l.position)
        r.rx = Math.min(r.rx, l.x ?? 0); r.rz = Math.min(r.rz, l.y ?? 0)
      }
      const racks = [...racksMap.values()].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }))
      setIsDemo(racks.length === 0)

      const placed = racks.map(rack => ({
        rack,
        ox: Number.isFinite(rack.rx) ? rack.rx : 0,
        oz: Number.isFinite(rack.rz) ? rack.rz : 0,
      }))
      let extentX = 1, extentZ = 1
      for (const { rack, ox, oz } of placed) {
        extentX = Math.max(extentX, ox + rack.maxP * CELL_W)
        extentZ = Math.max(extentZ, oz + ROW_D)
      }
      root.position.set(-extentX / 2, 0, -extentZ / 2)
      floor.position.set(0, -0.02, 0)

      let totalSlots = 0
      for (const r of racks) totalSlots += r.maxT * r.maxP
      let nPosts = 0, nBeams = 0
      for (const r of racks) { nPosts += (r.maxP + 1) * 2; nBeams += r.maxT * 2 }

      const palletGeo = new THREE.BoxGeometry(1, 1, 1)
      const loadGeo = new THREE.BoxGeometry(1, 1, 1)
      const postGeo = new THREE.BoxGeometry(1, 1, 1)
      const beamGeo = new THREE.BoxGeometry(1, 1, 1)
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x9a6b3f, roughness: 0.95 })
      // Shrink-wrap qilingan tiniq suv butilkalari — yaltiroq (past roughness),
      // ozgina shaffof plastik plyonka. Instance rangi tepada beriladi.
      const loadMat = new THREE.MeshStandardMaterial({
        color: 0xffffff, roughness: 0.14, metalness: 0.02,
        transparent: true, opacity: 0.96,
      })
      const postMat = new THREE.MeshStandardMaterial({ color: 0x1e40af, roughness: 0.42, metalness: 0.55 })
      const beamMat = new THREE.MeshStandardMaterial({ color: 0xea580c, roughness: 0.5, metalness: 0.45 })
      geoDisposables.push(palletGeo, loadGeo, postGeo, beamGeo)
      matDisposables.push(woodMat, loadMat, postMat, beamMat)

      const palletMesh = new THREE.InstancedMesh(palletGeo, woodMat, Math.max(1, totalSlots))
      palletMesh.castShadow = true; palletMesh.receiveShadow = true
      const loadMesh = new THREE.InstancedMesh(loadGeo, loadMat, Math.max(1, totalSlots))
      loadMesh.name = 'slots'; loadMesh.castShadow = true; loadMesh.receiveShadow = true
      loadMeshRef = loadMesh
      const postMesh = new THREE.InstancedMesh(postGeo, postMat, Math.max(1, nPosts)); postMesh.castShadow = true
      const beamMesh = new THREE.InstancedMesh(beamGeo, beamMat, Math.max(1, nBeams)); beamMesh.castShadow = true

      const dummy = new THREE.Object3D()
      const water = new THREE.Color(0xbfe0f5)   // shrink-wrap suv rangi
      const icy = new THREE.Color(0xd7ecf9)     // ogohlantirish holatlarига aralashadi
      const hidden = new THREE.Matrix4().makeScale(0, 0, 0)
      const miniRacks: MiniRack[] = []

      let occ = 0, si = 0, pi = 0, bi = 0
      for (const { rack, ox, oz } of placed) {
        const byTP = new Map<string, { id: string; code: string; status: string }>()
        for (const c of rack.cells) byTP.set(`${c.tier}:${c.position}`, c)
        const rackTopY = rack.maxT * TH + BASE_Y
        const cx = ox + (rack.maxP * CELL_W) / 2
        const beamLen = rack.maxP * CELL_W
        miniRacks.push({ x: ox, z: oz, w: rack.maxP * CELL_W, d: ROW_D })

        for (let t = 1; t <= rack.maxT; t++) {
          for (let p = 1; p <= rack.maxP; p++) {
            const c = byTP.get(`${t}:${p}`)
            const status = c?.status ?? 'empty'
            if (status === 'occupied') occ++
            const px = ox + (p - 1) * CELL_W + CELL_W / 2
            const pz = oz + ROW_D / 2
            const tierY = (t - 1) * TH + BASE_Y
            dummy.position.set(px, tierY + 0.07, pz)
            dummy.scale.set(CELL_W * 0.9, 0.14, ROW_D * 0.86)
            dummy.updateMatrix()
            palletMesh.setMatrixAt(si, dummy.matrix)
            const lh = TH * 0.72
            dummy.position.set(px, tierY + 0.14 + lh / 2, pz)
            dummy.scale.set(CELL_W * 0.88, lh, ROW_D * 0.86)
            dummy.updateMatrix()
            slotMatrix.push(dummy.matrix.clone())
            if (status === 'empty') loadMesh.setMatrixAt(si, hidden)
            else loadMesh.setMatrixAt(si, dummy.matrix)
            // Band = tiniq suv (haqiqiy sklad kabi); qisman/blok = ogohlantirish rangi
            // (icy blue bilan aralashib, plastik plyonka tusini beradi).
            const sc = status === 'occupied'
              ? water.clone()
              : new THREE.Color().setHex(STATE_COLOR[status] ?? STATE_COLOR.empty).lerp(icy, 0.5)
            loadMesh.setColorAt(si, sc)
            statusColor.push(sc.clone())
            heatColor.push(new THREE.Color())
            const code = c?.code ?? `${rack.name}-?`
            slotInfo.push({ cellId: code, row: rack.name, tier: t, pos: p, status, locId: c?.id ?? null })
            if (!codeToInst.has(code)) codeToInst.set(code, [])
            codeToInst.get(code)!.push(si)
            si++
          }
        }

        for (let p = 0; p <= rack.maxP; p++) {
          const xb = ox + p * CELL_W
          for (const zb of [oz, oz + ROW_D]) {
            dummy.position.set(xb, rackTopY / 2, zb); dummy.scale.set(0.14, rackTopY, 0.14)
            dummy.updateMatrix(); postMesh.setMatrixAt(pi++, dummy.matrix)
          }
        }
        for (let t = 1; t <= rack.maxT; t++) {
          const by = (t - 1) * TH + BASE_Y
          for (const zb of [oz, oz + ROW_D]) {
            dummy.position.set(cx, by, zb); dummy.scale.set(beamLen, 0.12, 0.16)
            dummy.updateMatrix(); beamMesh.setMatrixAt(bi++, dummy.matrix)
          }
        }
        const sp = makeLabel(rack.name, '#ffffff', '#2563eb', 0.4, true)
        sp.position.set(cx, rackTopY + 0.35, oz + ROW_D / 2)
        root.add(sp)
      }
      palletMesh.instanceMatrix.needsUpdate = true
      loadMesh.instanceMatrix.needsUpdate = true
      if (loadMesh.instanceColor) loadMesh.instanceColor.needsUpdate = true
      postMesh.instanceMatrix.needsUpdate = true
      beamMesh.instanceMatrix.needsUpdate = true
      root.add(palletMesh, loadMesh, postMesh, beamMesh)

      // ── Po'lat farma shift + high-bay chiroqlar (haqiqiy zavod kabi) ──────────
      const ceilY = Math.max(TH * 3, ...racks.map(r => r.maxT * TH + BASE_Y)) + 3.2
      // Shift paneli (metall, soya qabul qilmaydi — faqat fon)
      const ceilGeo = new THREE.PlaneGeometry(extentX + 24, extentZ + 24)
      // FrontSide: normal pastga qaraydi → walk rejimида (pastdan) ko'rinadi,
      // orbit (yuqoridan) esa backface culling bilan ko'rmaydi → rack'lar ochiq.
      const ceilMat = new THREE.MeshStandardMaterial({ color: 0x33404f, roughness: 0.9, side: THREE.FrontSide })
      const ceil = new THREE.Mesh(ceilGeo, ceilMat)
      ceil.rotation.x = Math.PI / 2
      ceil.position.set(extentX / 2, ceilY + 0.6, extentZ / 2)
      root.add(ceil); geoDisposables.push(ceilGeo); matDisposables.push(ceilMat)
      // High-bay chiroqlar: grid bo'ylab, har biri emissiv disk + PointLight
      const lampGeo = new THREE.CylinderGeometry(0.45, 0.6, 0.35, 20)
      const lampMat = new THREE.MeshStandardMaterial({
        color: 0xffffff, emissive: 0xdff0ff, emissiveIntensity: 2.4, roughness: 0.4,
      })
      geoDisposables.push(lampGeo); matDisposables.push(lampMat)
      const cols = Math.max(2, Math.round(extentX / 12))
      const rows = Math.max(1, Math.round(extentZ / 8))
      for (let cxi = 0; cxi < cols; cxi++) {
        for (let czi = 0; czi < rows; czi++) {
          const lx = (extentX * (cxi + 0.5)) / cols
          const lz = (extentZ * (czi + 0.5)) / rows
          const lamp = new THREE.Mesh(lampGeo, lampMat)
          lamp.position.set(lx, ceilY, lz)
          root.add(lamp)
          const pl = new THREE.PointLight(0xeaf4ff, 26, 26, 2.0)
          pl.position.set(lx, ceilY - 0.4, lz)
          root.add(pl)
        }
      }

      // Heatmap ranglari (yashil=bo'sh → qizil=band, holatga qarab)
      for (let i = 0; i < statusColor.length; i++) {
        const st = slotInfo[i].status
        const ratio = st === 'occupied' ? 1 : st === 'partial' ? 0.55 : st === 'blocked' ? 0.85 : 0.05
        heatColor[i].setHSL((1 - ratio) * 0.33, 0.75, 0.5)   // 0.33=yashil, 0=qizil
      }
      applyHeatRef.current = (on: boolean) => {
        if (!loadMeshRef) return
        for (let i = 0; i < statusColor.length; i++)
          loadMeshRef.setColorAt(i, on ? heatColor[i] : statusColor[i])
        if (loadMeshRef.instanceColor) loadMeshRef.instanceColor.needsUpdate = true
        needsRender = true
      }

      setStats({ total: totalSlots, occ, free: totalSlots - occ })
      setMini({ racks: miniRacks, w: extentX, d: extentZ, cam: [0, 0] })

      // Sensorlar
      const maxTop = Math.max(TH * 2, ...racks.map(r => r.maxT * TH + BASE_Y))
      getSensors(warehouseId).catch(() => [] as any[]).then((sensors: any[]) => {
        if (disposed || !Array.isArray(sensors) || sensors.length === 0) return
        const n = sensors.length
        sensors.forEach((s, i) => {
          const sx = (extentX * (i + 1)) / (n + 1)
          const sy = maxTop + 0.6, sz = -1.8
          const alert = s.status === 'alert'
          const col = alert ? 0xdc2626 : s.status === 'no-data' ? 0x94a3b8 : 0x16a34a
          const gGeo = new THREE.SphereGeometry(0.16, 16, 16)
          const gMat = new THREE.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 0.9 })
          const glow = new THREE.Mesh(gGeo, gMat); glow.position.set(sx, sy, sz)
          root.add(glow); geoDisposables.push(gGeo); matDisposables.push(gMat)
          const tt = s.last_temp != null ? `${Number(s.last_temp).toFixed(1)}°C` : '—'
          const hh = s.last_hum != null ? `${Math.round(Number(s.last_hum))}%` : '—'
          const lab = makeLabel(`${s.name}  🌡${tt} 💧${hh}`, '#ffffff', alert ? '#dc2626' : '#0f766e', 0.8)
          lab.position.set(sx, sy + 0.9, sz); root.add(lab)
        })
        needsRender = true
      })

      // Kamera boshlang'ich (orbit)
      const span = Math.max(extentX, extentZ, 10)
      camera.position.set(span * 0.15, span * 0.55, extentZ + span * 0.6)
      orbit.target.set(0, TH, 0)
      orbit.update()

      // Walk kirish/chiqish
      enterWalkRef.current = () => {
        orbit.enabled = false
        camera.position.set(0, EYE, extentZ / 2 + 3)
        camera.lookAt(0, EYE, 0)
        walk.lock()
        needsRender = true
      }
      exitWalkRef.current = () => {
        if (walkActive) walk.unlock()
        orbit.enabled = true
        camera.position.set(span * 0.15, span * 0.55, extentZ + span * 0.6)
        orbit.target.set(0, TH, 0); orbit.update()
        needsRender = true
      }

      // Qidiruv → yacheykaga uchish (kod yoki qator bo'yicha). Topilgan Slot'ni qaytaradi.
      flyToRef.current = (q: string): Slot | null => {
        if (!q) return null
        const uq = q.toUpperCase()
        let idx = slotInfo.findIndex(s => s.cellId.toUpperCase() === uq)
        if (idx < 0) idx = slotInfo.findIndex(s => s.cellId.toUpperCase().includes(uq) || s.row.toUpperCase() === uq)
        if (idx < 0 || !slotMatrix[idx]) return null
        const world = new THREE.Vector3().setFromMatrixPosition(slotMatrix[idx].clone().premultiply(root.matrixWorld))
        // Yacheyka oldida, biroz balandroq turadigan kamera nuqtasi
        const camTo = world.clone().add(new THREE.Vector3(4, 3.5, 6))
        tween = {
          camA: camera.position.clone(), camB: camTo,
          tgtA: orbit.target.clone(), tgtB: world.clone(), t: 0,
        }
        flashing.push({ inst: idx, until: performance.now() + 2600 })
        needsRender = true
        return slotInfo[idx]
      }

      needsRender = true
      render()
    })

    // Hover + tanlash (raycast loadMesh)
    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    let hovered = -1
    const pickInstance = (ev: MouseEvent): number => {
      const mm = loadMeshRef
      if (!mm) return -1
      const rect = renderer.domElement.getBoundingClientRect()
      pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1
      pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1
      raycaster.setFromCamera(pointer, camera)
      const hit = raycaster.intersectObject(mm)[0]
      return hit && hit.instanceId != null ? hit.instanceId : -1
    }
    const onMove = (ev: MouseEvent) => {
      if (walkActive) return
      const id = pickInstance(ev)
      if (id === hovered) return
      hovered = id
      if (id >= 0 && slotMatrix[id]) {
        highlight.position.setFromMatrixPosition(slotMatrix[id].clone().premultiply(root.matrixWorld))
        const sc = new THREE.Vector3(); slotMatrix[id].decompose(new THREE.Vector3(), new THREE.Quaternion(), sc)
        highlight.scale.copy(sc).multiplyScalar(1.06)
        highlight.visible = true
        renderer.domElement.style.cursor = 'pointer'
      } else {
        highlight.visible = false
        renderer.domElement.style.cursor = ''
      }
      needsRender = true
    }
    const onClick = (ev: MouseEvent) => {
      if (walkActive) return
      const id = pickInstance(ev)
      if (id >= 0) setSelected(slotInfo[id] ?? null)
      needsRender = true
    }
    renderer.domElement.addEventListener('mousemove', onMove)
    renderer.domElement.addEventListener('click', onClick)

    // Real-time: qoldiq o'zgargan yacheyka miltillaydi
    const flashing: { inst: number; until: number }[] = []
    const offRt = onRealtimeEvent((e) => {
      if (e.type !== 'stock' && e.type !== 'reservation') return
      // location_id emas, biz kod bilan indekslaymiz — reservation'da code bor
      const codes = e.code ? [e.code] : []
      for (const code of codes) {
        for (const inst of codeToInst.get(code) ?? [])
          flashing.push({ inst, until: performance.now() + 2200 })
      }
      needsRender = true
    })

    const onResize = () => {
      const w = mount.clientWidth || 800
      const h = mount.clientHeight || 600
      if (w === 0) return
      camera.aspect = w / h; camera.updateProjectionMatrix()
      renderer.setSize(w, h); needsRender = true
    }
    window.addEventListener('resize', onResize)
    const ro = new ResizeObserver(() => onResize()); ro.observe(mount)

    // Minimap kamera nuqtasi (throttled → React state)
    let lastMini = 0

    let raf = 0, prev = performance.now()
    const fwd = new THREE.Vector3(), right = new THREE.Vector3()
    const loop = () => {
      raf = requestAnimationFrame(loop)
      const now = performance.now()
      const dt = Math.min(0.05, (now - prev) / 1000); prev = now

      if (walkActive) {
        camera.getWorldDirection(fwd); fwd.y = 0; fwd.normalize()
        right.crossVectors(fwd, camera.up).normalize()
        const speed = (keys['ShiftLeft'] ? 9 : 4.2) * dt
        const move = new THREE.Vector3()
        if (keys['KeyW'] || keys['ArrowUp']) move.add(fwd)
        if (keys['KeyS'] || keys['ArrowDown']) move.sub(fwd)
        if (keys['KeyD'] || keys['ArrowRight']) move.add(right)
        if (keys['KeyA'] || keys['ArrowLeft']) move.sub(right)
        if (move.lengthSq() > 0) {
          move.normalize().multiplyScalar(speed)
          camera.position.add(move)
          camera.position.y = EYE
          needsRender = true
        }
      } else {
        if (tween) {
          tween.t = Math.min(1, tween.t + dt * 1.6)
          const e = 1 - Math.pow(1 - tween.t, 3)   // easeOutCubic
          camera.position.lerpVectors(tween.camA, tween.camB, e)
          orbit.target.lerpVectors(tween.tgtA, tween.tgtB, e)
          orbit.update()
          if (tween.t >= 1) tween = null
          needsRender = true
        } else if (orbit.update()) needsRender = true
      }

      // flash animatsiyasi
      if (flashing.length && loadMeshRef) {
        for (let i = flashing.length - 1; i >= 0; i--) {
          const f = flashing[i]
          if (now > f.until) {
            loadMeshRef.setColorAt(f.inst, (heatmap ? heatColor : statusColor)[f.inst])
            flashing.splice(i, 1)
          } else {
            const k = 0.5 + 0.5 * Math.sin(now * 0.02)
            loadMeshRef.setColorAt(f.inst, new THREE.Color(0x38bdf8).lerp(new THREE.Color(0xffffff), k))
          }
        }
        if (loadMeshRef.instanceColor) loadMeshRef.instanceColor.needsUpdate = true
        needsRender = true
      }

      // minimap kamera (10/s)
      if (now - lastMini > 100) {
        lastMini = now
        setMini(prevM => prevM.racks.length
          ? { ...prevM, cam: [camera.position.x + prevM.w / 2, camera.position.z + prevM.d / 2] }
          : prevM)
      }

      if (needsRender) { render(); needsRender = false }
    }
    loop()

    return () => {
      disposed = true
      enterWalkRef.current = null; exitWalkRef.current = null; applyHeatRef.current = null
      cancelAnimationFrame(raf)
      offRt()
      ro.disconnect()
      window.removeEventListener('resize', onResize)
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
      renderer.domElement.removeEventListener('mousemove', onMove)
      renderer.domElement.removeEventListener('click', onClick)
      orbit.dispose(); walk.dispose()
      geoDisposables.forEach(g => g.dispose())
      matDisposables.forEach(m => m.dispose())
      labelDisposables.forEach(m => { m.map?.dispose(); m.dispose() })
      hlGeo.dispose(); hlMat.dispose()
      floorGeo.dispose(); floorMat.dispose()
      grid.geometry.dispose(); (grid.material as THREE.Material).dispose()
      renderer.dispose()
      if (renderer.domElement.parentNode === mount) mount.removeChild(renderer.domElement)
    }
  }, [warehouseId])

  // ── Minimap SVG ──
  const MINI_W = 190
  const miniScale = MINI_W / Math.max(mini.w, 1)
  const miniH = Math.max(40, mini.d * miniScale + 10)

  return (
    <div className="relative">
      <div ref={mountRef} style={{ width: '100%', height: 620 }}
        className="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 cursor-grab active:cursor-grabbing bg-slate-200" />

      {/* Rejim + boshqaruv paneli */}
      <div className="absolute top-3 left-3 flex flex-col gap-2">
        <div className="flex rounded-lg overflow-hidden border border-slate-200 shadow-md text-xs bg-white">
          <button onClick={() => setMode('orbit')}
            className={`px-3 py-1.5 flex items-center gap-1.5 transition ${mode === 'orbit' ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}>
            <Orbit size={14} /> Aylanma
          </button>
          <button onClick={() => setMode('walk')}
            className={`px-3 py-1.5 flex items-center gap-1.5 transition ${mode === 'walk' ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}>
            <Footprints size={14} /> Yurish
          </button>
        </div>
        <button onClick={() => setHeatmap(h => !h)}
          className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-xs shadow-md border transition ${heatmap ? 'bg-orange-500 text-white border-orange-500' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'}`}>
          {heatmap ? <Flame size={14} /> : <Gauge size={14} />} Issiqlik xaritasi
        </button>
      </div>

      {/* Qidiruv — yacheyka kodiga uchish */}
      {mode === 'orbit' && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 flex items-center gap-1.5 bg-white/95 rounded-lg px-2 py-1.5 shadow-md border border-slate-100">
          <Search size={14} className="text-slate-400" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') runSearch() }}
            placeholder="Yacheyka kodi (A-05)…"
            className="text-xs bg-transparent outline-none w-36 text-slate-700 placeholder:text-slate-400"
          />
          <button onClick={runSearch}
            className="text-xs px-2 py-0.5 rounded bg-blue-600 text-white hover:bg-blue-700 transition">
            Top
          </button>
        </div>
      )}

      {/* Statistika */}
      <div className="absolute top-3 right-3 bg-white/95 rounded-lg px-3 py-2.5 text-xs text-slate-600 shadow-md border border-slate-100">
        <div className="font-semibold mb-1.5 flex items-center gap-2">
          {stats.total} joy
          {isDemo && <span className="px-1.5 py-0.5 bg-amber-50 text-amber-600 border border-amber-200 rounded text-[10px] font-medium">Demo</span>}
        </div>
        <div className="text-slate-400 mb-1.5">
          Band: <b className="text-green-600">{stats.occ}</b> · Bo'sh: <b className="text-slate-500">{stats.free}</b>
        </div>
        <div className="flex items-center gap-2.5 flex-wrap">
          <Legend c="#16a34a" t="band" /><Legend c="#d97706" t="qisman" />
          <Legend c="#dc2626" t="blok" /><Legend c="#cbd5e1" t="bo'sh" />
        </div>
      </div>

      {/* Yurish rejimi ko'rsatma + crosshair */}
      {mode === 'walk' && (
        <>
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="w-5 h-5 rounded-full border-2 border-white/70 flex items-center justify-center">
              <div className="w-1 h-1 rounded-full bg-white/90" />
            </div>
          </div>
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-slate-900/85 text-white rounded-lg px-4 py-2 text-xs shadow-lg flex items-center gap-3">
            <kbd className="font-mono bg-white/15 px-1.5 rounded">W A S D</kbd> yurish
            <span className="opacity-60">·</span>
            <kbd className="font-mono bg-white/15 px-1.5 rounded">Shift</kbd> yugurish
            <span className="opacity-60">·</span>
            <kbd className="font-mono bg-white/15 px-1.5 rounded">Sichqoncha</kbd> qarash
            <span className="opacity-60">·</span>
            <kbd className="font-mono bg-white/15 px-1.5 rounded">Esc</kbd> chiqish
          </div>
          {!walkHint && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900/40" onClick={() => enterWalkRef.current?.()}>
              <div className="bg-white rounded-xl px-6 py-4 shadow-pop text-center cursor-pointer">
                <Footprints className="mx-auto text-blue-600 mb-2" size={28} />
                <div className="font-semibold text-slate-800">Skladga kirish uchun bosing</div>
                <div className="text-xs text-slate-500 mt-1">Sichqoncha bilan qarang, WASD bilan yuring</div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Minimap */}
      {mini.racks.length > 0 && mode === 'orbit' && (
        <div className="absolute bottom-3 right-3 bg-white/90 rounded-lg p-2 shadow-md border border-slate-100">
          <div className="text-[10px] text-slate-400 mb-1 flex items-center gap-1"><Grid3x3 size={11} /> Minimap</div>
          <svg width={MINI_W} height={miniH} className="block">
            <rect x={0} y={0} width={MINI_W} height={miniH} fill="#f8fafc" rx={4} />
            {mini.racks.map((r, i) => (
              <rect key={i} x={r.x * miniScale} y={r.z * miniScale + 4}
                width={r.w * miniScale} height={r.d * miniScale} rx={1.5}
                fill="#93c5fd" stroke="#3b82f6" strokeWidth={0.5} />
            ))}
            <circle cx={mini.cam[0] * miniScale} cy={mini.cam[1] * miniScale + 4} r={3.5} fill="#ef4444" />
          </svg>
        </div>
      )}

      {/* Bosib tanlash (orbit) — yacheyka ichidagi tovar + kodlar */}
      {selected && mode === 'orbit' && (
        <div className="absolute bottom-3 left-3 bg-white rounded-xl px-3.5 py-3 text-xs shadow-pop border border-slate-200 w-[280px] max-h-[380px] overflow-y-auto">
          <div className="flex items-center justify-between mb-1.5">
            <div className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
              <Boxes size={15} className="text-blue-500" /> {selected.cellId}
            </div>
            <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-slate-600"><X size={14} /></button>
          </div>
          <div className="text-slate-500 space-y-0.5">
            <div>Qator: <b>{selected.row}</b> · Etaj: <b>{selected.tier}</b> · Pallet: <b>{selected.pos}</b></div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm inline-block"
                style={{ background: '#' + STATE_COLOR[selected.status].toString(16).padStart(6, '0') }} />
              {{ occupied: 'Band', partial: 'Qisman', blocked: 'Bloklangan', empty: "Bo'sh" }[selected.status]}
            </div>
          </div>

          <div className="mt-2.5 pt-2.5 border-t border-slate-100">
            {contentsLoading && (
              <div className="flex items-center gap-1.5 text-slate-400 py-1"><Loader2 size={13} className="animate-spin" /> Yuklanmoqda…</div>
            )}
            {!contentsLoading && contents && Array.isArray(contents.stock) && contents.stock.length > 0 && (
              <div className="space-y-1.5">
                <div className="text-[10px] uppercase tracking-wide text-slate-400 font-semibold">Tovar</div>
                {contents.stock.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between bg-slate-50 rounded-lg px-2 py-1.5">
                    <div className="min-w-0">
                      <div className="font-medium text-slate-700 truncate">{nameOf(s.product_name)}</div>
                      {(s.expiry_date || s.batch) && <div className="text-[10px] text-slate-400 truncate">Partiya: {s.expiry_date || s.batch}</div>}
                    </div>
                    <div className="text-right shrink-0 ml-2">
                      <div className="font-bold text-slate-800">{s.qty ?? 0}</div>
                      {s.qty_booked ? <div className="text-[10px] text-amber-600">bron {s.qty_booked}</div> : null}
                    </div>
                  </div>
                ))}
                {Array.isArray(contents.code_tree) && contents.code_tree.length > 0 && (
                  <div className="text-[10px] text-slate-400">Transport kodlar: <b>{contents.code_tree.length}</b></div>
                )}
                {Array.isArray(contents.reservations) && contents.reservations.length > 0 && (
                  <div className="text-[10px] text-amber-600">Bron: <b>{contents.reservations.length}</b></div>
                )}
              </div>
            )}
            {!contentsLoading && (!contents || !contents.stock || contents.stock.length === 0) && (
              <div className="text-slate-400 py-1">Bu yacheykada tovar yo'q.</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function nameOf(n: any): string {
  if (!n) return '—'
  if (typeof n === 'string') return n
  return n.uz || n.ru || n.en || Object.values(n)[0] as string || '—'
}

function Legend({ c, t }: { c: string; t: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="w-3 h-3 rounded-sm inline-block border border-black/5" style={{ background: c }} />{t}
    </span>
  )
}
