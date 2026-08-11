<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  Activity,
  Boxes,
  Container,
  Database,
  ExternalLink,
  Gauge,
  Globe,
  HardDrive,
  House,
  Laptop,
  Loader2,
  Monitor,
  Network,
  Pencil,
  Plus,
  Router,
  Server,
  Settings,
  Shield,
  RefreshCw,
  Search,
  Trash2,
  Wifi,
  X
} from 'lucide-vue-next'
import { api, type Device, type Service } from './api'
import { useDashboardStore } from './store'

const store = useDashboardStore()
const query = ref('')
const selectedDevice = ref<number | 'all'>('all')
const settingsOpen = ref(false)
const managePanel = ref<'devices' | 'services' | null>(null)
const modal = ref<'device' | 'service' | null>(null)
const editingId = ref<number | null>(null)
const busy = ref(false)
const message = ref('')
const iconMap = {
  activity: Activity,
  boxes: Boxes,
  container: Container,
  database: Database,
  docker: Container,
  gauge: Gauge,
  globe: Globe,
  home: House,
  house: House,
  laptop: Laptop,
  mac: Laptop,
  mihomo: Network,
  monitor: Monitor,
  nas: HardDrive,
  network: Network,
  router: Router,
  server: Server,
  shield: Shield,
  storage: HardDrive,
  wifi: Wifi
}
const brandIconAliases: Record<string, string> = {
  apple: 'apple',
  bazarr: 'bazarr',
  bitwarden: 'bitwarden',
  cloudflare: 'cloudflare',
  debian: 'debian',
  docker: 'docker',
  elasticsearch: 'elasticsearch',
  emby: 'emby',
  esphome: 'esphome',
  frigate: 'frigate',
  gitea: 'gitea',
  github: 'github',
  gitlab: 'gitlab',
  grafana: 'grafana',
  'home-assistant': 'homeassistant',
  homeassistant: 'homeassistant',
  homebridge: 'homebridge',
  immich: 'immich',
  influxdb: 'influxdb',
  jellyfin: 'jellyfin',
  jenkins: 'jenkins',
  kibana: 'kibana',
  linux: 'linux',
  mariadb: 'mariadb',
  minio: 'minio',
  mongodb: 'mongodb',
  mysql: 'mysql',
  navidrome: 'navidrome',
  nextcloud: 'nextcloud',
  nginx: 'nginx',
  openwrt: 'openwrt',
  plex: 'plex',
  portainer: 'portainer',
  postgres: 'postgresql',
  postgresql: 'postgresql',
  prowlarr: 'prowlarr',
  proxmox: 'proxmox',
  qbit: 'qbittorrent',
  qbittorrent: 'qbittorrent',
  radarr: 'radarr',
  redis: 'redis',
  sonarr: 'sonarr',
  syncthing: 'syncthing',
  synology: 'synology',
  tailscale: 'tailscale',
  traefik: 'traefikproxy',
  transmission: 'transmission',
  truenas: 'truenas',
  ubuntu: 'ubuntu',
  unraid: 'unraid',
  vaultwarden: 'bitwarden',
  windows: 'windows',
  wireguard: 'wireguard'
}
const iconOptions = [...new Set([...Object.keys(brandIconAliases), ...Object.keys(iconMap)])].sort()

const deviceForm = reactive({
  name: '',
  host: '',
  device_type: 'NAS',
  icon: 'server',
  description: '',
  sort_order: 0
})

const serviceForm = reactive({
  device_id: 0,
  name: '',
  protocol: 'http' as 'http' | 'https',
  port: 80 as number | null,
  path: '/',
  custom_url: '',
  icon: 'globe',
  description: '',
  favorite: false,
  enabled: true,
  health_enabled: true,
  health_method: 'GET' as 'GET' | 'HEAD',
  timeout_ms: 3000,
  sort_order: 0
})

onMounted(() => {
  store.load()
  window.setInterval(() => store.load(), 30000)
})

const filteredServices = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return store.services
    .filter((service) => selectedDevice.value === 'all' || service.device_id === selectedDevice.value)
    .filter((service) => {
      if (!needle) return true
      return [service.name, service.device_name, service.description].some((value) => value.toLowerCase().includes(needle))
    })
    .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))
})

const summary = computed(() => {
  const online = store.services.filter((item) => ['online', 'auth'].includes(item.health?.status || '')).length
  const offline = store.services.filter((item) => item.health?.status === 'offline').length
  return { devices: store.devices.length, services: store.services.length, online, offline }
})

