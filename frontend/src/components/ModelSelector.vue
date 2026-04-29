<template>
  <div class="model-selector">
    <button class="selector-btn" @click="open = !open">
      <span class="current">{{ selectedModel ? selectedModel.display_name : '选择模型' }}</span>
      <span class="arrow">{{ open ? '▲' : '▼' }}</span>
    </button>

    <div v-if="open" class="dropdown">
      <template v-if="models.length">
        <div
          v-for="m in models"
          :key="m.id"
          class="dropdown-item"
          :class="{ active: selectedModel?.id === m.id }"
          @click="select(m)"
        >
          <span class="item-name">{{ m.display_name }} <span v-if="m.support_image" class="img-tag">🖼</span></span>
          <span class="item-check" v-if="selectedModel?.id === m.id">✓</span>
        </div>
      </template>
      <div v-else class="empty">
        <p>暂无可用模型</p>
        <p class="empty-hint">请先配置 API Key</p>
        <button class="btn-config" @click="$emit('openKeys')">配置 Key</button>
      </div>
    </div>

    <div v-if="open" class="backdrop" @click="open = false"></div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits, watch } from 'vue'

const props = defineProps({
  models: { type: Array, default: () => [] },
  modelValue: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'openKeys'])

const open = ref(false)
const selectedModel = ref(props.modelValue)

watch(() => props.modelValue, (v) => { selectedModel.value = v })

function select(m) {
  selectedModel.value = m
  emit('update:modelValue', m)
  open.value = false
}
</script>

<style scoped>
.model-selector { position: relative; }

.selector-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 14px; background: transparent; border: none;
  border-radius: 8px; cursor: pointer; color: var(--text-primary); font-size: .95rem;
  transition: background .15s;
}
.selector-btn:hover { background: var(--bg-hover); }
.current { font-weight: 600; }
.arrow { font-size: .65rem; color: var(--text-muted); }

.dropdown {
  position: absolute; top: calc(100% + 4px); left: 50%; transform: translateX(-50%);
  min-width: 240px;
  background: var(--bg-modal); border: 1px solid var(--border); border-radius: 12px;
  box-shadow: var(--shadow-lg); z-index: 50; overflow: hidden; padding: 4px 0;
}

.dropdown-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; cursor: pointer; transition: background .15s;
  color: var(--text-primary); font-size: .9rem;
}
.dropdown-item:hover { background: var(--bg-hover); }
.dropdown-item.active { font-weight: 600; }
.item-name { flex: 1; }
.img-tag { font-size: .8rem; margin-left: 4px; }
.item-check { color: var(--accent); font-size: .85rem; margin-left: 8px; }

.empty { padding: 24px; text-align: center; }
.empty p { color: var(--text-muted); margin-bottom: 6px; }
.empty-hint { font-size: .8rem; }
.btn-config {
  margin-top: 12px; padding: 8px 20px; background: var(--accent); color: #fff;
  border: none; border-radius: 20px; cursor: pointer; font-size: .85rem;
}
.btn-config:hover { background: var(--accent-hover); }

.backdrop { position: fixed; inset: 0; z-index: 40; }
</style>
