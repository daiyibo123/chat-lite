<template>
  <div class="image-gen-inline">
    <div class="gen-card">
      <canvas ref="canvasRef" class="particle-canvas" :class="{ 'fade-out': imageReady }"></canvas>
      <img
        v-if="imageUrl"
        :key="imageUrl"
        :src="imageUrl"
        class="gen-image"
        :class="{ 'fade-in': imageReady }"
        @load="handleImageLoad"
        @error="handleImageError"
        @click="openFull"
      />
      <button v-if="imageUrl" class="download-btn" title="下载图片" @click.stop="downloadImage">⬇</button>
      <div class="gen-status">
        <span v-if="!imageUrl" class="gen-loading">
          <span class="dot-anim">●</span>
          <span class="dot-anim d2">●</span>
          <span class="dot-anim d3">●</span>
          &nbsp;正在生成图片…
        </span>
        <span v-else-if="imageError" class="gen-error">图片加载失败 · 点击打开</span>
        <span v-else-if="!imageReady" class="gen-loading">
          <span class="dot-anim">●</span>
          <span class="dot-anim d2">●</span>
          <span class="dot-anim d3">●</span>
          &nbsp;正在加载图片…
        </span>
        <span v-else class="gen-done">生成完成 · 点击查看大图</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, defineProps } from 'vue'

const props = defineProps({
  imageUrl: { type: String, default: '' },
})

const canvasRef = ref(null)
const imageReady = ref(false)
const imageError = ref(false)
let animId = null
let particles = []

watch(() => props.imageUrl, (url) => {
  imageReady.value = false
  imageError.value = false
  if (!url) return
  const img = new Image()
  img.onload = () => handleImageLoad()
  img.onerror = () => handleImageError()
  img.src = url
})

function initParticles() {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const w = canvas.width = Math.max(1, Math.floor(rect.width || 320))
  const h = canvas.height = Math.max(1, Math.floor(rect.height || 320))
  particles = []
  const count = 120
  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 1.5,
      vy: (Math.random() - 0.5) * 1.5,
      r: Math.random() * 3 + 1,
      hue: Math.random() * 60 + 330,
      alpha: Math.random() * 0.6 + 0.4,
    })
  }
}

function drawParticles() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const w = canvas.width
  const h = canvas.height

  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = '#1a1a2e'
  ctx.fillRect(0, 0, w, h)

  const grd = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2)
  grd.addColorStop(0, 'rgba(233, 69, 96, 0.15)')
  grd.addColorStop(0.5, 'rgba(100, 60, 180, 0.08)')
  grd.addColorStop(1, 'rgba(0, 0, 0, 0)')
  ctx.fillStyle = grd
  ctx.fillRect(0, 0, w, h)

  for (const p of particles) {
    p.x += p.vx
    p.y += p.vy
    if (p.x < 0 || p.x > w) p.vx *= -1
    if (p.y < 0 || p.y > h) p.vy *= -1

    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    ctx.fillStyle = `hsla(${p.hue}, 80%, 65%, ${p.alpha})`
    ctx.fill()
  }

  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 60) {
        ctx.beginPath()
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.strokeStyle = `hsla(340, 60%, 60%, ${0.15 * (1 - dist / 60)})`
        ctx.lineWidth = 0.5
        ctx.stroke()
      }
    }
  }

  animId = requestAnimationFrame(drawParticles)
}

function openFull() {
  if (props.imageUrl) window.open(props.imageUrl, '_blank')
}

function handleImageLoad() {
  imageReady.value = true
  imageError.value = false
}

function handleImageError() {
  imageReady.value = false
  imageError.value = true
}

async function downloadImage() {
  if (!props.imageUrl) return
  const filename = `chat-lite-image-${Date.now()}.png`
  try {
    const res = await fetch(props.imageUrl)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch {
    const a = document.createElement('a')
    a.href = props.imageUrl
    a.download = filename
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    a.remove()
  }
}

onMounted(() => {
  initParticles()
  drawParticles()
})

onUnmounted(() => {
  if (animId) cancelAnimationFrame(animId)
})
</script>

<style scoped>
.image-gen-inline {
  display: block;
  width: 320px;
  max-width: 100%;
  margin: 4px 0;
}
.gen-card {
  position: relative;
  width: 320px;
  max-width: 100%;
  aspect-ratio: 1 / 1;
  background: #1a1a2e;
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow);
}
.particle-canvas,
.gen-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: 12px;
}
.particle-canvas {
  transition: opacity 1s ease;
  z-index: 1;
}
.particle-canvas.fade-out {
  opacity: 0;
  pointer-events: none;
}
.gen-image {
  z-index: 2;
  object-fit: cover;
  opacity: 0;
  transition: opacity 1s ease;
  cursor: pointer;
}
.gen-image.fade-in {
  opacity: 1;
}
.download-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 3;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 10px;
  background: rgba(0,0,0,.58);
  color: #fff;
  cursor: pointer;
  opacity: 0;
  transform: translateY(-4px);
  transition: opacity .15s ease, transform .15s ease, background .15s ease;
  backdrop-filter: blur(8px);
}
.gen-card:hover .download-btn {
  opacity: 1;
  transform: translateY(0);
}
.download-btn:hover {
  background: rgba(0,0,0,.78);
}
.gen-status {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(to top, rgba(22, 33, 62, .94), rgba(22, 33, 62, .65));
  color: #e0e0e0;
  font-size: 0.86rem;
}
.gen-loading {
  display: flex;
  align-items: center;
  gap: 2px;
  color: #ddd;
}
.dot-anim {
  animation: dotPulse 1.4s ease-in-out infinite;
  color: #e94560;
  font-size: 0.6rem;
}
.d2 { animation-delay: 0.2s; }
.d3 { animation-delay: 0.4s; }
@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}
.gen-error {
  color: #f87171;
}
.gen-done {
  color: #4ade80;
}
</style>