function statusLabel(status?: string) {
  return ({ online: '在线', auth: '需认证', degraded: '异常', offline: '离线', unknown: '未检测' } as Record<string, string>)[status || 'unknown'] || '未检测'
}

function statusClass(status?: string) {
  return `status ${status || 'unknown'}`
}

function latencyClass(latency?: number | null) {
  if (latency == null) return 'metric unknown'
  if (latency < 500) return 'metric good'
  if (latency < 1500) return 'metric warn'
  return 'metric bad'
}

function httpClass(code?: number | null) {
  if (code == null) return 'metric unknown'
  if (code >= 200 && code < 400) return 'metric good'
  if (code === 401 || code === 403) return 'metric warn'
  return 'metric bad'
}

function fmtTime(value?: string | null) {
  return value ? new Date(value).toLocaleString() : '尚未检测'
}

function iconComponent(icon?: string) {
  const key = (icon || '').trim().toLowerCase()
  return iconMap[key as keyof typeof iconMap] || Globe
}

function isImageIcon(icon?: string) {
  const value = (icon || '').trim()
  return /^https?:\/\//i.test(value) || value.startsWith('/') || Boolean(brandIconAliases[value.toLowerCase()])
}

function iconImageSrc(icon?: string) {
  const value = (icon || '').trim()
  if (/^https?:\/\//i.test(value) || value.startsWith('/')) return value
  const slug = brandIconAliases[value.toLowerCase()]
  return slug ? `https://cdn.simpleicons.org/${slug}` : ''
}

function accentClass(service: Service) {
  return `accent-${service.id % 5}`
}

function openService(service: Service) {
  window.open(service.url, '_blank', 'noopener,noreferrer')
}

function resetDevice(device?: Device) {
  editingId.value = device?.id || null
  Object.assign(deviceForm, device || { name: '', host: '', device_type: 'NAS', icon: 'server', description: '', sort_order: 0 })
  modal.value = 'device'
}

function resetService(service?: Service) {
  editingId.value = service?.id || null
  Object.assign(serviceForm, service || {
    device_id: store.devices[0]?.id || 0,
    name: '',
    protocol: 'http',
    port: 80,
    path: '/',
    custom_url: '',
    icon: 'globe',
    description: '',
    favorite: false,
    enabled: true,
    health_enabled: true,
    health_method: 'GET',
    timeout_ms: 3000,
    sort_order: 0
  })
  serviceForm.custom_url = service?.custom_url || ''
  modal.value = 'service'
}

async function saveDevice() {
  busy.value = true
  try {
    editingId.value ? await api.updateDevice(editingId.value, deviceForm) : await api.createDevice(deviceForm)
    modal.value = null
    await store.load()
  } catch (error) {
    message.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    busy.value = false
  }
}

async function saveService(checkAfter = false) {
  busy.value = true
  try {
    const payload = { ...serviceForm, custom_url: serviceForm.custom_url || null }
    const saved = editingId.value ? await api.updateService(editingId.value, payload) : await api.createService(payload)
    if (checkAfter) await api.check(saved.id)
    modal.value = null
    await store.load()
  } catch (error) {
    message.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    busy.value = false
  }
}

async function removeDevice(device: Device) {
  const cascade = device.service_count > 0 && window.confirm(`设备 ${device.name} 仍有关联服务，是否同时删除这些服务？`)
  if (device.service_count > 0 && !cascade) return
  await api.deleteDevice(device.id, cascade)
  await store.load()
}

async function removeService(service: Service) {
  if (!window.confirm(`删除服务 ${service.name}？`)) return
  await api.deleteService(service.id)
  await store.load()
}
</script>

<template>
  <main class="shell">
    <datalist id="icon-options">
      <option v-for="icon in iconOptions" :key="icon" :value="icon" />
    </datalist>
    <section class="workspace">
      <header class="topline">
        <div class="brand compact">
          <div class="brand-mark"><Server :size="22" /></div>
          <div>
            <h1>Dashboard</h1>
            <p>服务导航</p>
          </div>
        </div>
        <div class="hero-actions" @mouseenter="settingsOpen = true" @mouseleave="settingsOpen = false">
          <button class="settings-button" @click="settingsOpen = !settingsOpen"><Settings :size="16" />设置</button>
          <div v-if="settingsOpen" class="settings-menu">
            <button @click="managePanel = 'devices'; settingsOpen = false">设备管理</button>
            <button @click="managePanel = 'services'; settingsOpen = false">服务管理</button>
          </div>
        </div>
      </header>

      <section class="toolbar">
        <label class="search"><Search :size="18" /><input v-model="query" placeholder="搜索服务、设备或说明" /></label>
        <button class="icon-btn" title="刷新" @click="store.load()"><RefreshCw :size="18" /></button>
      </section>

      <p v-if="store.error || message" class="alert">{{ store.error || message }}</p>

      <section class="content">
        <div v-if="!filteredServices.length" class="empty-state">
          <Activity :size="28" />
          <h3>暂无可显示服务</h3>
          <p>新增设备和服务后，这里会显示导航卡片。</p>
        </div>
        <div v-else class="grid">
          <article
            v-for="service in filteredServices"
            :key="service.id"
            :class="['card', accentClass(service)]"
            role="link"
            tabindex="0"
            @click="openService(service)"
            @keydown.enter="openService(service)"
          >
            <div class="card-top">
              <div class="service-icon">
                <img v-if="isImageIcon(service.icon)" :src="iconImageSrc(service.icon)" alt="" />
                <component :is="iconComponent(service.icon)" v-else :size="22" />
              </div>
              <div class="service-title">
                <h2>{{ service.name }}</h2>
                <p>{{ service.device_name }}</p>
              </div>
              <span :class="statusClass(service.health?.status)">{{ statusLabel(service.health?.status) }}</span>
            </div>
            <p class="service-desc">{{ service.description || service.url }}</p>
            <div class="meta"><Server :size="15" />{{ service.device_host }}</div>
            <div class="health-line">
              <span :class="latencyClass(service.health?.latency_ms)">{{ service.health?.latency_ms ?? '-' }} ms</span>
              <span :class="httpClass(service.health?.http_status)">HTTP {{ service.health?.http_status ?? '-' }}</span>
            </div>
            <div class="time">{{ fmtTime(service.health?.checked_at) }}</div>
            <div class="actions">
              <button @click.stop="store.check(service)"><RefreshCw :size="16" />检测</button>
              <span class="open-hint"><ExternalLink :size="16" />点击卡片打开</span>
            </div>
          </article>
        </div>
      </section>

    <div v-if="managePanel" class="modal">
      <section class="manage-dialog">
        <button type="button" class="close" @click="managePanel = null"><X :size="18" /></button>
        <template v-if="managePanel === 'devices'">
          <div class="manage-head">
            <div>
              <h2>设备管理</h2>
              <p>维护 EasyTier 设备地址，服务入口会引用这里的主机名。</p>
            </div>
            <button @click="resetDevice()"><Plus :size="16" />新增设备</button>
          </div>
          <div class="table">
            <div class="row head"><span>名称</span><span>地址</span><span>类型</span><span>服务</span><span>操作</span></div>
            <div v-for="device in store.devices" :key="device.id" class="row">
              <span>{{ device.name }}</span><span>{{ device.host }}</span><span>{{ device.device_type }}</span>
              <span>{{ device.online_count }}/{{ device.service_count }}</span>
              <span class="row-actions"><button @click="resetDevice(device)"><Pencil :size="15" /></button><button @click="removeDevice(device)"><Trash2 :size="15" /></button></span>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="manage-head">
            <div>
              <h2>服务管理</h2>
              <p>配置服务入口、检测方式和展示顺序。</p>
            </div>
            <button :disabled="!store.devices.length" @click="resetService()"><Plus :size="16" />新增服务</button>
          </div>
          <div class="table service-table">
            <div class="row head"><span>名称</span><span>设备</span><span>地址</span><span>状态</span><span>操作</span></div>
            <div v-for="service in store.services" :key="service.id" class="row">
              <span>{{ service.name }}</span><span>{{ service.device_name }}</span><span class="url">{{ service.url }}</span>
              <span>{{ statusLabel(service.health?.status) }}</span>
              <span class="row-actions"><button @click="store.check(service)"><RefreshCw :size="15" /></button><button @click="resetService(service)"><Pencil :size="15" /></button><button @click="removeService(service)"><Trash2 :size="15" /></button></span>
            </div>
          </div>
        </template>
      </section>
    </div>

    <div v-if="modal" class="modal">
      <form class="dialog" @submit.prevent="modal === 'device' ? saveDevice() : saveService(false)">
        <button type="button" class="close" @click="modal = null"><X :size="18" /></button>
        <div class="dialog-head">
          <h2>{{ editingId ? '编辑' : '新增' }}{{ modal === 'device' ? '设备' : '服务' }}</h2>
          <p>{{ modal === 'device' ? '设备地址变化后，未配置完整 URL 的服务会自动使用新地址。' : '配置原始管理入口，点击卡片会在新标签页打开。' }}</p>
        </div>
        <template v-if="modal === 'device'">
          <section class="form-section">
            <h3>基础信息</h3>
            <div class="two">
              <label class="field"><span>设备名称</span><input v-model="deviceForm.name" required placeholder="例如 Mac Mini" /></label>
              <label class="field"><span>设备地址</span><input v-model="deviceForm.host" required placeholder="EasyTier IP 或主机名" /></label>
            </div>
            <div class="two">
              <label class="field"><span>设备类型</span><input v-model="deviceForm.device_type" placeholder="例如 NAS / Router / Mac" /></label>
              <label class="field"><span>图标标识或图片 URL</span><input v-model="deviceForm.icon" list="icon-options" placeholder="选择或输入，例如 server / nas / router" /></label>
            </div>
            <label class="field"><span>设备说明</span><textarea v-model="deviceForm.description" placeholder="可选说明"></textarea></label>
            <label class="field compact-field"><span>排序值</span><input v-model.number="deviceForm.sort_order" type="number" placeholder="越小越靠前" /></label>
          </section>
        </template>
        <template v-else>
          <section class="form-section">
            <h3>基础信息</h3>
            <div class="two">
              <label class="field"><span>所属设备</span><select v-model.number="serviceForm.device_id" required><option v-for="device in store.devices" :key="device.id" :value="device.id">{{ device.name }}</option></select></label>
              <label class="field"><span>服务名称</span><input v-model="serviceForm.name" required placeholder="例如 iStoreOS 管理页面" /></label>
            </div>
            <label class="field"><span>说明</span><textarea v-model="serviceForm.description" placeholder="可选说明"></textarea></label>
          </section>
          <section class="form-section">
            <h3>访问地址</h3>
            <div class="two">
              <label class="field"><span>协议</span><select v-model="serviceForm.protocol"><option>http</option><option>https</option></select></label>
              <label class="field"><span>端口</span><input v-model.number="serviceForm.port" type="number" min="1" max="65535" placeholder="例如 80" /></label>
            </div>
            <label class="field"><span>路径</span><input v-model="serviceForm.path" placeholder="例如 /admin" /></label>
            <label class="field"><span>完整 URL，可选</span><input v-model="serviceForm.custom_url" placeholder="填写后优先使用，例如 https://example.com" /></label>
          </section>
          <section class="form-section">
            <h3>检测与展示</h3>
            <div class="checks"><label><input v-model="serviceForm.enabled" type="checkbox" /> 启用入口</label><label><input v-model="serviceForm.health_enabled" type="checkbox" /> 启用检测</label></div>
            <div class="two">
              <label class="field"><span>检测方法</span><select v-model="serviceForm.health_method"><option>GET</option><option>HEAD</option></select></label>
              <label class="field"><span>超时时间，毫秒</span><input v-model.number="serviceForm.timeout_ms" type="number" min="100" max="30000" /></label>
            </div>
            <div class="two">
              <label class="field">
                <span>图标标识或图片 URL</span>
                <div class="icon-input">
                  <div class="service-icon preview-icon">
                    <img v-if="isImageIcon(serviceForm.icon)" :src="iconImageSrc(serviceForm.icon)" alt="" />
                    <component :is="iconComponent(serviceForm.icon)" v-else :size="20" />
                  </div>
                  <input v-model="serviceForm.icon" list="icon-options" placeholder="选择常见服务，或填图片 URL" />
                </div>
              </label>
              <label class="field"><span>排序值</span><input v-model.number="serviceForm.sort_order" type="number" placeholder="越小越靠前" /></label>
            </div>
          </section>
        </template>
        <div class="dialog-actions">
          <button type="button" v-if="modal === 'service'" @click="saveService(true)">测试连接并保存</button>
          <button type="submit" :disabled="busy"><Loader2 v-if="busy" :size="16" class="spin" />保存</button>
        </div>
      </form>
    </div>
    </section>
  </main>
</template>
